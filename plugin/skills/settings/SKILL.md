---
description: View or change Caddy plugin settings stored at ~/.caddy/config.json. Use when the user types /caddy:settings followed by show, set <key> <value>, or unset <key>. Local-only — no backend round-trip, no MCP call.
---

# Caddy: Settings

Manage the local Caddy plugin configuration at `~/.caddy/config.json`. This skill is purely client-side. It never calls Caddy's MCP server, never sends data to Caddy's backend, and never reads anything outside `~/.caddy/`. The customer's settings stay on their machine.

## Subcommands

`$ARGUMENTS` is the rest of the line the user typed after `/caddy:settings`. Parse it as a subcommand plus optional arguments.

Three valid forms:
- `show` — display current config
- `set <key> <value>` — persist a setting
- `unset <key>` — clear a setting

If `$ARGUMENTS` is empty, or the first token is not one of `show`, `set`, `unset`, print the usage block and stop. Do not proceed.

### Usage block (print on missing or unknown subcommand)

```
Usage:
  /caddy:settings show                       # display current config
  /caddy:settings set <key> <value>          # persist a setting
  /caddy:settings unset <key>                # clear a setting

Settable keys:
  connector    anthropic-connector | copy-paste
```

If the user typed an unknown subcommand (`/caddy:settings foo`), prepend the line: `unknown subcommand 'foo'` before the usage block.

## Config schema

```json
{
  "schemaVersion": 1,
  "connector": "anthropic-connector"
}
```

- **File location:** `~/.caddy/config.json` (local to the user's machine; Caddy's backend never reads it).
- **`schemaVersion`** is always written by this skill on any `set` or `unset` operation. Required. Value is currently `1`. Not customer-settable; not displayed in `show` output.
- **`connector`** is optional. Valid values: `"anthropic-connector"` (the user has set up Anthropic-hosted Gmail/Calendar/Drive connectors via claude.ai), or `"copy-paste"` (the user operates in copy-paste degraded mode and will paste content into prompts manually). No default value: unset means undefined, and consumers (future anchor skills) must handle the missing case explicitly.
- **All keys except `schemaVersion` are optional.** Unset keys are not implicitly defaulted.
- **Migration policy:** If a future v2+ version of this skill needs to break value shapes, it will look at `schemaVersion` and migrate forward. A config file with no `schemaVersion` is treated as v0 (pre-versioning) and auto-promoted to `schemaVersion: 1` on the first `set` or `unset`. This skill never removes `schemaVersion`.

## `show` flow

1. Try to read `~/.caddy/config.json` using the Read tool.

2. **Always print first**, regardless of whether the file exists:
   ```
   Config file: ~/.caddy/config.json
   ```
   Followed by a blank line. The customer needs to know where the file lives so they can manually inspect, back up, or hand-edit it.

3. **If the file does not exist:**
   Print:
   ```
   (no config yet; run /caddy:settings set <key> <value> to start)
   ```

4. **If the file exists and parses as valid JSON:**
   - Filter out `schemaVersion` (it's an internal field, not a customer-facing setting).
   - Sort the remaining keys alphabetically.
   - For each key, print one line: `key: value`
   - If there are no customer-facing keys after filtering, print the empty-state line from step 3.

5. **If the file exists but is malformed JSON** (Read succeeds but the contents don't parse):
   Print:
   ```
   error: ~/.caddy/config.json is not valid JSON. Inspect it manually or delete it to start fresh.
   ```
   Do not attempt automatic recovery. The customer's options are clear: fix the file, or delete it.

6. **Always print last** (after a blank line):
   ```
   Settable keys: connector
   ```
   So the customer discovers what they can change without consulting external docs.

## `set <key> <value>` flow

1. **Validate `<key>` against the allowed customer-settable keys:** currently `["connector"]`.
   - If `<key>` is missing entirely: print `set requires a key and a value. Valid keys: connector`. Stop. No file write.
   - If `<key>` is not in the allowed list: print `unknown setting key '<key>'; valid keys: connector`. Stop. No file write.

2. **Validate `<value>` against the allowed values for that key:**
   - For `connector`: valid values are `["anthropic-connector", "copy-paste"]`.
   - If `<value>` is missing: print `set requires a value for '<key>'. Valid values: anthropic-connector, copy-paste`. Stop. No file write.
   - If `<value>` is not valid: print `invalid value '<value>' for '<key>'; valid values: anthropic-connector, copy-paste`. Stop. No file write.

3. **Read the existing config:**
   - Try Read on `~/.caddy/config.json`.
   - If the file does not exist or the Read fails for any reason: treat the current config as `{}`.
   - If the file exists and parses: use the parsed object as the starting point.
   - If the file exists but is malformed JSON: print the same error as `show` step 5 and stop. Do not overwrite a malformed file with new content; require the customer to resolve the malformed state first.

4. **Merge:** start from the existing config object, set `schemaVersion: 1` (always; auto-promote pre-versioning configs), set `<key>: <value>`. Preserve any other keys already present (forward-compat for future schema additions).

5. **Write to disk via Write tool:**
   - JSON-encode the merged object with 2-space indent and a trailing newline.
   - Target path: `~/.caddy/config.json`.
   - **If the Write tool fails** (permission denied, disk full, read-only filesystem, parent directory missing+uncreatable, ENAMETOOLONG, or any other reason): catch the failure and print:
     ```
     could not write to ~/.caddy/config.json: <reason from the failure>. Try: chmod u+w ~/.caddy/ or check filesystem permissions/disk space.
     ```
     Do not propagate the raw error to the user. Do not expose stack traces.
     - **No partial-write guarantee:** the Write tool either writes the full new content or doesn't write at all. We do not produce intermediate or truncated files.

6. **On success, print:**
   ```
   Set <key> = <value>
   ```

## `unset <key>` flow

1. **Validate `<key>`:**
   - If `<key>` is missing: print `unset requires a valid key. Valid keys: connector`. Stop. No file write.
   - If `<key>` is `schemaVersion`: print `cannot unset 'schemaVersion'; it is an internal field, not a settable key`. Stop. No file write.
   - If `<key>` is not in the allowed list: print `unknown key '<key>'; valid keys: connector`. Stop. No file write.

2. **Read the existing config:**
   - Try Read on `~/.caddy/config.json`.
   - If the file does not exist OR the file exists but does not contain `<key>`: print:
     ```
     (no value to unset; '<key>' was not set)
     ```
     Stop. No file write.
   - If the file exists but is malformed JSON: print the same error as `show` step 5 and stop.

3. **Remove the key:** delete `<key>` from the parsed object. Keep `schemaVersion: 1` (set it if not present). Keep all other keys.

4. **Write to disk via Write tool:** same write logic as `set` step 5, including the same write-failure error handling and no-partial-write guarantee.

5. **On success, print:**
   ```
   Unset <key>
   ```

## Hard rules

- **No MCP tool calls.** This skill never invokes `plugin:caddy:caddy` or any other backend tool. Pure local-file work.
- **No Bash invocations.** Use the Read and Write tools only. (Atomic-write via shell rename is out of scope for v1; documented in plan boundaries.)
- **No writes outside `~/.caddy/`.** The skill operates exclusively on `~/.caddy/config.json`. Never touch `~/.caddy/voice.md`, `~/.caddy/brand.md`, or anything else.
- **Never expose stack traces or raw tool errors to the user.** All failure paths produce customer-readable error strings per the formats above.
- **Never log the bearer token, the Anthropic key, or the user's config values to any persistent location.** Skill output goes to the user's session transcript only.

## Examples (for the assistant to follow)

**Example 1 — empty show:**

User: `/caddy:settings show`

(File does not exist.)

Output:
```
Config file: ~/.caddy/config.json

(no config yet; run /caddy:settings set <key> <value> to start)

Settable keys: connector
```

**Example 2 — set, then show:**

User: `/caddy:settings set connector anthropic-connector`

Output:
```
Set connector = anthropic-connector
```

File now contains:
```json
{
  "schemaVersion": 1,
  "connector": "anthropic-connector"
}
```

User: `/caddy:settings show`

Output:
```
Config file: ~/.caddy/config.json

connector: anthropic-connector

Settable keys: connector
```

(Note: `schemaVersion` is NOT listed in `show` output.)

**Example 3 — unset:**

User: `/caddy:settings unset connector`

Output:
```
Unset connector
```

File now contains:
```json
{
  "schemaVersion": 1
}
```

**Example 4 — invalid key:**

User: `/caddy:settings set foo bar`

Output:
```
unknown setting key 'foo'; valid keys: connector
```

(No file write.)

**Example 5 — invalid value:**

User: `/caddy:settings set connector banana`

Output:
```
invalid value 'banana' for 'connector'; valid values: anthropic-connector, copy-paste
```

(No file write.)

**Example 6 — write failure:**

User: `/caddy:settings set connector anthropic-connector`

(But `~/.caddy/` is read-only.)

Output:
```
could not write to ~/.caddy/config.json: permission denied. Try: chmod u+w ~/.caddy/ or check filesystem permissions/disk space.
```

(No file write. No stack trace.)

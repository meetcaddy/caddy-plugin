# Caddy plugin

> **Invite-only v1.0.** Caddy is currently a closed-pilot SaaS for a small group of operators. If you do not have a bearer token from Tucker, you cannot use this plugin yet. Contact hi@meetcaddy.com to request access.

Caddy. Your unfair advantage. Voice-fingerprinted drafts and operator rhythm, running in your own Claude Code on your existing Claude subscription.

This plugin is the thin Claude Code surface for Caddy. The skills run inside your own Claude Code session on your Claude subscription — no prompt logic or model routing runs server-side. Caddy is single-billing: the backend's only role is validating your license.

---

## Prerequisite

Claude Code installed and authenticated. You can run it in the Claude desktop app (Code mode), the CLI, or an IDE extension.

**Recommended: the Claude desktop app's Code mode.** It runs Caddy at full capability with the least setup, and you do not need a separate code editor. Use Code mode specifically; regular chat and Projects cannot run Caddy.

If you do not have Claude Code yet, install it first: see https://docs.claude.com/en/docs/claude-code/quickstart. Then come back here.

---

## What you need

One long-lived secret, exported as an environment variable in the shell that launches Claude Code:

1. **`CADDY_BEARER_TOKEN`** — your Caddy account token. Issued via a one-time exchange URL Tucker sends after invite approval. The URL is good for a single click; you redeem it to receive the bearer token in your browser, then paste the token into your shell profile (or `.env`). Treat the bearer token like a password.

Caddy is single-billing: drafting and operator-rhythm work run inside your own Claude Code session on your existing Claude subscription. There is no separate Anthropic API key to obtain, set, or pay for.

---

## Install (macOS)

> **Windows:** the steps differ (PowerShell + Scoop, not zsh/Homebrew). Follow the Windows install guide Tucker sends you, not the macOS steps below.

> **Editor note:** if your terminal doesn't have the `code` shell command (typical on a fresh Mac), substitute `open -e` in the commands below. `open -e ~/.zshrc` opens the file in TextEdit. To create an empty file first if it doesn't exist: `touch ~/.zshrc && open -e ~/.zshrc`. If you'd rather install the `code` CLI: open VS Code, press Cmd+Shift+P, type "shell command", pick **Shell Command: Install 'code' command in PATH**.

> **TextEdit warning:** before editing `~/.zshrc` or your voice/brand files in TextEdit, turn off Smart Quotes (Edit → Substitutions → uncheck Smart Quotes). TextEdit otherwise silently converts straight `"` to curly `"` which breaks shell config files and degrades voice fingerprint matching.

1. Export your bearer token in your shell profile so every Claude Code session inherits it:

   ```sh
   # in ~/.zshrc or ~/.bashrc
   export CADDY_BEARER_TOKEN="caddy_..."        # from Tucker's exchange URL
   ```

   Reload your shell: `source ~/.zshrc` (or close and reopen the terminal).

   Verify it is set:
   ```sh
   echo "Bearer: ${CADDY_BEARER_TOKEN:0:8}..."
   ```
   It should print something (the `:0:8` only shows the first 8 chars; full token isn't echoed).

2. Create your local voice + brand markdown (the plugin reads these on every draft):

   ```sh
   mkdir -p ~/.caddy
   $EDITOR ~/.caddy/voice.md     # paste 200+ words of your writing
   $EDITOR ~/.caddy/brand.md     # paste 100+ words about your brand
   ```

3. Launch Claude Code, then add the Caddy marketplace and install the plugin:

   ```
   /plugin marketplace add meetcaddy/caddy-plugin
   /plugin install caddy@meet-caddy
   ```

   The first command registers Caddy's plugin catalog. The second downloads the plugin into your Claude Code session (sparse clone of the `plugin/` folder, pinned to the commit the marketplace currently tags).

4. **Single-billing:** Caddy runs entirely inside your own Claude Code session on your existing Claude subscription. If Claude Code prompts you about an API key for the MCP server, just hit Enter to skip — Caddy does not need one.

5. Test:

   ```
   /caddy:draft Write a 3-paragraph LinkedIn post announcing my Q4 product update.
   ```

   You should see the draft stream in line by line, in your voice.

---

## First-time setup (recommended)

If this is your first time using Caddy on this machine, run `/caddy:intake` once. It interviews you for ~30 to 60 minutes about your voice and your brand, then writes `~/.caddy/voice.md` and `~/.caddy/brand.md` to your disk. `/caddy:draft` uses those files on every call. You can skip intake and write the markdown yourself if you prefer; the format is documented in `plugin/skills/intake/SKILL.md`.

```
/caddy:intake
```

Your interview answers stay local on your machine. Caddy is single-billing: `/caddy:draft` reads `~/.caddy/voice.md` and `~/.caddy/brand.md` locally inside your own Claude Code session — they are never sent to Caddy's backend (the backend only validates your license).

---

## Daily triage

Once you're set up, `/caddy:triage` handles the inbound flood. Paste a pile of emails, messages, or tasks, walk through them one at a time, and end with a prioritized action list at `~/.caddy/triage/triage-YYYY-MM-DD.md`. The triage file stays on your machine; only your tier + action decisions are saved, not verbatim message bodies.

```
/caddy:triage
```

---

## Daily brief

Each morning, `/caddy:start-of-day` reads your existing Caddy context (voice.md + brand.md + today's triage) and produces a daily brief at `~/.caddy/briefs/start-of-day-YYYY-MM-DD.md`. If you have a connector configured (`/caddy:settings set connector anthropic-connector` or `copy-paste`), it'll also pull or ask for today's calendar + key inbox items. The brief stays on your machine; pasted message bodies never land in the file.

```
/caddy:start-of-day
```

---

## Meeting prep

Before any meeting where you want to walk in sharp, run `/caddy:prep`. Tell Caddy who the meeting's with and what it's about; it reads your context (voice + brand + today's triage), then writes a prep brief at `~/.caddy/briefs/prep-YYYY-MM-DD-<slug>.md` with talking points, open questions, and a suggested first move. Different meetings on the same day get different slugs so they don't overwrite each other.

```
/caddy:prep
```

---

## Meeting followup

After a meeting, run `/caddy:followup`. Tell Caddy what happened (outcomes, decisions, action items). It reads your context (voice + brand + the matching prep file from earlier if you ran `/caddy:prep` with the same slug + date), then writes a recap brief at `~/.caddy/briefs/followup-YYYY-MM-DD-<slug>.md` with what was decided, action items split Mine/Theirs, open threads, triage suggestions, and a draft follow-up message in your voice.

```
/caddy:followup
```

---

## Configure (optional)

Caddy ships with a local-only settings command for tuning plugin behavior. Settings persist to `~/.caddy/config.json` and are local to your machine. Caddy's backend never sees them.

```
/caddy:settings show                            # display current config
/caddy:settings set connector anthropic-connector   # tell Caddy you use Anthropic-hosted Gmail/Calendar/Drive connectors
/caddy:settings unset connector                 # clear a setting
```

Available settings:
- `connector` — values: `anthropic-connector` or `copy-paste`. Optional. Future anchor skills (intake, triage, etc.) will branch on this; `/caddy:draft` does not read it.

---

## Knowledge graph (optional companion)

`/caddy:graphify` builds a navigable knowledge graph from any folder of code, docs, papers, or images and writes three outputs to `graphify-out/`: interactive HTML, queryable JSON, and a plain-language report. Useful for understanding a new codebase, a research corpus, or a client's document pile before you touch anything.

```
/caddy:graphify <path>            # full pipeline on a folder
/caddy:graphify query "<question>" # ask a question of the existing graph
/caddy:graphify explain "<concept>" # plain-language explanation of a node
```

**Prerequisite (one-time):** install the upstream `graphify` CLI binary on your machine. See the skill's Prerequisite section for the canonical install commands. If `graphify` is not on your PATH, the skill will attempt to auto-install on first invocation and exit cleanly with a pointer to the install command if that fails.

---

## BASE workspace orientation (optional companion)

BASE (Builder's Automated State Engine) is a workspace orchestration framework: project tracking, decision logs, weekly/daily rituals, drift detection, structured grooming cycles. Once installed it gives Claude Code a durable "this is what my workspace IS" context. Caddy's `/caddy:base-setup` installs BASE's MCP server once at a fixed home (`~/.caddy/base`) and registers it at Claude Code **user scope**, so it loads in every session from any folder; the BASE skills + slash commands themselves come from the Homebrew tap.

```
/base:scaffold       # set up BASE in a new workspace
/base:audit          # deep workspace optimization audit
/base:groom          # structured grooming cycle (project + decision review)
/base:status         # current workspace state snapshot
/caddy:base-setup    # install base-mcp globally (one-time per machine)
```

**Prerequisite (one-time per machine):** install the Caddy Homebrew tap and BASE. The `caddy-frameworks` meta-formula bundles BASE + PAUL + SEED + Skillsmith + Aegis in one install:

```
brew tap meetcaddy/caddy
brew install caddy-frameworks
caddy-link
```

After that, run `/caddy:base-setup` once inside Claude Code. It installs `base-mcp` at the fixed home `~/.caddy/base` and registers it at Claude Code **user scope**, so the `mcp__base-mcp__*` tools are available in every session from any folder — there is no per-workspace step and no folder to remember. The setup is idempotent (safe to re-run); a re-run cleanly repairs a stale registration.

Upstream: `@chrisai/base@3.1.5` by Christopher Kahler (MIT).

---

## CARL rule routing + decision logging (optional companion)

CARL (Context Augmentation & Reinforcement Layer) is a rule-routing + decision-logging framework: it tracks which rules apply to which contexts, logs decisions per domain, and supports staged proposals with operator approval. Once installed, CARL gives Claude Code a durable "what did we already decide and why?" memory layer. Caddy's `/caddy:carl-setup` installs CARL's MCP server once at a fixed home (`~/.carl`) and registers it at Claude Code **user scope**, so it loads in every session from any folder; the underlying carl-core package comes from the Homebrew tap.

CARL is **MCP-only** — it ships no slash commands or suite skills, just 30 MCP tools you call by name (or by asking Claude in chat). The starter set (8 v2 tools):

```
mcp__carl-mcp__carl_v2_log_decision       # log a decision in CARL state
mcp__carl-mcp__carl_v2_search_decisions   # find past decisions by domain or text
mcp__carl-mcp__carl_v2_get_decisions      # list decisions in a domain
mcp__carl-mcp__carl_v2_list_domains       # see all CARL domains
mcp__carl-mcp__carl_v2_get_config         # read current config + active rules
mcp__carl-mcp__carl_v2_stage_proposal     # propose a new rule for approval
mcp__carl-mcp__carl_v2_approve_proposal   # promote staged proposal to active
mcp__carl-mcp__carl_v2_get_staged         # see what's pending approval
```

The remaining 22 tools cover advanced cases: rule CRUD (`add_rule`, `remove_rule`, `replace_rules`), archival, domain creation/toggling, and v1 legacy tools kept for back-compat with CARL workspaces from prior installs.

**Prerequisite (one-time per machine):** install the Caddy Homebrew tap — the `caddy-frameworks` meta-formula bundles CARL alongside BASE + PAUL + SEED + Skillsmith + Aegis:

```
brew tap meetcaddy/caddy
brew install caddy-frameworks
caddy-link
```

After that, run `/caddy:carl-setup` once inside Claude Code. It installs `carl-mcp` at the fixed home `~/.carl` and registers it at Claude Code **user scope**, so the `mcp__carl-mcp__*` tools are available in every session from any folder — there is no per-workspace step. CARL keeps one global `~/.carl/` directory (decisions log + sessions). The setup is idempotent (safe to re-run); a re-run cleanly repairs a stale registration.

**Rule injection into every prompt, from any folder:** `/caddy:carl-setup` automatically registers CARL's `UserPromptSubmit` hook in your Claude Code `settings.json` (with a one-time backup of the prior file). Because the CARL scope lives at `~/.carl`, the hook's existing walk-up discovers it from any working directory under your home folder, so active CARL rules inject into every prompt no matter where Claude Code was launched. No manual step — it is part of the setup skill.

Upstream: `carl-core@2.0.2` by Christopher Kahler (MIT). Same upstream author as BASE.

---

## Secret hygiene

**Do NOT** paste `CADDY_BEARER_TOKEN` into:
- Any chat interface, including Claude.ai conversations or other AI assistants
- Any git repository (even private; rotate immediately if pushed)
- Any screenshot for support (redact before sharing)
- Any `echo` or `cat` command that prints them to your terminal scrollback

If you have done any of the above, treat the affected token as compromised and rotate it immediately (see "Credential lifecycle" below).

The Caddy bearer token is long-lived; it does not expire on a schedule. It must be rotated manually if compromised.

---

## Credential lifecycle

### Caddy bearer token

If you suspect your bearer token is leaked, email **hi@meetcaddy.com** immediately with subject line `Bearer token rotation request`. Include your account email. Tucker will revoke the old token and issue a fresh one-time exchange URL. Existing Claude Code sessions will start returning auth errors until you swap the new token into your env vars.

---

## First-call failure table

Caddy is single-billing: `/caddy:draft` and the other skills run inside your own Claude Code session on your Claude subscription, so there is no Caddy-side model call and no Anthropic API error codes to decode. Real failures fall into three buckets — the plugin's license proxy, Claude Code's own auth, and install issues — each covered below.

### Errors from the plugin's local proxy (start with `proxy:`)

These come from the small Node script that bridges Claude Code to the Caddy backend.

| Message starts with | What it means | What you do |
|---|---|---|
| `proxy: upstream 401` | Your `CADDY_BEARER_TOKEN` was rejected by Caddy (wrong, expired, or revoked). | Verify the env var matches the bearer you received from your exchange URL. If it does and still fails, your token may have been rotated. Email hi@meetcaddy.com to reissue. |
| `proxy: upstream 4xx` (other 4xx) | Caddy rejected the request (rare; typically a malformed call). | Try again. If it persists, email hi@meetcaddy.com with the timestamp. |
| `proxy: upstream 5xx` | Caddy backend is having problems. | Wait 60 seconds and retry. If persistent across multiple drafts, email hi@meetcaddy.com. |
| `proxy: could not reach Caddy server (ENOTFOUND \| ECONNREFUSED \| ETIMEDOUT)` | Network connectivity issue (DNS, firewall, or Caddy is down). | Check your internet connection. If you're behind a corporate firewall, the proxy needs outbound HTTPS to `api.meetcaddy.com`. If your network is fine, Caddy itself may be down — wait, then retry. |
| `proxy: stream interrupted` | The streaming response was cut off mid-flight (network blip, laptop sleep, etc.). | Try again. The draft was not delivered; this is a fresh run. |
| Anything else starting with `proxy:` | Unexpected proxy error. | Email hi@meetcaddy.com with the full error text and the timestamp. |

### Claude Code's own auth errors (not Caddy)

These are errors from Claude Code itself, before the Caddy plugin even runs. They look like Caddy errors because they show up in response to `/caddy:draft`, but the fix is on the Claude Code side.

| Error message | What it means | What you do |
|---|---|---|
| `Please run /login` + `API Error: 401 Invalid authentication credentials` | Claude Code's own session token is missing or expired on this machine. The Caddy plugin never got a chance to run. | Inside your Claude Code session, type `/login` and complete the browser sign-in flow. Then retry `/caddy:draft`. |
| Slash command `/caddy:draft` not recognized | The plugin didn't load. | Run `/plugin` and verify `caddy` shows as installed. If not, run `/plugin install caddy@meet-caddy` again. If it shows installed but the command still doesn't appear, run `/reload-plugins`. |

### Install-level errors (rare)

If you see a totally different error (`command not found: node`, JSON parse error, etc.), it's an install issue rather than a server issue. Check that Node.js 18 or higher is on your PATH (`node --version`) and that `bin/caddy-mcp-proxy.mjs` is executable. Then email hi@meetcaddy.com.

---

## Uninstall

To remove the plugin from Claude Code, run inside a session:

```
/plugin uninstall caddy@meet-caddy
```

If you also want to remove the marketplace registration (so Caddy no longer shows up in `/plugin marketplace list`):

```
/plugin marketplace remove meet-caddy
```

You can also unset the env var by removing the `export CADDY_BEARER_TOKEN` line from your shell profile and reloading the shell. Your `~/.caddy/voice.md` and `~/.caddy/brand.md` files are yours; they are NOT touched by uninstall. Delete them manually if you want a clean wipe.

Cancelling your Caddy subscription is a separate flow (email hi@meetcaddy.com). Uninstalling the plugin does not cancel billing, and revoking your bearer token is a separate operator action on our end.

---

## Support

Compromise reports, install help, billing questions, feature requests: **hi@meetcaddy.com**. v1.0 is invite-only, so this address is monitored personally by Tucker.

When reporting an issue, include:
- Timestamp (your local time + timezone)
- The exact error text or `proxy:` message (see the failure tables above)
- Your account email
- Claude Code version (`claude --version`)
- Your OS and version (macOS or Windows)

Do **not** include your bearer token in support emails. We do not need it to debug; if we do, we will ask via a secure channel.

---

## What this plugin does NOT do

- It does not auto-update silently. Bumps go out as new marketplace versions; you re-run `/plugin install caddy@meet-caddy` to pick them up.
- It does not store voice/brand markdown anywhere besides your local `~/.caddy/`. Those files live on your machine; back them up yourself.
- It does not log anything beyond what Claude Code itself logs in your session.
- It runs on macOS and Windows. Linux is not supported.
- All v1.0 anchor skills (`/caddy:intake`, `/caddy:triage`, `/caddy:start-of-day`, `/caddy:prep`, `/caddy:followup`) are supported, alongside `/caddy:draft` and `/caddy:settings`.

---

## Known limitations

A few rough edges to be aware of. None are blockers, but they affect how you'll interact with the plugin day to day.

- **Caddy runs on your own Claude session — no Anthropic API key.** You do not set or pay for an `ANTHROPIC_API_KEY`. If Claude Code ever asks about an API key for the MCP server, hit Enter to skip; Caddy does not need one.
  - **If you see `Please run /login`:** Claude Code's own sign-in is missing or expired (common on a fresh install). Type `/login` inside Claude Code, complete the browser sign-in, and retry. This is purely a Claude Code thing; the Caddy plugin is unaffected.

- **Env vars must be exported in the same shell that launches Claude Code.** If you start Claude Code from one terminal and your `export CADDY_BEARER_TOKEN` line lives in `~/.bashrc` but you launched from a zsh session (or vice versa), the plugin won't see the token. Use `echo $CADDY_BEARER_TOKEN` in the same terminal *before* launching Claude Code to verify it's set.

- **`/caddy:draft`, `/caddy:settings`, `/caddy:intake`, `/caddy:triage`, `/caddy:start-of-day`, `/caddy:prep`, and `/caddy:followup` are ALL shipped.** That's the full v1.0 anchor skills set. v1.1+ ports the remaining 38+ skills.

- **Only one customer-settable key in v1.0: `connector` (modes: `anthropic-connector` or `copy-paste`).** Additional settings — voice strictness, model preference, draft length, etc. — ship in v1.1+. The config file schema includes a `schemaVersion` field so future settings can be added without breaking existing customer config.

- **Concurrent drafts are not isolated.** If you fire two `/caddy:draft` calls back-to-back without waiting for the first to finish, the second one will queue rather than parallelize cleanly. Wait for the first stream to complete.

- **Auto-update is opt-in.** Marketplace installs pin to the SHA listed in `marketplace.json` at install time. Re-running `/plugin install caddy@meet-caddy` pulls whatever is currently tagged in the marketplace; nothing happens silently in the background.

- **Marketplace URL is not load-bearing.** The public mirror at `github.com/meetcaddy/caddy-plugin` contains only this thin shim. The real Caddy IP (skills, frameworks, prompts, voice tuning) lives on Caddy's private server and is only reachable with a valid `CADDY_BEARER_TOKEN`. Cloning the mirror by itself gets you nothing.

---

## Under the hood (for curious operators)

The plugin ships a small Node.js stdio-to-HTTP proxy at `bin/caddy-mcp-proxy.mjs` (about 100 lines, zero third-party dependencies). It reads only `CADDY_BEARER_TOKEN` from the shell environment and forwards MCP requests to Caddy's server at https://api.meetcaddy.com/api/mcp with that bearer attached for a license check. Caddy is single-billing: the `/api/mcp` endpoint validates your license only — it performs no model generation. The actual drafting and operator-rhythm work is done by the self-contained skill files running inside your own Claude Code session on your existing Claude subscription. Node.js 18 or higher is required (built-in `fetch`).

Your bearer token is your Caddy license. There is no Anthropic API key in the flow, and Caddy never makes a model call on your behalf — generation happens in your own Claude Code session.

---

## Developer mode (local install, for Caddy team only)

If you are working on the plugin source itself rather than consuming the marketplace build, you can install directly from a local checkout:

```sh
chmod +x ./bin/caddy-mcp-proxy.mjs
claude --plugin-dir ./
```

This bypasses the marketplace and runs whatever is on disk. Not for customers. The marketplace install path above is the supported flow.

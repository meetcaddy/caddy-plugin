# Caddy plugin (v0.1.4)

> **Invite-only v1.0.** Caddy is currently a closed-pilot SaaS for a small group of operators. If you do not have a bearer token from Tucker, you cannot use this plugin yet. Contact hi@meetcaddy.com to request access.

Caddy. Your unfair advantage. Voice-fingerprinted drafts, powered by the Caddy backend.

This plugin is the thin Claude Code surface for the Caddy SaaS. The actual prompt logic, voice tuning, and model routing live on Caddy's servers; this plugin just routes your slash commands to them and renders the streamed output in your local Claude Code session.

---

## Prerequisite

Claude Code (CLI or IDE extension) installed and authenticated.

If you do not have Claude Code yet, install it first: see https://docs.claude.com/en/docs/claude-code/quickstart. Then come back here.

---

## What you need

Two long-lived secrets, both exported as environment variables in the shell that launches Claude Code:

1. **`CADDY_BEARER_TOKEN`** — your Caddy account token. Issued via a one-time exchange URL Tucker sends after invite approval. The URL is good for a single click; you redeem it to receive the bearer token in your browser, then paste the token into your shell profile (or `.env`). Treat the bearer token like a password.

2. **`ANTHROPIC_API_KEY`** — your own Anthropic API key from https://platform.anthropic.com. Caddy uses BYOK (bring your own key); you pay Anthropic directly for the model usage, and Caddy never stores this key on its servers (per-request only).

---

## Install (macOS only for v0.1.0)

> **Editor note:** if your terminal doesn't have the `code` shell command (typical on a fresh Mac), substitute `open -e` in the commands below. `open -e ~/.zshrc` opens the file in TextEdit. To create an empty file first if it doesn't exist: `touch ~/.zshrc && open -e ~/.zshrc`. If you'd rather install the `code` CLI: open VS Code, press Cmd+Shift+P, type "shell command", pick **Shell Command: Install 'code' command in PATH**.

> **TextEdit warning:** before editing `~/.zshrc` or your voice/brand files in TextEdit, turn off Smart Quotes (Edit → Substitutions → uncheck Smart Quotes). TextEdit otherwise silently converts straight `"` to curly `"` which breaks shell config files and degrades voice fingerprint matching.

1. Export your two secrets in your shell profile so every Claude Code session inherits them:

   ```sh
   # in ~/.zshrc or ~/.bashrc
   export CADDY_BEARER_TOKEN="caddy_..."        # from Tucker's exchange URL
   export ANTHROPIC_API_KEY="sk-ant-..."         # from platform.anthropic.com
   ```

   Reload your shell: `source ~/.zshrc` (or close and reopen the terminal).

   Verify both are set:
   ```sh
   echo "Bearer: ${CADDY_BEARER_TOKEN:0:8}..."
   echo "Anthropic: ${ANTHROPIC_API_KEY:0:8}..."
   ```
   Both should print something (the `:0:8` only shows the first 8 chars; full token isn't echoed).

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

   The first command registers Caddy's plugin catalog. The second downloads the plugin into your Claude Code session (sparse clone of the `plugin/` folder, pinned to the v0.1.0 commit).

4. **When Claude Code prompts you about an API key for the MCP server, answer "No"** (or hit Enter to skip). Caddy reads `ANTHROPIC_API_KEY` from your shell environment directly. If you paste it into the prompt, Claude Code stores it in plugin config instead, which can confuse rotation later. See "Known limitations" below for context.

5. Test:

   ```
   /caddy:draft Write a 3-paragraph LinkedIn post announcing my Q4 product update.
   ```

   You should see the draft stream in line by line, in your voice.

---

## First-time setup (recommended)

If this is your first time using Caddy on this machine, run `/caddy:intake` once. It interviews you for ~5-10 minutes about your voice and your brand, then writes `~/.caddy/voice.md` and `~/.caddy/brand.md` to your disk. `/caddy:draft` uses those files on every call. You can skip intake and write the markdown yourself if you prefer; the format is documented in `plugin/skills/intake/SKILL.md`.

```
/caddy:intake
```

Your interview answers stay local on your machine. They only leave when you later run `/caddy:draft` (which sends voice + brand context to Caddy's backend and your Anthropic key for that one draft call; nothing persisted on either side).

---

## Configure (optional)

Caddy ships with a local-only settings command for tuning plugin behavior. Settings persist to `~/.caddy/config.json` and are local to your machine. Caddy's backend never sees them.

```
/caddy:settings show                            # display current config
/caddy:settings set connector anthropic-connector   # tell Caddy you use Anthropic-hosted Gmail/Calendar/Drive connectors
/caddy:settings unset connector                 # clear a setting
```

Available settings in v0.1.3:
- `connector` — values: `anthropic-connector` or `copy-paste`. Optional. Future anchor skills (intake, triage, etc.) will branch on this; `/caddy:draft` does not read it in v0.1.3.

---

## Secret hygiene

**Do NOT** paste `CADDY_BEARER_TOKEN` or `ANTHROPIC_API_KEY` into:
- Any chat interface, including Claude.ai conversations or other AI assistants
- Any git repository (even private; rotate immediately if pushed)
- Any screenshot for support (redact before sharing)
- Any `echo` or `cat` command that prints them to your terminal scrollback

If you have done any of the above, treat the affected token as compromised and rotate it immediately (see "Credential lifecycle" below).

The Caddy bearer token is long-lived; it does not expire on a schedule. The Anthropic API key is long-lived too. Both must be rotated manually if compromised.

---

## Credential lifecycle

### Caddy bearer token

If you suspect your bearer token is leaked, email **hi@meetcaddy.com** immediately with subject line `Bearer token rotation request`. Include your account email. Tucker will revoke the old token and issue a fresh one-time exchange URL. Existing Claude Code sessions will start returning auth errors until you swap the new token into your env vars.

### Anthropic API key

If you suspect your Anthropic key is leaked, revoke it yourself at https://platform.anthropic.com/settings/keys. Generate a new key on the same page. Update `ANTHROPIC_API_KEY` in your shell profile, reload your shell, and restart Claude Code. Caddy does not need to be involved; we never stored your key.

---

## First-call failure table

If `/caddy:draft` returns an error, here is what each code means and what to do:

| Code | What it means | What you do |
|---|---|---|
| `invalid_api_key` | Your `ANTHROPIC_API_KEY` was rejected by Anthropic. | Check the env var is exported in the same shell Claude Code runs in. Verify the key is active at https://platform.anthropic.com/settings/keys. |
| `permission_denied` | Your Anthropic key works but lacks permission for the requested model. | Check your Anthropic account tier and model access. |
| `invalid_request` | Caddy sent Anthropic a malformed request. | Likely a Caddy bug. Email hi@meetcaddy.com with the timestamp. |
| `not_found` | The model or resource Caddy asked for does not exist. | Your plugin version may be out of date. Update the plugin source, or contact hi@meetcaddy.com. |
| `upstream_rate_limited` | Anthropic rate-limited the request. | Wait 60 seconds and retry. If persistent, your Anthropic account may need a higher rate tier. |
| `upstream_unavailable` | Anthropic is unreachable or timed out (Caddy has a 55-second budget per draft). | Try again shortly. If persistent on multiple drafts, check Anthropic status. |
| `internal` | Caddy hit an internal error. | Try again. If persistent, email hi@meetcaddy.com with the timestamp; do NOT include the bearer token or Anthropic key. |

### Errors from the plugin's local proxy (start with `proxy:`)

These come from the small Node script that bridges Claude Code to the Caddy backend.

| Message starts with | What it means | What you do |
|---|---|---|
| `proxy: upstream 401` | Your `CADDY_BEARER_TOKEN` was rejected by Caddy (wrong, expired, or revoked). | Verify the env var matches the bearer you received from your exchange URL. If it does and still fails, your token may have been rotated. Email hi@meetcaddy.com to reissue. |
| `proxy: upstream 4xx` (other 4xx) | Caddy rejected the request (rare; typically a malformed call). | Try again. If it persists, email hi@meetcaddy.com with the timestamp. |
| `proxy: upstream 5xx` | Caddy backend is having problems. | Wait 60 seconds and retry. If persistent across multiple drafts, email hi@meetcaddy.com. |
| `proxy: could not reach Caddy server (ENOTFOUND \| ECONNREFUSED \| ETIMEDOUT)` | Network connectivity issue (DNS, firewall, or Caddy is down). | Check your internet connection. If you're behind a corporate firewall, the proxy needs outbound HTTPS to `caddy-app-tbern75s-projects.vercel.app`. If your network is fine, Caddy itself may be down — wait, then retry. |
| `proxy: stream interrupted` | The streaming response was cut off mid-flight (network blip, laptop sleep, etc.). | Try again. The draft was not delivered; this is a fresh run. |
| Anything else starting with `proxy:` | Unexpected proxy error. | Email hi@meetcaddy.com with the full error text and the timestamp. |

### Claude Code's own auth errors (not Caddy)

These are errors from Claude Code itself, before the Caddy plugin even runs. They look like Caddy errors because they show up in response to `/caddy:draft`, but the fix is on the Claude Code side.

| Error message | What it means | What you do |
|---|---|---|
| `Please run /login` + `API Error: 401 Invalid authentication credentials` | Claude Code's own session token is missing or expired on this Mac. The Caddy plugin never got a chance to run. | Inside your Claude Code session, type `/login` and complete the browser sign-in flow. Then retry `/caddy:draft`. |
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

You can also unset your env vars by removing the two `export` lines from your shell profile and reloading the shell. Your `~/.caddy/voice.md` and `~/.caddy/brand.md` files are yours; they are NOT touched by uninstall. Delete them manually if you want a clean wipe.

Cancelling your Caddy subscription is a separate flow (email hi@meetcaddy.com). Uninstalling the plugin does not cancel billing, and revoking your bearer token is a separate operator action on our end.

---

## Support

Compromise reports, install help, billing questions, feature requests: **hi@meetcaddy.com**. v1.0 is invite-only, so this address is monitored personally by Tucker.

When reporting an issue, include:
- Timestamp (your local time + timezone)
- The exact error code (from the failure table above) or error text
- Your account email
- Claude Code version (`claude --version`)
- macOS version

Do **not** include your bearer token or Anthropic API key in support emails. We do not need them to debug; if we do, we will ask via a secure channel.

---

## What this plugin does NOT do (v0.1.0)

- It does not auto-update silently. Bumps go out as new marketplace versions; you re-run `/plugin install caddy@meet-caddy` to pick them up.
- It does not store voice/brand markdown anywhere besides your local `~/.caddy/`. Those files live on your machine; back them up yourself.
- It does not log anything beyond what Claude Code itself logs in your session.
- It does not work on Windows or Linux yet (macOS first; other platforms after the v1.0 pilot).
- It does not support anchor skills (`/caddy:triage`, `/caddy:prep`, `/caddy:start-of-day`, `/caddy:followup`) yet. Those land in v0.2.0+. `/caddy:settings` is supported as of v0.1.3 and `/caddy:intake` is supported as of v0.1.4.

---

## Known limitations (v0.1.0)

A few rough edges to be aware of. None are blockers, but they affect how you'll interact with the plugin day to day.

- **Claude Code may prompt about your `ANTHROPIC_API_KEY` when it launches.** The prompt typically reads "Detected `ANTHROPIC_API_KEY` in environment. Use this for your Claude Code session?" with Yes/No options.
  - **If you're on Claude Max (subscription):** answer **No**. Your env var stays available to the Caddy plugin's proxy regardless of what Claude Code uses for itself, and saying Yes would route Claude Code's own usage through your API key, which double-bills against your Max sub.
  - **If you're on pay-per-token Anthropic API only (no Max):** answer **Yes**. That tells Claude Code to use your API key for its own usage too. Either way, Caddy still reads the env var directly via the proxy.
  - **If after answering "No" you see `Please run /login`:** Claude Code's OAuth session is missing or expired on this Mac (common on a fresh install). Type `/login` inside Claude Code, complete the browser sign-in, and retry. This is purely a Claude Code thing; the Caddy plugin is unaffected.

- **Env vars must be exported in the same shell that launches Claude Code.** If you start Claude Code from one terminal and your `export` lines live in `~/.bashrc` but you launched from a zsh session (or vice versa), the plugin won't see the secrets. Use `echo $CADDY_BEARER_TOKEN` and `echo $ANTHROPIC_API_KEY` in the same terminal *before* launching Claude Code to verify they're set.

- **`/caddy:draft`, `/caddy:settings`, and `/caddy:intake` are the commands shipped as of v0.1.4.** No `/caddy:triage`, no `/caddy:prep`, no `/caddy:start-of-day`, no `/caddy:followup` yet. Those ship in v0.2.0+.

- **Only one customer-settable key in v1.0: `connector` (modes: `anthropic-connector` or `copy-paste`).** Additional settings — voice strictness, model preference, draft length, etc. — ship in v1.1+. The config file schema includes a `schemaVersion` field so future settings can be added without breaking existing customer config.

- **Concurrent drafts are not isolated.** If you fire two `/caddy:draft` calls back-to-back without waiting for the first to finish, the second one will queue rather than parallelize cleanly. Wait for the first stream to complete.

- **Auto-update is opt-in.** Marketplace installs pin to the SHA listed in `marketplace.json` at install time. Re-running `/plugin install caddy@meet-caddy` pulls whatever is currently tagged in the marketplace; nothing happens silently in the background.

- **Marketplace URL is not load-bearing.** The public mirror at `github.com/meetcaddy/caddy-plugin` contains only this thin shim. The real Caddy IP (skills, frameworks, prompts, voice tuning) lives on Caddy's private server and is only reachable with a valid `CADDY_BEARER_TOKEN`. Cloning the mirror by itself gets you nothing.

---

## Under the hood (for curious operators)

The plugin ships a small Node.js stdio-to-HTTP proxy at `bin/caddy-mcp-proxy.mjs` (about 100 lines, zero third-party dependencies). The proxy reads `CADDY_BEARER_TOKEN` and `ANTHROPIC_API_KEY` from the shell environment, then forwards each MCP request to Caddy's MCP server at https://caddy-app-tbern75s-projects.vercel.app/api/mcp with those values attached as request headers. SSE streaming responses are parsed and forwarded to stdout line by line. All draft generation happens server-side using Anthropic Claude Sonnet 4.6, streamed back via the MCP `notifications/message` channel. Node.js 18 or higher is required (built-in `fetch`).

Your bearer token authenticates you to Caddy. Your Anthropic key pays for the model call. Caddy stores neither.

---

## Developer mode (local install, for Caddy team only)

If you are working on the plugin source itself rather than consuming the marketplace build, you can install directly from a local checkout:

```sh
chmod +x ./bin/caddy-mcp-proxy.mjs
claude --plugin-dir ./
```

This bypasses the marketplace and runs whatever is on disk. Not for customers. The marketplace install path above is the supported flow.

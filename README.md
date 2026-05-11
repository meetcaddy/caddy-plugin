# Caddy plugin (public mirror)

This repository is the public distribution mirror for the **Caddy** Claude Code plugin. It contains only the thin plugin shim that customers install into their Claude Code; the Caddy backend (prompts, skills, frameworks, methodology) lives on a separate private server and is accessed via remote MCP calls.

## For Caddy customers

If you have received an invite from Caddy, install the plugin inside Claude Code:

```sh
/plugin marketplace add meetcaddy/caddy-plugin
/plugin install caddy@meet-caddy
```

You will also need:
- A Caddy bearer token (issued by us via your one-time exchange URL)
- An Anthropic API key (from https://platform.anthropic.com)

Full install instructions, troubleshooting, and credential management lives in `plugin/README.md` inside this repo. Read that before running your first `/caddy:draft` call.

## For the curious

This mirror contains:
- `.claude-plugin/marketplace.json` — the Claude Code marketplace catalog that lists Caddy
- `plugin/` — the plugin shim Claude Code installs (a ~250-line manifest + stdio→HTTPS proxy + skill markdown)

It does NOT contain Caddy's actual prompts, skills, agents, frameworks, or any of the methodology that defines the product. Those live on Caddy's servers behind authentication. Cloning this repo gives you a transport-layer shim that is useless without a valid Caddy account.

## License

Use of this plugin requires an active Caddy subscription. © 2026 Orbital Access LLC d/b/a Meet Caddy. All rights reserved. Customers receive a non-transferable, revocable license to install and use the plugin while their subscription is active.

## Sync

This mirror is auto-synced from the private Caddy backend repository on each tagged release. Do not open pull requests here; the source-of-truth lives elsewhere. Issues + support: hi@meetcaddy.com.

---
description: "Wire a new MCP integration into Caddy from a plain-language need, safely. Maps what you want to do ('send invoices', 'read my CRM', 'post to social') to a Caddy-VETTED MCP server from a curated allowlist, writes the config, prompts you to paste secrets into the env file yourself (never into chat), and runs caddy-agent-audit as a mandatory gate before anything goes live. Refuses to install unvetted servers by name or route business data to non-Anthropic models. Triggers: 'caddy connect', 'connect my <tool>', 'wire up <CRM/email/calendar/etc.>', 'add an integration', 'set up an MCP for X', 'what MCP do I need for Y'."
---

# /caddy:connect: vetted, conversational MCP wiring

Most "AI MCP installers" run any npm/PyPI package by name and let you paste secrets into the chat. That
is exactly how an AI setup leaks credentials or installs a hostile server. `/caddy:connect` does the
opposite: it maps your *need* to a **Caddy-vetted server**, gates the install with a security scan, and
keeps secrets out of the conversation.

## The flow
1. **Understand the need.** Ask what the user wants to *do* (the job), not which tool. ("I want to send
   client emails" → email MCP; "manage my pipeline" → CRM MCP.)
2. **Map to a vetted server** from the allowlist below. If the need maps to something NOT on the
   allowlist, say so and offer to (a) check the Caddy MCP registry for a vetted match, or (b) flag it for
   review. Do NOT install an unvetted server by name.
3. **Write the config** into the user's MCP config (project or user scope as appropriate). Show the exact
   block before writing.
4. **Secrets stay out of chat.** Tell the user the exact env var(s) needed and the file path to paste
   them into themselves (e.g. `~/.caddy/<server>.env`). NEVER accept a secret pasted into the
   conversation; if one is pasted, tell them it's now compromised and to rotate it.
5. **MANDATORY gate:** run `caddy-agent-audit` against the new config + the server's command/env before
   declaring it live. If it flags a leaked secret, an injection-capable hook, or a risky command, STOP
   and surface it.
6. **Restart + verify.** Tell the user to restart Claude Code (hooks/servers register at start), then
   confirm the server's tools load.

## Caddy-vetted allowlist (v1)
| Need | Vetted server | Secret (paste into env, not chat) | Notes |
|---|---|---|---|
| Email (send/draft) | Nylas | Nylas grant/API key | Caddy default email path |
| CRM / pipeline / contacts | GoHighLevel (official) | Private Integration Token | one per sub-account |
| Social posting | Buffer | Buffer access token | |
| Calendar / Docs / Drive | Google (Calendar/Docs/Drive) | OAuth (user-run) | Caddy does not host OAuth |
| Meeting recordings | Fathom | Fathom token | read-only |
| Database (read) | Postgres / Supabase | connection string (read-only role) | least-privilege only |
| Notion / Airtable / Slack / Stripe | (review-then-add) | per-vendor | vet via caddy-agent-audit before adding to allowlist |

## Hard rules
- **Never** install an arbitrary npm/PyPI MCP by name on request. Allowlist or registry-vetted only.
- **Never** route business data to a non-Anthropic model (no model-router/aggregator servers that egress
  data, keeps the client's Annex III / sub-processors lean).
- **Never** accept secrets in chat: env file only; least-privilege credentials (read-only DB roles, etc.).
- `caddy-agent-audit` gate is mandatory before "live." No gate, no go.
- If unsure a server is safe, default to NOT installing and flag for review.

## Why this is the Caddy way
The allowlist + audit gate + secrets-out-of-chat is the moat vs open-source installers. It's *safe by
construction*, which is what an owned, admin-level-deployed system on the client's own plan requires.
Pairs with the ACE Exec Pack (whose agents need the client's stack wired to take action).

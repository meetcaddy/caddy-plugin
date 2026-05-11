---
description: Draft content in the operator's voice and brand. Use when the user types /caddy:draft or asks Caddy to write something (LinkedIn post, email, memo, etc.) that should sound like them. Requires the user's voice fingerprint at ~/.caddy/voice.md and brand context at ~/.caddy/brand.md.
---

# Caddy: Draft

Draft content in the operator's voice and brand by calling the `caddy.draft` MCP tool.

## Pre-flight

Before invoking the tool, read these two local files from the user's home directory:

1. `~/.caddy/voice.md` — voice fingerprint markdown. If the file is missing, stop and tell the user: "I need your voice fingerprint at ~/.caddy/voice.md before I can draft in your voice. Run /caddy:intake first, or paste 200+ words of your writing into that file." Do not invoke the tool without voice content.

2. `~/.caddy/brand.md` — brand context markdown. If the file is missing, stop and tell the user: "I need brand context at ~/.caddy/brand.md before I can draft. Paste 100+ words about your brand into that file." Do not invoke the tool without brand content.

## Invoke

Call the `caddy.draft` MCP tool with these arguments:

- `topic` — `$ARGUMENTS` (the prompt the user typed after `/caddy:draft`; if empty, ask the user what they want drafted before invoking)
- `voice` — the full contents of `~/.caddy/voice.md`
- `brand` — the full contents of `~/.caddy/brand.md`
- `audience` — optional; only set if the user named one (e.g., "for my LinkedIn network")
- `length_hint` — optional; only set if the user named a length (`short`, `medium`, or `long`)

## Stream the result

The tool streams chunks via MCP `notifications/message` events as the model writes. Surface those chunks inline to the user as they arrive. The final tool result contains the complete assembled draft; deliver that as the canonical output.

If you see a small inline JSON blob containing `"__caddy_meta":"usage"`, that is token-usage telemetry. Do not surface it as output; ignore it silently or render it as a discreet note (operator's choice).

## On error

The `caddy.draft` tool returns errors with a structured code from Caddy's error translator. Map them for the user:

- `invalid_api_key` — "Your ANTHROPIC_API_KEY was rejected. Check that it is exported in this shell and is valid at platform.anthropic.com."
- `permission_denied` — "Your Anthropic key lacks permission for the requested model. Check your Anthropic account access tier."
- `invalid_request` — "Caddy rejected the request as malformed. This is likely a Caddy bug; report at hi@meetcaddy.com."
- `not_found` — "Caddy could not find the requested model. The plugin may be out of date. Run /plugin update caddy or contact hi@meetcaddy.com."
- `upstream_rate_limited` — "Anthropic rate-limited the request. Wait a minute and try again. If persistent, your Anthropic account may need a higher tier."
- `upstream_unavailable` — "Anthropic is unreachable or timed out. Try again shortly."
- `internal` — "Caddy hit an internal error. Try again; if persistent, contact hi@meetcaddy.com with the timestamp."

If the error message starts with `proxy:` (e.g., `proxy: upstream 401`, `proxy: could not reach Caddy server`), it came from the local plugin bridge, not from Caddy's backend tool layer. Surface it as:

- `proxy: upstream 401` — "Your Caddy bearer token was rejected. Verify CADDY_BEARER_TOKEN matches the value from your exchange URL. If it does, email hi@meetcaddy.com for a new token."
- `proxy: upstream 5xx` — "Caddy backend is having problems. Wait a minute and try again. If persistent, email hi@meetcaddy.com."
- `proxy: could not reach Caddy server` — "Network or firewall issue. Check internet, then check whether caddy-app-tbern75s-projects.vercel.app is reachable. Retry once connectivity is back."
- `proxy: stream interrupted` — "The streaming response was cut off mid-flight. The draft did not complete. Try again."
- Any other `proxy:` error — "Unexpected plugin bridge error. Email hi@meetcaddy.com with the full message and timestamp."

Do not retry automatically; tell the user what happened and let them decide.

## Hard rules

- Do not invent voice or brand content. If the local files are missing, stop and ask.
- Do not call the tool more than once per user request unless the user explicitly asks for a revision.
- Do not log the bearer token, the Anthropic key, or the streamed draft to any persistent location. The draft is the user's content; their session transcript holds it.

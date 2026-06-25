---
name: caddy-agent-audit
description: Security-audit an AI agent harness configuration. Scans CLAUDE.md, settings.json, .mcp.json, hooks, and skills for leaked secrets, dangerous hook commands, risky permissions, and MCP exposure. Use to harden your own Claude Code setup, or as an ACE deliverable to security-audit a client's AI configuration. Read-only; never executes anything it finds.
allowed-tools: Bash, Read
---

# caddy-agent-audit (Caddy's AgentShield)

Most people secure their *code* and never look at their *agent config*, where a leaked token, an
injected hook, or a wide-open permission can do real damage. This scans the harness itself.

Read-only.

## What it checks
- **Secrets** in config files (OpenAI/Anthropic `sk-`, GitHub `ghp_`, AWS `AKIA`, GHL `pit-`, Slack
  `xox*`, inline Bearer tokens, private-key blocks, plaintext password/secret/api_key assignments).
- **Dangerous hook commands** (settings.json / hooks): `rm -rf`, `curl|bash`, `eval`, `--no-verify`,
  `core.hooksPath` overrides, `chmod 777`.
- **Risky permissions** (`dangerouslySkipPermissions`, `skipDangerousModePermissionPrompt`, `Bash(*)`,
  blanket `allow: ["*"]`).
- **Hook-event surface (v0.3):** parses the `hooks` block and flags **injection-capable events**
  (PreToolUse, UserPromptSubmit, PermissionRequest, ConfigChange, SessionStart, InstructionsLoaded,
  MessageDisplay, Elicitation/ElicitationResult, etc.; validated against the current Claude Code hooks
  docs). Configuring one is INFO ("verify the handler is trusted"); it then **follows each handler
  script** and raises severity when the handler *actively* mutates: HIGH for permission auto-approve /
  mode-switch (`behavior: allow`, `updatedPermissions`, `setMode`) or tool-input rewrite (`updatedInput`),
  MEDIUM for context injection (`additionalContext`) or output/turn suppression (`decision: block`).
  HTTP hooks are flagged as exfil surface (CRITICAL when they forward env vars).
- **MCP exposure** (secrets inline in server headers/env).

## Run
```bash
# Scan your own setup (~/.claude, ~/.mcp.json, ~/.claude.json):
python3 "$CLAUDE_PLUGIN_ROOT/skills/caddy-agent-audit/scan.py"
# Also scan a project's config (great for an ACE client audit):
python3 "$CLAUDE_PLUGIN_ROOT/skills/caddy-agent-audit/scan.py" --target "/path/to/project"
```
Output: findings ranked CRITICAL to INFO, each with file:line + a fix note, plus a summary count.

## Two uses
1. **Internal (Client-Zero):** run it on your own config; rotate anything flagged, lock files to `chmod 600`.
2. **ACE deliverable:** run it on a client's AI setup as part of the audit: "here's where your AI
   configuration leaks secrets or grants dangerous permissions, and how to fix it." That's the
   auditability wedge, made concrete and sellable.

## Notes
- Secrets in a *local* config (e.g. `~/.mcp.json` holding an MCP token) are *expected* for auth. The
  finding is a reminder to keep the file `chmod 600` and never commit it, not necessarily a breach.
- v0.3: pattern-based + hook-event-surface analysis (follows handler scripts). Roadmap: A2 PreToolUse
  *detect-and-prevent* safety bundle (block live secret-writes / key reads / destructive bash before
  execution), an `--opus` adversarial red-team pass, and full hook-injection dataflow analysis.

---
description: "Check a Caddy install end to end and report, in plain language, exactly what is wrong and the precise fix. Read-only: diagnoses, never changes anything. Run anytime something is off (most useful right after install, equally useful later). Triggers: 'verify caddy', 'check my caddy', 'is caddy working', 'caddy doctor', 'caddy not working', 'slash commands missing', 'proxy upstream 401', 'caddy-mcp failed', 'base-mcp failed', 'carl-mcp failed', 'draft doesn't sound like me', 'is my license working', install health check, post-install check."
---

# /caddy:verify

Run a full health check of this Caddy install and report each item as
**PASS**, **FAIL**, or **WARN**, with the exact fix for anything wrong.

This is the second half of the install story. The Terminal installer
handles the bare-machine half; this skill checks everything that lives
inside Claude Code (plugin, license, frameworks, voice, workspace
wiring) which the Terminal cannot see.

This skill is strictly **read-only**. It inspects state and tells you
what to do. It never installs, edits, moves, or deletes anything. Every
fix it prints is a command you choose to run yourself.

## What it checks (each maps to a known support case)

1. The six Caddy frameworks are installed via Homebrew.
2. The framework links in `~/.claude/` exist and are not blocked by a
   pre-existing file (the collision case).
3. The license token is set and is actually accepted by the server.
4. Your voice and brand files exist and the voice sample is substantial.
5. This workspace's MCP servers (`base-mcp`, `carl-mcp`) are wired.
6. The CARL safety hook is registered so safety rules actually fire.

## Execution

Claude: run the block below as one script. Do NOT stop on the first
failure, a diagnostic must run every check and print a full report.
Then present the OK/FAIL/WARN lines to the user verbatim, followed by
the SUMMARY line. Do not paraphrase the fixes.

```bash
WORKSPACE="${WORKSPACE:-$(pwd)}"
PASS=0; FAILN=0; WARNN=0
ok()   { echo "PASS  $*"; PASS=$((PASS+1)); }
fail() { echo "FAIL  $*"; FAILN=$((FAILN+1)); }
warn() { echo "WARN  $*"; WARNN=$((WARNN+1)); }
PY="$(command -v python3 || true)"

echo "Caddy verify — read-only health check"
echo "workspace: $WORKSPACE"
echo "----------------------------------------"

# 1. Frameworks installed (support case: slash commands do not appear)
MISSING_F=""
for f in caddy-base caddy-carl caddy-paul caddy-seed caddy-skillsmith caddy-aegis; do
  brew list "$f" >/dev/null 2>&1 || MISSING_F="$MISSING_F $f"
done
if [ -z "$MISSING_F" ]; then
  ok "all 6 Caddy frameworks installed via Homebrew"
else
  fail "missing Homebrew formulas:$MISSING_F"
  echo "      Fix: brew tap meetcaddy/caddy && brew install caddy-frameworks"
fi

# 2. ~/.claude links + collision (support case 7.3 / 7.7b)
# Only meaningful if the Homebrew frameworks are installed: a caddy-link
# collision can only exist when caddy-link is the install mechanism. If
# the formulas are absent, a directory at these paths is NOT a Caddy
# collision (it may be a legitimate non-Homebrew install). Telling the
# user to move it would be destructive, so this check is gated on #1.
if [ -n "$MISSING_F" ]; then
  warn "framework links: skipped (frameworks not installed; fix item 1 first)"
else
  COLLISION=0; MISSINGLINK=0
  for p in commands/base commands/paul commands/seed commands/skillsmith commands/aegis skills/base base-framework paul-framework skillsmith-specs aegis; do
    T="$HOME/.claude/$p"
    if [ -L "$T" ]; then :
    elif [ -e "$T" ]; then
      COLLISION=1
      echo "      occupied (not a Caddy link): $T"
      echo "        If this is YOUR content, leave it. If you intend to use the"
      echo "        Homebrew install path and it is leftover, move it aside then"
      echo "        re-run caddy-link:  mv \"$T\" \"$T.bak\""
    else
      MISSINGLINK=1
    fi
  done
  if [ "$COLLISION" -eq 1 ]; then
    fail "framework links blocked: a path is occupied by a non-Caddy file (inspect before moving, see above)"
  elif [ "$MISSINGLINK" -eq 1 ]; then
    warn "some framework links are absent. Fix: run caddy-link"
  else
    ok "framework links in ~/.claude/ are present and clean"
  fi
fi

# 3. License token present + accepted (support case 7.1: proxy upstream 401)
URL="${CADDY_MCP_URL:-https://caddy-app-tbern75s-projects.vercel.app/api/mcp}"
if [ -z "${CADDY_BEARER_TOKEN:-}" ]; then
  fail "CADDY_BEARER_TOKEN is not set in this shell"
  echo "      Fix: export the token from your welcome email, then restart"
  echo "      Claude Code. Add it to ~/.zshrc or ~/.bashrc to make it stick."
else
  CODE="$(curl -s -o /dev/null -w '%{http_code}' -m 10 -H "Authorization: Bearer $CADDY_BEARER_TOKEN" "$URL" 2>/dev/null || echo 000)"
  if [ "$CODE" = "401" ]; then
    fail "license token is set but the server rejected it (401)"
    echo "      Means: token is wrong, expired, or was revoked."
    echo "      Fix: re-copy the token from your welcome email. If it still"
    echo "      fails, your license may be revoked, contact hi@meetcaddy.com."
  elif [ "$CODE" = "000" ]; then
    warn "could not reach the license server (network/offline?). Token is set; re-run when online."
  else
    ok "license token is set and accepted by the server"
  fi
fi

# 4. Voice + brand files (support cases 7.2 / 7.4)
VOICE="$HOME/.caddy/voice.md"
BRAND="$HOME/.caddy/brand.md"
if [ ! -f "$VOICE" ] || [ ! -f "$BRAND" ]; then
  fail "voice or brand profile missing in ~/.caddy/"
  echo "      Fix: run /caddy:intake (the 10-question voice + brand interview)."
else
  WC="$(wc -w < "$VOICE" 2>/dev/null | tr -d ' ')"
  if [ "${WC:-0}" -lt 200 ] 2>/dev/null; then
    warn "voice.md exists but is thin (${WC:-0} words). Drafts may not sound like you."
    echo "      Fix: re-run /caddy:intake with longer, more specific answers."
  else
    ok "voice + brand profiles present (voice.md ~${WC} words)"
  fi
fi

# 5. Workspace MCP wiring (support case 7.6)
MCP_JSON="$WORKSPACE/.mcp.json"
if [ -z "$PY" ]; then
  warn "python3 not found; skipping the .mcp.json inspection"
elif [ ! -f "$MCP_JSON" ]; then
  fail "no .mcp.json in this workspace ($WORKSPACE)"
  echo "      Fix: from the project root run /caddy:base-setup then /caddy:carl-setup"
else
  MCP_REPORT="$("$PY" - "$MCP_JSON" <<'PYEOF'
import json,os,sys
try:
    data=json.load(open(sys.argv[1]))
except Exception as e:
    print("BADJSON %s" % e); sys.exit(0)
srv=data.get("mcpServers",{}) or {}
out=[]
for name in ("base-mcp","carl-mcp"):
    e=srv.get(name)
    if not e:
        out.append(name+":absent")
    else:
        args=e.get("args") or []
        p=args[0] if args else None
        out.append(name+(":ok" if p and os.path.isfile(p) else ":broken"))
print(" ".join(out))
PYEOF
)"
  case "$MCP_REPORT" in
    BADJSON*)
      fail ".mcp.json is not valid JSON (${MCP_REPORT#BADJSON })"
      echo "      Fix: re-run /caddy:base-setup and /caddy:carl-setup (they rebuild it)." ;;
    *broken*|*absent*)
      fail "workspace MCP wiring incomplete: $MCP_REPORT"
      echo "      Fix: from the project root run /caddy:base-setup then /caddy:carl-setup" ;;
    *)
      ok "workspace MCP servers wired: $MCP_REPORT" ;;
  esac
fi

# 6. CARL safety hook registered (support case 7.6 / v0.5.0 safety rules)
SETTINGS="$HOME/.claude/settings.json"
if [ -z "$PY" ]; then
  warn "python3 not found; skipping the safety-hook check"
elif [ ! -f "$SETTINGS" ]; then
  warn "no ~/.claude/settings.json; safety hook not registered"
  echo "      Fix: run /caddy:carl-setup (registers the safety hook)."
else
  HOOK="$("$PY" - "$SETTINGS" <<'PYEOF'
import json,sys
try:
    s=json.load(open(sys.argv[1]))
except Exception:
    print("badjson"); sys.exit(0)
for e in (s.get("hooks",{}) or {}).get("UserPromptSubmit",[]) or []:
    for h in e.get("hooks",[]) or []:
        if "carl-hook.py" in (h.get("command","") or ""):
            print("present"); sys.exit(0)
print("absent")
PYEOF
)"
  if [ "$HOOK" = "present" ]; then
    ok "CARL safety hook is registered (safety rules will fire)"
  elif [ "$HOOK" = "badjson" ]; then
    warn "~/.claude/settings.json is not valid JSON; cannot confirm safety hook"
    echo "      Fix: re-run /caddy:carl-setup (it backs up and rewrites safely)."
  else
    warn "CARL safety hook not registered (safety rules will NOT fire)"
    echo "      Fix: run /caddy:carl-setup (Step 7 registers the hook)."
  fi
fi

echo "----------------------------------------"
if [ "$FAILN" -eq 0 ] && [ "$WARNN" -eq 0 ]; then
  echo "SUMMARY: all clear ($PASS passed). Caddy is healthy."
elif [ "$FAILN" -eq 0 ]; then
  echo "SUMMARY: $PASS passed, $WARNN warning(s), 0 failures. Usable; address warnings above."
else
  echo "SUMMARY: $PASS passed, $WARNN warning(s), $FAILN failure(s). Fix the FAIL items above (each has a Fix line), then re-run /caddy:verify."
fi
```

## After running

Work top to bottom: every FAIL prints the exact command to fix it. Re-run
`/caddy:verify` after applying fixes until the SUMMARY says all clear.
WARN items are usable-but-worth-improving, not blockers.

## Notes

- **Read-only.** No file is created, edited, moved, or deleted. All Python
  is `json.load` only (never writes). Safe to run anytime, any number of
  times, including mid-session.
- The license check sends one authenticated request to the Caddy endpoint
  (`$CADDY_MCP_URL` or the production default) and interprets only the
  HTTP status: 401 means the token is bad/revoked, any non-401 means the
  token cleared authentication. It never prints the token.
- Run it from your project root so the workspace MCP check (`.mcp.json`)
  inspects the right directory; otherwise pass `WORKSPACE=/path`.

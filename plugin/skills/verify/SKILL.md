---
description: "Check a Caddy install end to end and report, in plain language, exactly what is wrong and the precise fix. Read-only: diagnoses, never changes anything. Run anytime something is off (most useful right after install, equally useful later). Triggers: 'verify caddy', 'check my caddy', 'is caddy working', 'caddy doctor', 'caddy not working', 'slash commands missing', 'proxy upstream 401', 'caddy-mcp failed', 'base-mcp failed', 'carl-mcp failed', 'draft doesn't sound like me', 'is my license working', install health check, post-install check."
---

# /caddy:verify

Run a full health check of this Caddy install and report each item as
**PASS**, **FAIL**, or **WARN**, with the exact fix for anything wrong.

This is the second half of the install story. The Terminal installer
handles the bare-machine half; this skill checks everything that lives
inside Claude Code (plugin, license, frameworks, voice, global MCP
wiring) which the Terminal cannot see.

This skill is strictly **read-only**. It inspects state and tells you
what to do. It never installs, edits, moves, or deletes anything. Every
fix it prints is a command you choose to run yourself.

## What it checks (each maps to a known support case)

1. The six Caddy frameworks are installed (Homebrew on macOS, Scoop on Windows).
2. The framework links in the Claude config dir exist (and on macOS are not
   blocked by a pre-existing file, the collision case).
3. The license token is set and is actually accepted by the server.
4. Your voice and brand files exist and the voice sample is substantial.
5. The global MCP servers (`base-mcp`, `carl-mcp`) are installed at their
   fixed paths and registered at Claude Code user scope (load in every
   session, any folder).
6. The CARL safety hook is registered so safety rules actually fire.
7. No leftover per-folder `.mcp.json` files are shadowing the global
   user-scope registration (the Option-2 migration footgun).

## Execution

Claude: run the block below as one script. Do NOT stop on the first
failure, a diagnostic must run every check and print a full report.
Then present the OK/FAIL/WARN lines to the user verbatim, followed by
the SUMMARY line. Do not paraphrase the fixes.

```bash
PASS=0; FAILN=0; WARNN=0
ok()   { echo "PASS  $*"; PASS=$((PASS+1)); }
fail() { echo "FAIL  $*"; FAILN=$((FAILN+1)); }
warn() { echo "WARN  $*"; WARNN=$((WARNN+1)); }

# --- OS-aware resolution preamble ------------------------------------------
# macOS branch is behavior-identical to prior versions (brew, $HOME/.claude,
# $HOME/.caddy, command -v python3). Windows branch resolves the Scoop
# install root, Scoop's absolute python.exe (never the MS Store `python3`
# alias), and %USERPROFILE%-based config dirs (Git Bash $HOME can differ
# from %USERPROFILE% under corporate AD).
case "$(uname -s)" in
  Darwin)
    OS=mac
    PY="$(command -v python3 || true)"
    CLAUDE_DIR="$HOME/.claude"
    CADDY_DIR="$HOME/.caddy"
    FW_FIX="brew tap meetcaddy/caddy && brew install caddy-frameworks"
    TOKEN_HINT="Add it to ~/.zshrc or ~/.bashrc to make it stick."
    fw_installed() { brew list "$1" >/dev/null 2>&1; }
    ;;
  MINGW*|MSYS*|CYGWIN*)
    OS=win
    SCOOP_ROOT="$(cygpath -u "${SCOOP:-$USERPROFILE\\scoop}" 2>/dev/null || printf '%s' "$HOME/scoop")"
    PY="$SCOOP_ROOT/apps/python/current/python.exe"
    [ -x "$PY" ] || PY="$(ls "$SCOOP_ROOT"/apps/python*/current/python.exe 2>/dev/null | head -n1)"
    [ -x "$PY" ] || PY=""
    UP="$(cygpath -u "$USERPROFILE" 2>/dev/null || printf '%s' "$HOME")"
    CLAUDE_DIR="$UP/.claude"
    CADDY_DIR="$UP/.caddy"
    FW_FIX="scoop bucket add caddy https://github.com/meetcaddy/scoop-caddy && scoop install caddy-frameworks"
    TOKEN_HINT="Set it persistently in PowerShell: setx CADDY_BEARER_TOKEN \"caddy_...\" (then reopen the terminal)."
    fw_installed() { [ -d "$SCOOP_ROOT/apps/$1/current" ]; }
    ;;
  *)
    OS=other
    PY="$(command -v python3 || true)"
    CLAUDE_DIR="$HOME/.claude"; CADDY_DIR="$HOME/.caddy"
    FW_FIX="(unsupported OS, macOS or Windows only)"
    TOKEN_HINT="Add it to your shell profile to make it stick."
    fw_installed() { return 1; }
    ;;
esac
# ---------------------------------------------------------------------------

echo "Caddy verify, read-only health check"
echo "(global install; not folder-specific)"
echo "----------------------------------------"

# 1. Frameworks installed (support case: slash commands do not appear)
MISSING_F=""
for f in caddy-base caddy-carl caddy-paul caddy-seed caddy-skillsmith caddy-aegis; do
  fw_installed "$f" || MISSING_F="$MISSING_F $f"
done
if [ -z "$MISSING_F" ]; then
  ok "all 6 Caddy frameworks installed"
else
  fail "missing frameworks:$MISSING_F"
  echo "      Fix: $FW_FIX"
fi

# 2. Framework links + collision (support case 7.3 / 7.7b)
# Only meaningful if the frameworks are installed: a caddy-link collision
# can only exist when caddy-link is the install mechanism. If the
# frameworks are absent, a directory at these paths is NOT a Caddy
# collision (it may be a legitimate non-Caddy install). Telling the user
# to move it would be destructive, so this check is gated on #1.
# macOS uses POSIX symlinks (collision-detectable). Windows caddy-link
# creates junctions (indistinguishable from real dirs in Git Bash, and
# the Windows helper does its own collision handling) so on Windows this
# is a presence check only.
if [ -n "$MISSING_F" ]; then
  warn "framework links: skipped (frameworks not installed; fix item 1 first)"
elif [ "$OS" = win ]; then
  MISSINGLINK=0
  for p in commands/base commands/paul commands/seed commands/skillsmith commands/aegis skills/base; do
    [ -e "$CLAUDE_DIR/$p" ] || MISSINGLINK=1
  done
  if [ "$MISSINGLINK" -eq 1 ]; then
    warn "some framework links are absent under %USERPROFILE%\\.claude\\. Fix: run caddy-link"
  else
    ok "framework links present under %USERPROFILE%\\.claude\\"
  fi
else
  COLLISION=0; MISSINGLINK=0
  for p in commands/base commands/paul commands/seed commands/skillsmith commands/aegis skills/base base-framework paul-framework skillsmith-specs aegis; do
    T="$CLAUDE_DIR/$p"
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
  echo "      Claude Code. $TOKEN_HINT"
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
VOICE="$CADDY_DIR/voice.md"
BRAND="$CADDY_DIR/brand.md"
if [ ! -f "$VOICE" ] || [ ! -f "$BRAND" ]; then
  fail "voice or brand profile missing (no voice.md/brand.md in your Caddy home dir)"
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

# 5. Global MCP servers installed at fixed paths + registered at user scope
#    (support case 7.6). Option-2 model: BASE installs at ~/.caddy/base,
#    CARL at ~/.carl, each registered ONCE at Claude Code USER scope so it
#    loads in every session from any directory. There is no per-folder
#    .mcp.json to inspect. A server is healthy only if BOTH its fixed
#    index.js exists on disk AND it is registered at user scope.
BASE_IDX="$HOME/.caddy/base/.base/base-mcp/index.js"
CARL_IDX="$HOME/.carl/carl-mcp/index.js"
CLAUDE_BIN="$(command -v claude || true)"

check_global_mcp() {
  # $1 = server name (base-mcp|carl-mcp), $2 = expected index.js path
  # Surfaces the ACTUAL resolved scope (user / project / local), not just
  # presence. A project-scope registration via a shadow .mcp.json was the
  # 2026-05-25 footgun where `claude mcp get` succeeded (because something
  # was registered) but the registration was the wrong scope; the per-server
  # PASS line falsely said "user scope". We now parse `claude mcp get`'s
  # "Scope:" line and surface it.
  name="$1"; idx="$2"; onfile=0; onreg=0; regscope=""
  [ -f "$idx" ] && onfile=1
  if [ -n "$CLAUDE_BIN" ]; then
    regscope="$(claude mcp get "$name" 2>/dev/null \
      | grep -E '^[[:space:]]*Scope:' | head -1 \
      | sed -E 's/^[[:space:]]*Scope:[[:space:]]*//' | tr -d '\r')"
    [ -n "$regscope" ] && onreg=1
  fi
  setup="/caddy:${name%-mcp}-setup"
  if [ "$onfile" -eq 1 ] && [ "$onreg" -eq 1 ]; then
    case "$regscope" in
      *[Uu]ser*)
        ok "$name installed and registered at user scope ($regscope)"
        ;;
      *[Pp]roject*)
        warn "$name installed but registered at PROJECT scope ($regscope); will only load from this folder tree, not from any folder"
        echo "      Fix: run $setup (re-registers at user scope via claude mcp add --scope user)"
        ;;
      *[Ll]ocal*)
        warn "$name installed but registered at LOCAL scope ($regscope); non-standard for Caddy"
        echo "      Fix: run $setup (re-registers at user scope)"
        ;;
      *)
        ok "$name installed and registered ($regscope)"
        ;;
    esac
  elif [ "$onfile" -eq 0 ] && [ "$onreg" -eq 0 ]; then
    fail "$name not installed and not registered with Claude Code"
    echo "      Fix: run $setup"
  elif [ "$onfile" -eq 0 ]; then
    fail "$name registered ($regscope) but its file is missing ($idx)"
    echo "      Fix: run $setup (re-copies the server to its fixed path)"
  else
    fail "$name present on disk but not registered with Claude Code"
    echo "      Fix: run $setup (re-registers via claude mcp add --scope user)"
  fi
}

if [ -z "$CLAUDE_BIN" ]; then
  warn "the 'claude' CLI is not on PATH; checking fixed install paths only (cannot confirm user-scope registration)"
  if [ -f "$BASE_IDX" ]; then ok "base-mcp present at $BASE_IDX"; else fail "base-mcp missing at $BASE_IDX"; echo "      Fix: run /caddy:base-setup"; fi
  if [ -f "$CARL_IDX" ]; then ok "carl-mcp present at $CARL_IDX"; else fail "carl-mcp missing at $CARL_IDX"; echo "      Fix: run /caddy:carl-setup"; fi
else
  check_global_mcp base-mcp "$BASE_IDX"
  check_global_mcp carl-mcp "$CARL_IDX"
fi

# 6. CARL safety hook registered (support case 7.6 / v0.5.0 safety rules)
SETTINGS="$CLAUDE_DIR/settings.json"
if [ -z "$PY" ]; then
  warn "python not found; skipping the safety-hook check"
elif [ ! -f "$SETTINGS" ]; then
  warn "no Claude Code settings.json yet; safety hook not registered"
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
    echo "      Fix: run /caddy:carl-setup (Step 6 registers the hook)."
  fi
fi

# 7. Shadow per-folder .mcp.json files (Option-2 migration footgun, learned 2026-05-19)
# Any per-folder .mcp.json that still references base-mcp or carl-mcp takes
# precedence over the user-scope registration when Claude Code is launched
# from its directory tree, and base-mcp/carl-mcp will fail to connect (-32000)
# even though the global install is perfect. The home-level shadow
# (~/.mcp.json) is the worst because it covers every session launched from
# any subdir of home. Scans a few common dev roots; read-only.
SHADOW_LIST="$( {
  [ -f "$HOME/.mcp.json" ] && echo "$HOME/.mcp.json"
  find "$HOME/Desktop" "$HOME/Documents" "$HOME/Downloads" "$HOME/development" "$HOME/Sites" \
       -maxdepth 4 -name .mcp.json -type f 2>/dev/null
} | sort -u | while read -r f; do
  [ -f "$f" ] && grep -lE 'base-mcp|carl-mcp' "$f" 2>/dev/null
done )"
if [ -z "$SHADOW_LIST" ]; then
  ok "no shadow per-folder .mcp.json files found (user-scope registration is not being shadowed)"
else
  fail "shadow per-folder .mcp.json files found (they will shadow the global user-scope registration):"
  echo "$SHADOW_LIST" | sed 's/^/        /'
  echo "      Fix: rename each to '<path>.preoption2.bak' (reversible). Restore later with:"
  echo "      mv <path>.preoption2.bak <path>"
fi

echo "----------------------------------------"
if [ "$FAILN" -eq 0 ] && [ "$WARNN" -eq 0 ]; then
  echo "SUMMARY: all clear ($PASS passed). Caddy is healthy."
  echo ""
  echo "Next step: run /caddy:capabilities to see everything your Caddy can do."
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

When the SUMMARY says all clear, run `/caddy:capabilities` to see
everything your Caddy can do.

## Notes

- **Read-only.** No file is created, edited, moved, or deleted. All Python
  is `json.load` only (never writes). Safe to run anytime, any number of
  times, including mid-session.
- The license check sends one authenticated request to the Caddy endpoint
  (`$CADDY_MCP_URL` or the production default) and interprets only the
  HTTP status: 401 means the token is bad/revoked, any non-401 means the
  token cleared authentication. It never prints the token.
- This is a **global** install check. BASE and CARL are installed once at
  fixed paths (`~/.caddy/base`, `~/.carl`) and registered at Claude Code
  user scope, so the result is the same from any directory. There is no
  workspace folder to run it in and no `WORKSPACE` variable to set.
- The user-scope registration check shells out to `claude mcp get`
  (read-only; prints nothing). If the `claude` CLI is not on PATH, the
  check degrades to a fixed-path-only check and emits a WARN.

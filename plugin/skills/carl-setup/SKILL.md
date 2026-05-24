---
description: "Wire CARL's carl-mcp server so it loads in EVERY Claude Code session, machine-wide, with no workspace folder to remember. Installs carl-mcp once at a fixed home-level CARL home (~/.carl), registers it at Claude Code user scope, seeds the Caddy-managed safety-rules domain there, and registers the CARL UserPromptSubmit hook so rules inject into every prompt from any directory. Use after installing caddy-frameworks. One-time per machine; idempotent (safe to re-run for repair). Triggers: 'set up carl', 'wire carl-mcp', 'carl-mcp failed', 'carl-mcp not running', 'carl-mcp missing', missing caddy-safety rules, multi-action guardrail not firing, CARL rules not injecting, or any carl-mcp tool failing with missing-tool errors."
---

# /caddy:carl-setup

Wire the **carl-mcp** server so CARL is available in every Claude Code session, no matter which folder Claude was started from.

CARL ships its global source files via the framework installer (`caddy-frameworks` lands the carl-core MCP source + workspace template + the CARL hook under the OS package prefix). carl-mcp itself is a small Node.js stdio MCP server. This skill installs it **once at a fixed location** and registers it at Claude Code's **user scope**, so Claude loads it in every session automatically. The customer never has to launch from a special folder.

carl-mcp resolves its state location from its own install path (`path.resolve(__dirname, '../..')`), so installing it at `~/.carl/carl-mcp/` makes the home directory CARL's single, always-on workspace, with state at `~/.carl/{carl.json, sessions/, decisions/, ...}`.

Placing CARL state at `~/.carl` (home root) is deliberate: the upstream CARL UserPromptSubmit hook finds rules by walking **up** from the current directory looking for a `.carl/carl.json`. With the global scope at `~/.carl/carl.json`, that unmodified walk-up discovers it from **any** working directory under the home folder, with zero upstream patch, so it survives package updates cleanly. (BASE lives at `~/.caddy/base`; CARL at `~/.carl`. The slight path asymmetry is the intentional cost of keeping the upstream hook unpatched.)

## Prerequisite

You must have `caddy-carl` installed via the OS package manager (it ships the carl-mcp source files + the hook), plus Python 3 (the seeder and the CARL hook are Python).

**macOS (Homebrew):**

```bash
brew tap meetcaddy/caddy
brew install caddy-frameworks    # bundles caddy-carl alongside BASE + PAUL + SEED + Skillsmith + Aegis
caddy-link                       # symlinks BASE/PAUL/SEED/Skillsmith/Aegis into ~/.claude/
```

macOS ships `python3` system-wide, so no extra Python step is needed. After install, CARL's source is readable at `$(brew --prefix caddy-carl)/share/caddy-carl/mcp/`.

**Windows (Scoop):**

```powershell
scoop bucket add caddy https://github.com/meetcaddy/scoop-caddy
scoop install caddy-frameworks   # bundles caddy-carl alongside BASE + PAUL + SEED + Skillsmith + Aegis
scoop install python             # required: the CARL seeder + hook are Python 3
caddy-link                       # junctions BASE/PAUL/SEED/Skillsmith/Aegis into %USERPROFILE%\.claude\
```

Windows has no system `python3`, and the bare name `python3` is hijacked by a Microsoft Store alias, so this skill resolves Scoop's `python.exe` by absolute path rather than trusting PATH. After the Scoop install, CARL's source is readable at `<scoop>\apps\caddy-carl\current\share\caddy-carl\mcp\`.

CARL is MCP-only (ships no slash commands or suite skill), so `caddy-link` doesn't create any `commands/carl/` symlinks on either OS.

## What this skill does

This installs **one global CARL workspace per machine** at the home directory. That is intentional: a Caddy customer has one Caddy, always on, not a separate one per folder.

1. **Locate the CARL source** at the package prefix's `share/caddy-carl/` (macOS: `$(brew --prefix caddy-carl)/share/caddy-carl/`; Windows: `<scoop>\apps\caddy-carl\current\share\caddy-carl\`). Resolved at runtime so a package upgrade automatically picks up new versions.
2. **Copy the MCP server** from `<carl-pkg>/mcp/` into the fixed path `~/.carl/carl-mcp/`. carl-mcp's `index.js` uses `path.resolve(__dirname, '../..')` for workspace resolution, so installing it at `~/.carl/carl-mcp/index.js` makes the home directory CARL's single workspace and `~/.carl/` its state directory.
3. **Seed the workspace template** by copying `<carl-pkg>/carl-template/carl.json` into `~/.carl/carl.json` and creating an empty `~/.carl/sessions/` directory. Only seeds if `~/.carl/carl.json` doesn't already exist (idempotent; preserves any prior CARL state).
4. **Run `npm install`** in `~/.carl/carl-mcp/` to fetch `@modelcontextprotocol/sdk` (only if missing).
5. **Register carl-mcp at Claude Code user scope** via `claude mcp add --scope user`, with an absolute path to the fixed `index.js`. User scope means Claude loads it in every session, every directory, with no per-folder `.mcp.json`. The registration is made idempotent by removing any existing user-scope `carl-mcp` entry first, then adding fresh (so a re-run repairs a stale path cleanly).
6. **Seed the Caddy-managed `caddy-safety` domain** into `~/.carl/carl.json` from `carl-rules/caddy-safety.json` shipped with this skill. Uses `lib/seed-carl-domain.py` so the seeder remains idempotent: customer-edited rules are preserved (DIVERGED), and unedited rules pick up upstream Caddy revisions automatically. Sidecar state lives at `~/.carl/caddy-carl-state.json` to track what's Caddy-shipped vs customer-modified.
7. **Register the CARL UserPromptSubmit hook** in the Claude Code `settings.json` (macOS `~/.claude/settings.json`; Windows `%USERPROFILE%\.claude\settings.json`) pointing at the upstream `<carl-pkg>/hooks/carl-hook.py`. The registered command is `python3 <hook>` on macOS and `"<abs python.exe>" "<abs hook>"` on Windows (absolute paths dodge the Microsoft Store `python3` alias). This hook is already global (it runs for every prompt in every session); placing the CARL scope at `~/.carl` is what lets its existing walk-up actually find the seeded rules from any directory. Idempotent (skips if our entry is already present). One-time backup of the pre-existing `settings.json` is written alongside it as `settings.json.pre-caddy-carl.bak`.

## Execution

This is machine-wide. There is no workspace folder to pick and no `cd` to perform first: the install target is the fixed home-level CARL home, resolved in the preamble below.

This block runs in bash on both OSes (on Windows that is the Git Bash that Claude Code uses). Only the **home directory**, the **CARL source location**, the **Python interpreter**, and the **path-persist form** differ by OS; everything after the resolution preamble is shared.

```bash
# --- OS-aware resolution preamble -------------------------------------------
# Resolves per-OS:
#   CADDY_USER_HOME : the home directory that becomes CARL's single workspace
#                     (macOS $HOME; Windows %USERPROFILE% — resolved from
#                     USERPROFILE, not $HOME, because corporate AD can redirect
#                     Git Bash $HOME to a share Claude Code never reads).
#   CARL_PKG        : install prefix; CARL source lives at
#                     $CARL_PKG/share/caddy-carl/
#   PYTHON_BIN      : the Python 3 used for the seeder and the settings.json
#                     hook merge (executed by THIS skill)
#   CLAUDE_DIR      : where Claude Code reads user config (settings.json)
#   to_persist()    : path form WRITTEN INTO config / passed to node + python.
#                     Identity on macOS; Windows mixed-slash (cygpath -m:
#                     C:/Users/...) so node/python accept it with no JSON
#                     backslash escaping.
#   HOOK_CMD_FOR()  : the settings.json hook command (python3 <hook> on macOS;
#                     quoted absolute python.exe + hook on Windows).
case "$(uname -s)" in
  Darwin)
    CADDY_USER_HOME="$HOME"                             # $HOME is reliable on macOS
    CARL_PKG="$(brew --prefix caddy-carl 2>/dev/null)"
    PYTHON_BIN="$(command -v python3)"
    CLAUDE_DIR="$HOME/.claude"
    to_persist() { printf '%s' "$1"; }                 # identity on macOS
    HOOK_CMD_FOR() { printf 'python3 %s' "$1"; }        # byte-identical to prior versions
    PKG_HINT="brew tap meetcaddy/caddy && brew install caddy-frameworks && caddy-link"
    PY_HINT="python3 ships with macOS"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    CADDY_USER_HOME="$(cygpath -u "$USERPROFILE" 2>/dev/null || printf '%s' "$HOME")"
    # Scoop user install root: honor $SCOOP, else %USERPROFILE%\scoop.
    SCOOP_WIN="${SCOOP:-$USERPROFILE\\scoop}"
    SCOOP_ROOT="$(cygpath -u "$SCOOP_WIN" 2>/dev/null || printf '%s' "$HOME/scoop")"
    CARL_PKG="$SCOOP_ROOT/apps/caddy-carl/current"
    # Scoop python.exe (absolute; never the bare 'python3' MS Store alias).
    PYTHON_BIN="$SCOOP_ROOT/apps/python/current/python.exe"
    if [[ ! -x "$PYTHON_BIN" ]]; then
      # Fallback: versioned scoop python app dir (e.g. python311).
      PYTHON_BIN="$(ls "$SCOOP_ROOT"/apps/python*/current/python.exe 2>/dev/null | head -n1)"
    fi
    # Claude Code on Windows reads %USERPROFILE%\.claude\settings.json.
    CLAUDE_DIR="$CADDY_USER_HOME/.claude"
    to_persist() { cygpath -m "$1"; }                  # /c/Users -> C:/Users
    HOOK_CMD_FOR() { printf '"%s" "%s"' "$(cygpath -m "$PYTHON_BIN")" "$(cygpath -m "$1")"; }
    PKG_HINT="scoop bucket add caddy https://github.com/meetcaddy/scoop-caddy && scoop install caddy-frameworks && caddy-link"
    PY_HINT="scoop install python"
    ;;
  *)
    echo "ERROR: unsupported OS '$(uname -s)' for /caddy:carl-setup (macOS and Windows only)."
    exit 1
    ;;
esac

CARL_WORKSPACE_DIR="$CADDY_USER_HOME/.carl"
CARL_MCP_DIR="$CARL_WORKSPACE_DIR/carl-mcp"

# Sanity: caddy-carl package must be installed
if [[ -z "$CARL_PKG" ]] || [[ ! -d "$CARL_PKG/share/caddy-carl/mcp" ]]; then
  echo "ERROR: caddy-carl not installed (expected source at $CARL_PKG/share/caddy-carl/mcp)."
  echo "  Run: $PKG_HINT"
  exit 1
fi

# Sanity: a usable Python 3 must be resolvable
if [[ -z "$PYTHON_BIN" ]] || [[ ! -x "$PYTHON_BIN" ]]; then
  echo "ERROR: Python 3 not found (the CARL seeder + hook require it)."
  echo "  Run: $PY_HINT"
  exit 1
fi
# ---------------------------------------------------------------------------

CARL_GLOBAL_SRC="$CARL_PKG/share/caddy-carl/mcp"
CARL_TEMPLATE_DIR="$CARL_PKG/share/caddy-carl/carl-template"

# Step 1: copy carl-mcp source into the fixed CARL home
if [[ -f "$CARL_MCP_DIR/index.js" ]]; then
  echo "SKIP $CARL_MCP_DIR (already present)"
else
  mkdir -p "$CARL_WORKSPACE_DIR"
  cp -R "$CARL_GLOBAL_SRC" "$CARL_MCP_DIR"
  echo "OK  carl-mcp source copied to $CARL_MCP_DIR"
fi

# Step 2: seed workspace template (carl.json + sessions/) — idempotent
if [[ -f "$CARL_WORKSPACE_DIR/carl.json" ]]; then
  echo "SKIP $CARL_WORKSPACE_DIR/carl.json (already exists; CARL state preserved)"
else
  cp "$CARL_TEMPLATE_DIR/carl.json" "$CARL_WORKSPACE_DIR/carl.json"
  mkdir -p "$CARL_WORKSPACE_DIR/sessions"
  echo "OK  carl.json + sessions/ seeded from template"
fi

# Step 3: npm install dependencies (only if missing)
if [[ -d "$CARL_MCP_DIR/node_modules/@modelcontextprotocol/sdk" ]]; then
  echo "SKIP node_modules (already installed)"
else
  if (cd "$CARL_MCP_DIR" && npm install >/dev/null 2>&1); then
    echo "OK  npm install succeeded"
  else
    echo "FAIL npm install. Run manually: cd $CARL_MCP_DIR && npm install"
    exit 1
  fi
fi

# Step 4: register carl-mcp at Claude Code USER scope (loads in every session)
CARL_MCP_INDEX="$CARL_MCP_DIR/index.js"
if [[ ! -f "$CARL_MCP_INDEX" ]]; then
  echo "ERROR: $CARL_MCP_INDEX missing after copy"
  exit 1
fi
CARL_MCP_INDEX_PERSIST="$(to_persist "$CARL_MCP_INDEX")"

# Idempotent: drop any prior user-scope entry, then add fresh. `remove`
# tolerates "not found"; the explicit re-add guarantees a correct path on
# every run (this is how a stale-path repair happens now).
claude mcp remove carl-mcp --scope user >/dev/null 2>&1 || true
if claude mcp add --scope user carl-mcp -- node "$CARL_MCP_INDEX_PERSIST" >/dev/null 2>&1; then
  echo "OK  carl-mcp registered at Claude Code user scope -> $CARL_MCP_INDEX_PERSIST"
else
  echo "FAIL 'claude mcp add --scope user carl-mcp' did not succeed."
  echo "     Run manually: claude mcp add --scope user carl-mcp -- node \"$CARL_MCP_INDEX_PERSIST\""
  exit 1
fi

# Step 5: seed the Caddy-managed caddy-safety domain (multi-action guardrail rule)
#
# This skill ships two files alongside SKILL.md inside the plugin install:
#   carl-rules/caddy-safety.json   (rule source-of-truth; schema_version 1)
#   lib/seed-carl-domain.py        (idempotent seeder)
#
# Claude: before running this block, resolve SKILL_DIR to the absolute path
# of THIS skill's directory (the directory containing this SKILL.md plus
# carl-rules/ and lib/ siblings). Typical plugin install location is
# ~/.claude/plugins/<marketplace>/plugins/caddy/plugin/skills/carl-setup/;
# the exact path depends on the customer's Claude Code plugin install.
# If you cannot locate the skill directory, skip steps 5 and 6 and emit a
# WARN line. Steps 1-4 above will still have completed successfully.
#
# Do NOT improvise a separate ad-hoc pre-flight that `ls`-es paths. This
# Execution block is self-verifying and idempotent. If you must probe a path
# while resolving SKILL_DIR, use `[[ -e PATH ]]` or `test`, NEVER `ls`.

# Normalize up front. $SKILL_DIR is resolved by Claude and on Windows may
# arrive as a backslash path; the raw form can make the -f guard below
# false-negative (and silently skip the safety-rule seed). to_persist is
# identity on macOS, so the guard is byte-equivalent there.
CADDY_RULES_FILE="$(to_persist "$SKILL_DIR/carl-rules/caddy-safety.json")"
CADDY_SEEDER="$(to_persist "$SKILL_DIR/lib/seed-carl-domain.py")"
CADDY_CARL_JSON="$(to_persist "$CARL_WORKSPACE_DIR/carl.json")"
CADDY_STATE_FILE="$(to_persist "$CARL_WORKSPACE_DIR/caddy-carl-state.json")"

if [[ -f "$CADDY_SEEDER" ]] && [[ -f "$CADDY_RULES_FILE" ]]; then
  # Already persisted above, so python.exe (Windows) gets paths it can open.
  if "$PYTHON_BIN" "$CADDY_SEEDER" \
      --rules-file "$CADDY_RULES_FILE" \
      --carl-json "$CADDY_CARL_JSON" \
      --state-file "$CADDY_STATE_FILE"; then
    echo "OK  caddy-safety domain seeded into $CADDY_CARL_JSON"
  else
    echo "FAIL caddy-safety seed (seeder exited non-zero). Inspect $CADDY_CARL_JSON manually."
  fi
else
  echo "WARN skill bundle missing carl-rules/caddy-safety.json or lib/seed-carl-domain.py; skipping rule seed"
  echo "     (steps 1-4 succeeded; carl-mcp still wired, but caddy-safety domain not seeded)"
fi

# Step 6: register CARL UserPromptSubmit hook in the Claude Code settings.json
#
# Without this, seeded rules sit in carl.json but never inject into prompts.
# The hook is global (matcher '*', runs every prompt in every session); the
# fixed ~/.carl scope from steps 1-5 is what its existing walk-up resolves
# from any directory under the home folder.
# Idempotent: detects existing carl-hook.py registration and skips if present.
# One-time backup of pre-existing settings.json is preserved across re-runs.

CARL_HOOK_PATH="$CARL_PKG/share/caddy-carl/hooks/carl-hook.py"
CLAUDE_SETTINGS="$CLAUDE_DIR/settings.json"
CLAUDE_SETTINGS_BAK="$CLAUDE_DIR/settings.json.pre-caddy-carl.bak"

if [[ -f "$CARL_HOOK_PATH" ]]; then
  # Backup once, preserving the true pre-Caddy snapshot across re-runs.
  if [[ -f "$CLAUDE_SETTINGS" ]] && [[ ! -f "$CLAUDE_SETTINGS_BAK" ]]; then
    cp "$CLAUDE_SETTINGS" "$CLAUDE_SETTINGS_BAK"
    echo "OK  $CLAUDE_SETTINGS backed up to $CLAUDE_SETTINGS_BAK"
  fi

  # Command the Claude Code hook runner will execute every prompt.
  #   macOS:   python3 <hook.py>            (byte-identical to prior versions)
  #   Windows: "<scoop python.exe>" "<hook.py>"  (absolute; dodges the
  #            Microsoft Store 'python3' alias and PATH ambiguity)
  HOOK_CMD="$(HOOK_CMD_FOR "$CARL_HOOK_PATH")"
  HOOK_REG_RESULT="$(CADDY_SETTINGS="$(to_persist "$CLAUDE_SETTINGS")" CADDY_HOOK_CMD="$HOOK_CMD" "$PYTHON_BIN" -c "
import json, os, pathlib, sys
settings_path = pathlib.Path(os.environ['CADDY_SETTINGS'])
hook_cmd = os.environ['CADDY_HOOK_CMD']
settings_path.parent.mkdir(parents=True, exist_ok=True)
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        print('invalid-json')
        sys.exit(1)
else:
    settings = {}
hooks = settings.setdefault('hooks', {})
ups = hooks.setdefault('UserPromptSubmit', [])
already = False
for entry in ups:
    for h in entry.get('hooks', []):
        cmd = h.get('command', '')
        if 'carl-hook.py' in cmd:
            already = True
            break
    if already:
        break
if already:
    print('kept')
else:
    ups.append({
        'matcher': '*',
        'hooks': [{'type': 'command', 'command': hook_cmd}],
        'description': 'Caddy: CARL UserPromptSubmit hook (injects active rules from ~/.carl/carl.json into every prompt, from any directory). Bypass: remove this entry.',
        'id': 'user-prompt-submit:caddy-carl-hook'
    })
    tmp = settings_path.with_suffix(settings_path.suffix + '.tmp')
    tmp.write_text(json.dumps(settings, indent=2))
    os.replace(tmp, settings_path)
    print('merged')
")"
  case "$HOOK_REG_RESULT" in
    merged)       echo "OK  carl-hook.py registered in $CLAUDE_SETTINGS" ;;
    kept)         echo "SKIP carl-hook.py already registered in $CLAUDE_SETTINGS" ;;
    invalid-json) echo "FAIL $CLAUDE_SETTINGS is not valid JSON; hook registration skipped. Restore from $CLAUDE_SETTINGS_BAK if needed." ;;
    *)            echo "FAIL hook registration: unexpected result '$HOOK_REG_RESULT'" ;;
  esac
else
  echo "WARN $CARL_HOOK_PATH not found; seeded CARL rules will NOT auto-inject"
  echo "     Reinstall caddy-frameworks: $PKG_HINT"
fi

echo ""
echo "Done. carl-mcp now loads in every Claude Code session, from any folder."
echo "      Seeded caddy-safety rules will activate on the next prompt submission."
echo "      Restart Claude Code (or run /mcp) to load it now."
echo ""
echo "Starter tools (8 of CARL's 30; v2 surface — see plugin README for full set):"
echo "  carl_v2_log_decision        carl_v2_search_decisions"
echo "  carl_v2_get_decisions       carl_v2_list_domains"
echo "  carl_v2_get_config          carl_v2_stage_proposal"
echo "  carl_v2_approve_proposal    carl_v2_get_staged"
```

## After running

Restart Claude Code (or run `/mcp`). `/mcp` shows `carl-mcp ✓ connected` in **every** session regardless of which directory Claude was started in, and the 30 `mcp__carl-mcp__*` tools become available alongside any existing `mcp__base-mcp__*` / `mcp__caddy*` tools. Seeded `caddy-safety` rules inject on the next prompt from any folder. There is no workspace folder to remember.

## Customer-facing tool surface

CARL ships **30 MCP tools**. We recommend starting with these **8 v2 tools** (the operator-rhythm core):

1. **carl_v2_log_decision** — log a decision in CARL state
2. **carl_v2_search_decisions** — find past decisions by domain or text
3. **carl_v2_get_decisions** — list decisions in a domain
4. **carl_v2_list_domains** — see all CARL domains
5. **carl_v2_get_config** — read current CARL config + active rules
6. **carl_v2_stage_proposal** — stage a new rule for approval
7. **carl_v2_approve_proposal** — promote staged proposal to active rule
8. **carl_v2_get_staged** — see what's pending approval

The remaining 22 tools (v1 legacy + v2 advanced: add_rule, remove_rule, replace_rules, archive_decision, update_config, etc.) are available via the same `mcp__carl-mcp__*` surface. v1 tools are kept for back-compat with existing CARL workspaces from prior installs.

## Troubleshooting

- **`carl-mcp ✗ failed` after restart:** check `~/.carl/carl-mcp/index.js` and its `node_modules/@modelcontextprotocol/sdk/` exist. If either is missing, re-run this skill.
- **`carl-mcp` not listed by `/mcp` at all:** confirm the user-scope registration with `claude mcp get carl-mcp`. Re-run this skill to repair.
- **Stale path after a move:** re-run this skill; Step 4 removes and re-adds, fixing the path.
- **CARL rules not injecting into prompts:** this skill auto-registers `carl-hook.py` in the Claude Code `settings.json` (Step 6; `~/.claude/settings.json` on macOS, `%USERPROFILE%\.claude\settings.json` on Windows). If it didn't fire, open that file and confirm a `UserPromptSubmit` entry whose `command` ends in `carl-hook.py` is present and that the referenced path resolves to a real file. The seeded scope must also exist at `~/.carl/carl.json`. To force a re-register, remove the entry and re-run this skill.
- **Rules not found from a deeply nested folder:** the upstream hook walks up at most ~10 directory levels looking for `.carl/carl.json`. A working directory more than ten levels below the home folder will not reach `~/.carl` (not realistic for a normal customer). Run from anywhere closer to home.

## Notes

- **Idempotent**: safe to re-run. Step 4's remove-then-add repairs a stale path cleanly. Workspace template seeding (Step 2) only runs on first init (preserves prior CARL state). The caddy-safety domain seed (Step 5) preserves customer-edited rules and only updates unedited Caddy-shipped rules when the upstream version bumps. The hook registration (Step 6) skips if already registered.
- **One global CARL workspace** at `~/.carl`, by design. Not per project folder. (BASE is at `~/.caddy/base`; CARL at `~/.carl` so the unpatched upstream hook's walk-up resolves it from any directory under home.)
- The skill writes to three locations and adds one **user-scope** MCP entry via the `claude mcp` CLI (never by hand-editing `~/.claude.json`, which holds session/cache state):
  - `~/.carl/` (the single global CARL state, including the Caddy sidecar at `~/.carl/caddy-carl-state.json`)
  - `~/.claude/settings.json` (single entry: UserPromptSubmit hook for carl-hook.py — required for seeded rules to inject into prompts). A one-time backup is preserved at `~/.claude/settings.json.pre-caddy-carl.bak` before the first merge.
  - the user-scope MCP registration (via `claude mcp add --scope user`)
- No npm global pollution. carl-mcp dependencies (`@modelcontextprotocol/sdk`) are installed locally to `~/.carl/carl-mcp/`.

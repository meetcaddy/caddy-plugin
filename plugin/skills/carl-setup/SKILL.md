---
description: "Wire CARL's carl-mcp server into the current Claude Code workspace, seed the Caddy-managed safety rules domain, and register the CARL UserPromptSubmit hook so rules inject into every prompt. Use after installing caddy-frameworks via Homebrew, before any session where you want CARL rule routing, decision logging tools, or safety-rule enforcement. One-time per workspace; idempotent (safe to re-run for repair). Triggers: 'set up carl', 'wire carl-mcp', 'carl-mcp failed', 'carl-mcp not running', '.mcp.json missing carl-mcp', missing caddy-safety rules, multi-action guardrail not firing, or any carl-mcp tool failing with missing-tool errors."
---

# /caddy:carl-setup

Wire the **carl-mcp** server into the current workspace.

CARL ships its global source files via the Homebrew tap (`brew install caddy-frameworks` lands the carl-core MCP source + workspace template under `/opt/homebrew/opt/caddy-carl/share/caddy-carl/`). But carl-mcp itself runs as a per-workspace stdio MCP server: a small Node.js process that Claude Code launches alongside the workspace. The server reads/writes `<workspace>/.carl/{carl.json, sessions/, decisions/, ...}`, so it has to live in **this** workspace, not globally.

This skill replicates Stage 5a of the caddy-live customer install (the proven workspace-MCP wiring logic) so that opening a new workspace requires one command, not a recovery procedure.

## Prerequisite

You must have `caddy-carl` installed via the OS package manager (it ships the carl-mcp source files), plus Python 3 (the seeder and the CARL hook are Python).

**macOS (Homebrew):**

```bash
brew tap meetcaddy/caddy
brew install caddy-frameworks    # bundles caddy-carl alongside BASE + PAUL + SEED + Skillsmith + Aegis
caddy-link                       # symlinks BASE/PAUL/SEED/Skillsmith/Aegis into ~/.claude/
```

macOS ships `python3` system-wide, so no extra Python step is needed. After `caddy-link`, CARL's source is readable at `$(brew --prefix caddy-carl)/share/caddy-carl/mcp/`.

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

For the workspace where Claude Code was launched (the directory containing the project files):

1. **Locate the CARL source** at the package prefix's `share/caddy-carl/` (macOS: `$(brew --prefix caddy-carl)/share/caddy-carl/`; Windows: `<scoop>\apps\caddy-carl\current\share\caddy-carl\`). Resolved at runtime so a package upgrade automatically picks up new versions.
2. **Copy the MCP server** from `<carl-pkg>/mcp/` into `<workspace>/.carl/carl-mcp/`. carl-mcp's `index.js` uses `path.resolve(__dirname, '../..')` for workspace resolution, so it must live exactly at `<workspace>/.carl/carl-mcp/index.js`.
3. **Seed the workspace template** by copying `<carl-pkg>/carl-template/carl.json` into `<workspace>/.carl/carl.json` (the rules + domains + config file) and creating an empty `<workspace>/.carl/sessions/` directory. Only seeds if `<workspace>/.carl/carl.json` doesn't already exist (idempotent; preserves any prior CARL state).
4. **Run `npm install`** in the new `<workspace>/.carl/carl-mcp/` to fetch `@modelcontextprotocol/sdk`.
5. **Register the server** in `<workspace>/.mcp.json` with an **absolute path** to `<workspace>/.carl/carl-mcp/index.js`. Absolute paths are more robust than relative because Claude Code's CWD isn't guaranteed to match the workspace root (subdir launches, symlinked workspaces).
6. **Seed the Caddy-managed `caddy-safety` domain** into `<workspace>/.carl/carl.json` from `carl-rules/caddy-safety.json` shipped with this skill. Uses `lib/seed-carl-domain.py` so the seeder remains idempotent: customer-edited rules are preserved (DIVERGED), and unedited rules pick up upstream Caddy revisions automatically. Sidecar state lives at `<workspace>/.carl/caddy-carl-state.json` to track what's Caddy-shipped vs customer-modified.
7. **Register the CARL UserPromptSubmit hook** in the Claude Code `settings.json` (macOS `~/.claude/settings.json`; Windows `%USERPROFILE%\.claude\settings.json`) pointing at `<carl-pkg>/hooks/carl-hook.py`. The registered command is `python3 <hook>` on macOS and `"<abs python.exe>" "<abs hook>"` on Windows (absolute paths dodge the Microsoft Store `python3` alias). This is what makes seeded rules actually inject into every Claude Code prompt. Idempotent (skips if our entry is already present). One-time backup of the pre-existing `settings.json` is written alongside it as `settings.json.pre-caddy-carl.bak` (preserves original snapshot across re-runs).

The `.mcp.json` mutation handles three sub-cases idempotently:

- **(a) merge:** no `carl-mcp` entry exists → add one alongside existing servers (preserves `base-mcp`, `caddy.draft`, etc.).
- **(b) repair:** an entry exists but `args[0]` points at a non-existent file → rewrite to the correct absolute path.
- **(c) keep:** an entry exists and works → leave alone. Safe to re-run.

## Execution

Determine the workspace root first. By default it's the current working directory; if the user is in a subdir, they should `cd` to the project root before running the skill (or pass the workspace path explicitly).

This block runs in bash on both OSes (on Windows that is the Git Bash that Claude Code uses). Only the **CARL source location** and the **Python interpreter** differ by OS; everything after the resolution preamble is shared.

```bash
WORKSPACE="${WORKSPACE:-$(pwd)}"
CARL_WORKSPACE_DIR="$WORKSPACE/.carl"
CARL_MCP_DIR="$CARL_WORKSPACE_DIR/carl-mcp"
WORKSPACE_MCP_JSON="$WORKSPACE/.mcp.json"

# --- OS-aware resolution preamble -------------------------------------------
# Resolves three things per-OS:
#   CARL_PKG    : install prefix; CARL source lives at $CARL_PKG/share/caddy-carl/
#   PYTHON_BIN  : the Python 3 used for the .mcp.json merge, the seeder, and
#                 the settings.json hook merge (executed by THIS skill)
#   to_persist(): emits the form of a path that gets WRITTEN INTO a config
#                 file (.mcp.json args, settings.json hook command) and later
#                 executed by node / the Claude Code hook runner. On macOS the
#                 bash path is already native. On Windows the bash path is an
#                 MSYS path (/c/Users/...) that node and the hook runner do
#                 NOT understand, so it must be converted to a Windows path.
#                 Forward-slash mixed form (cygpath -m: C:/Users/...) is used
#                 so no JSON backslash-escaping is needed and node accepts it.
case "$(uname -s)" in
  Darwin)
    CARL_PKG="$(brew --prefix caddy-carl 2>/dev/null)"
    PYTHON_BIN="$(command -v python3)"
    CLAUDE_DIR="$HOME/.claude"                          # $HOME is reliable on macOS
    to_persist() { printf '%s' "$1"; }                 # identity on macOS
    HOOK_CMD_FOR() { printf 'python3 %s' "$1"; }        # byte-identical to prior versions
    PKG_HINT="brew tap meetcaddy/caddy && brew install caddy-frameworks"
    PY_HINT="python3 ships with macOS"
    ;;
  MINGW*|MSYS*|CYGWIN*)
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
    # Claude Code on Windows reads %USERPROFILE%\.claude\settings.json. Resolve
    # from $USERPROFILE, NOT $HOME: under corporate AD, Git Bash $HOME can be a
    # redirected HOMEDRIVE/HOMEPATH (network share) that Claude Code never reads.
    CLAUDE_DIR="$(cygpath -u "$USERPROFILE" 2>/dev/null || printf '%s' "$HOME")/.claude"
    to_persist() { cygpath -m "$1"; }                  # /c/Users -> C:/Users
    HOOK_CMD_FOR() { printf '"%s" "%s"' "$(cygpath -m "$PYTHON_BIN")" "$(cygpath -m "$1")"; }
    PKG_HINT="scoop bucket add caddy https://github.com/meetcaddy/scoop-caddy && scoop install caddy-frameworks"
    PY_HINT="scoop install python"
    ;;
  *)
    echo "ERROR: unsupported OS '$(uname -s)' for /caddy:carl-setup (macOS and Windows only)."
    exit 1
    ;;
esac

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

# Step 1: copy carl-mcp source into workspace
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

# Step 4: register in .mcp.json (merge / repair / keep)
# PYTHON_BIN is already resolved in the OS-aware preamble.
CARL_MCP_INDEX="$CARL_MCP_DIR/index.js"

if [[ ! -f "$CARL_MCP_INDEX" ]]; then
  echo "ERROR: $CARL_MCP_INDEX missing after copy"
  exit 1
fi

# Paths handed to python and written into config are the persisted form:
# identity on macOS, Windows mixed-slash (C:/...) on Windows so node and
# python.exe can actually use them. Passed via env (not interpolated into
# the script body) so they survive spaces and need no shell quoting.
CARL_MCP_INDEX_PERSIST="$(to_persist "$CARL_MCP_INDEX")"
WORKSPACE_MCP_JSON_PERSIST="$(to_persist "$WORKSPACE_MCP_JSON")"

if [[ -f "$WORKSPACE_MCP_JSON" ]]; then
  MERGE_RESULT="$(CADDY_MCP_JSON="$WORKSPACE_MCP_JSON_PERSIST" CADDY_IDX="$CARL_MCP_INDEX_PERSIST" "$PYTHON_BIN" -c "
import json, os
path = os.environ['CADDY_MCP_JSON']
correct_index = os.environ['CADDY_IDX']
with open(path) as f:
    data = json.load(f)
servers = data.setdefault('mcpServers', {})
existing = servers.get('carl-mcp')
action = 'unknown'
if existing is None:
    servers['carl-mcp'] = {'type': 'stdio', 'command': 'node', 'args': [correct_index]}
    action = 'merged'
else:
    args = existing.get('args') or []
    current_path = args[0] if args else None
    if current_path and os.path.isfile(current_path):
        action = 'kept'
    else:
        servers['carl-mcp'] = {'type': 'stdio', 'command': 'node', 'args': [correct_index]}
        action = 'repaired'
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
print(action)
")"
  case "$MERGE_RESULT" in
    merged)   echo "OK  carl-mcp merged into $WORKSPACE_MCP_JSON" ;;
    repaired) echo "OK  carl-mcp repaired in $WORKSPACE_MCP_JSON (path now $CARL_MCP_INDEX_PERSIST)" ;;
    kept)     echo "SKIP $WORKSPACE_MCP_JSON already has working carl-mcp entry" ;;
    *)        echo "FAIL merge unexpected result: $MERGE_RESULT"; exit 1 ;;
  esac
else
  CADDY_MCP_JSON="$WORKSPACE_MCP_JSON_PERSIST" CADDY_IDX="$CARL_MCP_INDEX_PERSIST" "$PYTHON_BIN" -c "
import json, os
with open(os.environ['CADDY_MCP_JSON'], 'w') as f:
    json.dump({'mcpServers': {'carl-mcp': {'type': 'stdio', 'command': 'node',
              'args': [os.environ['CADDY_IDX']]}}}, f, indent=2)
"
  echo "OK  $WORKSPACE_MCP_JSON created with carl-mcp registration"
fi

# Step 6: seed the Caddy-managed caddy-safety domain (multi-action guardrail rule)
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
# If you cannot locate the skill directory, skip steps 6 and 7 and emit a
# WARN line. Steps 1-5 above will still have completed successfully.
#
# Do NOT improvise a separate ad-hoc pre-flight that `ls`-es paths. This
# Execution block is self-verifying and idempotent: it already handles a
# fresh init (no <workspace>/.carl/ yet) and a pre-existing .mcp.json
# gracefully via guarded `[[ -e ]]`/`[[ -f ]]` tests. Just run the block.
# If you must probe a path while resolving SKILL_DIR, use `[[ -e PATH ]]`
# or `test`, NEVER `ls` — and never probe <workspace>/.carl, which
# legitimately does not exist before this skill runs. A non-zero `ls`
# exit there is benign but surfaces a confusing "Error: Exit code 2" to
# the customer mid-setup even though everything is fine.

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
  echo "     (steps 1-5 succeeded; carl-mcp still wired, but caddy-safety domain not seeded)"
fi

# Step 7: register CARL UserPromptSubmit hook in the Claude Code settings.json
#
# Without this, seeded rules sit in carl.json but never inject into prompts.
# Idempotent: detects existing carl-hook.py registration and skips if present.
# One-time backup of pre-existing settings.json is preserved across re-runs.
# CLAUDE_DIR is resolved per-OS in the preamble ($HOME/.claude on macOS,
# %USERPROFILE%\.claude on Windows) so the hook lands where Claude Code reads.

CARL_HOOK_PATH="$CARL_PKG/share/caddy-carl/hooks/carl-hook.py"
CLAUDE_SETTINGS="$CLAUDE_DIR/settings.json"
CLAUDE_SETTINGS_BAK="$CLAUDE_DIR/settings.json.pre-caddy-carl.bak"

if [[ -f "$CARL_HOOK_PATH" ]]; then
  # Backup once, preserving the true pre-Caddy snapshot across re-runs.
  if [[ -f "$CLAUDE_SETTINGS" ]] && [[ ! -f "$CLAUDE_SETTINGS_BAK" ]]; then
    cp "$CLAUDE_SETTINGS" "$CLAUDE_SETTINGS_BAK"
    echo "OK  ~/.claude/settings.json backed up to $CLAUDE_SETTINGS_BAK"
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
        'description': 'Caddy: CARL UserPromptSubmit hook (injects active rules from <workspace>/.carl/carl.json into every prompt). Bypass: remove this entry.',
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
echo "Done. Restart Claude Code (or run /mcp) to load carl-mcp in this workspace."
echo "      Seeded caddy-safety rules will activate on the next prompt submission."
echo ""
echo "Starter tools (8 of CARL's 30; v2 surface — see plugin README for full set):"
echo "  carl_v2_log_decision        carl_v2_search_decisions"
echo "  carl_v2_get_decisions       carl_v2_list_domains"
echo "  carl_v2_get_config          carl_v2_stage_proposal"
echo "  carl_v2_approve_proposal    carl_v2_get_staged"
```

## After running

Restart Claude Code (or run `/mcp` to reload servers) so the new `carl-mcp` entry in `.mcp.json` is picked up. The `/mcp` panel should then show `carl-mcp ✓ connected`, and the 30 `mcp__carl-mcp__*` tools become available alongside any existing `mcp__base-mcp__*` / `mcp__caddy*` tools.

## Customer-facing tool surface

CARL ships **30 MCP tools**. We recommend starting with these **8 v2 tools** (the operator-rhythm core):

1. **carl_v2_log_decision** — log a decision in the current workspace's CARL state
2. **carl_v2_search_decisions** — find past decisions by domain or text
3. **carl_v2_get_decisions** — list decisions in a domain
4. **carl_v2_list_domains** — see all CARL domains in this workspace
5. **carl_v2_get_config** — read current CARL config + active rules
6. **carl_v2_stage_proposal** — stage a new rule for approval
7. **carl_v2_approve_proposal** — promote staged proposal to active rule
8. **carl_v2_get_staged** — see what's pending approval

The remaining 22 tools (v1 legacy + v2 advanced: add_rule, remove_rule, replace_rules, archive_decision, update_config, etc.) are available via the same `mcp__carl-mcp__*` surface. v1 tools are kept for back-compat with existing CARL workspaces from caddy-live installs.

## Troubleshooting

- **`carl-mcp ✗ failed` after restart:** check `<workspace>/.carl/carl-mcp/index.js` exists and is readable. Check `<workspace>/.carl/carl-mcp/node_modules/@modelcontextprotocol/sdk/` exists. If either is missing, re-run this skill.
- **`.mcp.json` already had a broken carl-mcp entry:** this skill auto-repairs (case b). Re-run to fix.
- **Multiple workspaces:** run once per workspace where you want carl-mcp. Each gets its own `.carl/` directory.
- **CARL rules not injecting into prompts:** this skill auto-registers `carl-hook.py` in the Claude Code `settings.json` (Step 7; `~/.claude/settings.json` on macOS, `%USERPROFILE%\.claude\settings.json` on Windows). If it didn't fire, open that file and confirm a `UserPromptSubmit` entry whose `command` ends in `carl-hook.py` is present and that the referenced path resolves to a real file. On macOS the command is `python3 $(brew --prefix caddy-carl)/share/caddy-carl/hooks/carl-hook.py`; on Windows it is `"<scoop>\apps\python\current\python.exe" "<scoop>\apps\caddy-carl\current\share\caddy-carl\hooks\carl-hook.py"`. To force a re-register, remove the entry and re-run this skill.

## Notes

- This skill is **idempotent**: safe to run multiple times. Sub-cases (b repair) and (c keep) handle re-runs cleanly. Workspace template seeding only runs on first init (preserves prior CARL state). The caddy-safety domain seed (Step 6) preserves customer-edited rules and only updates unedited Caddy-shipped rules when the upstream version bumps. The hook registration (Step 7) skips if already registered.
- The skill writes to two locations:
  - `<workspace>/.carl/` (per-workspace CARL state, including the Caddy sidecar at `<workspace>/.carl/caddy-carl-state.json`)
  - `~/.claude/settings.json` (single entry: UserPromptSubmit hook for carl-hook.py — required for seeded rules to inject into prompts). A one-time backup is preserved at `~/.claude/settings.json.pre-caddy-carl.bak` before the first merge.
- No `~/.carl/` (global) mutations. No npm global pollution. carl-mcp dependencies (`@modelcontextprotocol/sdk`) are installed locally to the workspace via `npm install`.

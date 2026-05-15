---
description: "Wire CARL's carl-mcp server into the current Claude Code workspace, seed the Caddy-managed safety rules domain, and register the CARL UserPromptSubmit hook so rules inject into every prompt. Use after installing caddy-frameworks via Homebrew, before any session where you want CARL rule routing, decision logging tools, or safety-rule enforcement. One-time per workspace; idempotent (safe to re-run for repair). Triggers: 'set up carl', 'wire carl-mcp', 'carl-mcp failed', 'carl-mcp not running', '.mcp.json missing carl-mcp', missing caddy-safety rules, multi-action guardrail not firing, or any carl-mcp tool failing with missing-tool errors."
---

# /caddy:carl-setup

Wire the **carl-mcp** server into the current workspace.

CARL ships its global source files via the Homebrew tap (`brew install caddy-frameworks` lands the carl-core MCP source + workspace template under `/opt/homebrew/opt/caddy-carl/share/caddy-carl/`). But carl-mcp itself runs as a per-workspace stdio MCP server: a small Node.js process that Claude Code launches alongside the workspace. The server reads/writes `<workspace>/.carl/{carl.json, sessions/, decisions/, ...}`, so it has to live in **this** workspace, not globally.

This skill replicates Stage 5a of the caddy-live customer install (the proven workspace-MCP wiring logic) so that opening a new workspace requires one command, not a recovery procedure.

## Prerequisite

You must have `caddy-carl` installed via Homebrew (it ships the carl-mcp source files):

```bash
brew tap meetcaddy/caddy
brew install caddy-frameworks    # bundles caddy-carl alongside BASE + PAUL + SEED + Skillsmith + Aegis
caddy-link                       # symlinks BASE/PAUL/SEED/Skillsmith/Aegis into ~/.claude/
```

CARL is MCP-only (ships no slash commands or suite skill), so `caddy-link` doesn't create any `~/.claude/commands/carl/` symlinks. After `caddy-link`, CARL's source should be readable at `$(brew --prefix caddy-carl)/share/caddy-carl/mcp/`.

## What this skill does

For the workspace where Claude Code was launched (the directory containing the project files):

1. **Locate the CARL source** at `$(brew --prefix caddy-carl)/share/caddy-carl/` (Cellar path; resolved at runtime so `brew upgrade caddy-carl` automatically picks up new versions).
2. **Copy the MCP server** from `<carl-pkg>/mcp/` into `<workspace>/.carl/carl-mcp/`. carl-mcp's `index.js` uses `path.resolve(__dirname, '../..')` for workspace resolution, so it must live exactly at `<workspace>/.carl/carl-mcp/index.js`.
3. **Seed the workspace template** by copying `<carl-pkg>/carl-template/carl.json` into `<workspace>/.carl/carl.json` (the rules + domains + config file) and creating an empty `<workspace>/.carl/sessions/` directory. Only seeds if `<workspace>/.carl/carl.json` doesn't already exist (idempotent; preserves any prior CARL state).
4. **Run `npm install`** in the new `<workspace>/.carl/carl-mcp/` to fetch `@modelcontextprotocol/sdk`.
5. **Register the server** in `<workspace>/.mcp.json` with an **absolute path** to `<workspace>/.carl/carl-mcp/index.js`. Absolute paths are more robust than relative because Claude Code's CWD isn't guaranteed to match the workspace root (subdir launches, symlinked workspaces).
6. **Seed the Caddy-managed `caddy-safety` domain** into `<workspace>/.carl/carl.json` from `carl-rules/caddy-safety.json` shipped with this skill. Uses `lib/seed-carl-domain.py` so the seeder remains idempotent: customer-edited rules are preserved (DIVERGED), and unedited rules pick up upstream Caddy revisions automatically. Sidecar state lives at `<workspace>/.carl/caddy-carl-state.json` to track what's Caddy-shipped vs customer-modified.
7. **Register the CARL UserPromptSubmit hook** in `~/.claude/settings.json` pointing at `<carl-pkg>/hooks/carl-hook.py`. This is what makes seeded rules actually inject into every Claude Code prompt. Idempotent (skips if our entry is already present). One-time backup of pre-existing `~/.claude/settings.json` is written to `~/.claude/settings.json.pre-caddy-carl.bak` (preserves original snapshot across re-runs).

The `.mcp.json` mutation handles three sub-cases idempotently:

- **(a) merge:** no `carl-mcp` entry exists → add one alongside existing servers (preserves `base-mcp`, `caddy.draft`, etc.).
- **(b) repair:** an entry exists but `args[0]` points at a non-existent file → rewrite to the correct absolute path.
- **(c) keep:** an entry exists and works → leave alone. Safe to re-run.

## Execution

Determine the workspace root first. By default it's the current working directory; if the user is in a subdir, they should `cd` to the project root before running the skill (or pass the workspace path explicitly).

```bash
WORKSPACE="${WORKSPACE:-$(pwd)}"
CARL_PKG="$(brew --prefix caddy-carl 2>/dev/null)"
CARL_WORKSPACE_DIR="$WORKSPACE/.carl"
CARL_MCP_DIR="$CARL_WORKSPACE_DIR/carl-mcp"
WORKSPACE_MCP_JSON="$WORKSPACE/.mcp.json"

# Sanity: caddy-carl must be installed via brew
if [[ -z "$CARL_PKG" ]] || [[ ! -d "$CARL_PKG/share/caddy-carl/mcp" ]]; then
  echo "ERROR: caddy-carl Homebrew formula not installed."
  echo "  Run: brew tap meetcaddy/caddy && brew install caddy-frameworks"
  exit 1
fi

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
CARL_MCP_INDEX="$CARL_MCP_DIR/index.js"
PYTHON_BIN="$(command -v python3)"

if [[ ! -f "$CARL_MCP_INDEX" ]]; then
  echo "ERROR: $CARL_MCP_INDEX missing after copy"
  exit 1
fi

if [[ -f "$WORKSPACE_MCP_JSON" ]]; then
  MERGE_RESULT="$("$PYTHON_BIN" -c "
import json, os
path = '$WORKSPACE_MCP_JSON'
correct_index = '$CARL_MCP_INDEX'
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
    repaired) echo "OK  carl-mcp repaired in $WORKSPACE_MCP_JSON (path now $CARL_MCP_INDEX)" ;;
    kept)     echo "SKIP $WORKSPACE_MCP_JSON already has working carl-mcp entry" ;;
    *)        echo "FAIL merge unexpected result: $MERGE_RESULT"; exit 1 ;;
  esac
else
  cat > "$WORKSPACE_MCP_JSON" <<JSON_EOF
{
  "mcpServers": {
    "carl-mcp": {
      "type": "stdio",
      "command": "node",
      "args": ["$CARL_MCP_INDEX"]
    }
  }
}
JSON_EOF
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

CADDY_RULES_FILE="$SKILL_DIR/carl-rules/caddy-safety.json"
CADDY_SEEDER="$SKILL_DIR/lib/seed-carl-domain.py"
CADDY_CARL_JSON="$CARL_WORKSPACE_DIR/carl.json"
CADDY_STATE_FILE="$CARL_WORKSPACE_DIR/caddy-carl-state.json"

if [[ -f "$CADDY_SEEDER" ]] && [[ -f "$CADDY_RULES_FILE" ]]; then
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

# Step 7: register CARL UserPromptSubmit hook in ~/.claude/settings.json
#
# Without this, seeded rules sit in carl.json but never inject into prompts.
# Idempotent: detects existing carl-hook.py registration and skips if present.
# One-time backup of pre-existing settings.json is preserved across re-runs.

CARL_HOOK_PATH="$CARL_PKG/share/caddy-carl/hooks/carl-hook.py"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
CLAUDE_SETTINGS_BAK="$HOME/.claude/settings.json.pre-caddy-carl.bak"

if [[ -f "$CARL_HOOK_PATH" ]]; then
  # Backup once, preserving the true pre-Caddy snapshot across re-runs.
  if [[ -f "$CLAUDE_SETTINGS" ]] && [[ ! -f "$CLAUDE_SETTINGS_BAK" ]]; then
    cp "$CLAUDE_SETTINGS" "$CLAUDE_SETTINGS_BAK"
    echo "OK  ~/.claude/settings.json backed up to $CLAUDE_SETTINGS_BAK"
  fi

  HOOK_REG_RESULT="$("$PYTHON_BIN" -c "
import json, os, pathlib, sys
settings_path = pathlib.Path('$CLAUDE_SETTINGS')
hook_path = '$CARL_HOOK_PATH'
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
        if cmd.endswith('carl-hook.py') or hook_path in cmd:
            already = True
            break
    if already:
        break
if already:
    print('kept')
else:
    ups.append({
        'matcher': '*',
        'hooks': [{'type': 'command', 'command': 'python3 ' + hook_path}],
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
  echo "     Reinstall: brew reinstall caddy-carl"
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
- **CARL rules not injecting into prompts:** this skill auto-registers `carl-hook.py` in `~/.claude/settings.json` (Step 7). If it didn't fire, check whether the entry is present in your settings file and that `python3 $(brew --prefix caddy-carl)/share/caddy-carl/hooks/carl-hook.py` resolves to a real file. To force a re-register, remove the entry and re-run this skill.

## Notes

- This skill is **idempotent**: safe to run multiple times. Sub-cases (b repair) and (c keep) handle re-runs cleanly. Workspace template seeding only runs on first init (preserves prior CARL state). The caddy-safety domain seed (Step 6) preserves customer-edited rules and only updates unedited Caddy-shipped rules when the upstream version bumps. The hook registration (Step 7) skips if already registered.
- The skill writes to two locations:
  - `<workspace>/.carl/` (per-workspace CARL state, including the Caddy sidecar at `<workspace>/.carl/caddy-carl-state.json`)
  - `~/.claude/settings.json` (single entry: UserPromptSubmit hook for carl-hook.py — required for seeded rules to inject into prompts). A one-time backup is preserved at `~/.claude/settings.json.pre-caddy-carl.bak` before the first merge.
- No `~/.carl/` (global) mutations. No npm global pollution. carl-mcp dependencies (`@modelcontextprotocol/sdk`) are installed locally to the workspace via `npm install`.

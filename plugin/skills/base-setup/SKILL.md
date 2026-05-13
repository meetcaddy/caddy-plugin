---
description: "Wire BASE's base-mcp server into the current Claude Code workspace. Use after installing caddy-frameworks via Homebrew, before running /base:* commands that need workspace-state queries. One-time per workspace; idempotent (safe to re-run for repair). Triggers: 'set up base', 'wire base-mcp', 'base-mcp failed', 'base-mcp not running', '.mcp.json missing base-mcp', or any base: command failing with missing-tool errors."
---

# /caddy:base-setup

Wire the **base-mcp** server into the current workspace.

BASE ships its global pieces via the Homebrew tap (`brew install caddy-frameworks` drops slash commands + the skill + framework files into `~/.claude/`). But base-mcp itself runs as a per-workspace stdio MCP server: a small Node.js process that Claude Code launches alongside the workspace. The server reads/writes `<workspace>/.base/data/*.json` (project lists, decision logs, operator profile, etc.), so it has to live in **this** workspace, not globally.

This skill replicates Stage 5a of the caddy-live customer install (the proven workspace-MCP wiring logic) so that opening a new workspace requires one command, not a recovery procedure.

## Prerequisite

You must have `caddy-base` installed via Homebrew (it ships the base-mcp source files):

```bash
brew tap meetcaddy/caddy
brew install caddy-frameworks    # bundles caddy-base + 4 other frameworks
caddy-link                       # symlinks files into ~/.claude/
```

After `caddy-link`, the base-mcp source should be readable at `~/.claude/base-framework/packages/base-mcp/`.

## What this skill does

For the workspace where Claude Code was launched (the directory containing the project files):

1. **Copy the base-mcp source** from `~/.claude/base-framework/packages/base-mcp/` into `<workspace>/.base/base-mcp/`.
2. **Run `npm install`** in the new `<workspace>/.base/base-mcp/` to fetch `@modelcontextprotocol/sdk`.
3. **Register the server** in `<workspace>/.mcp.json` with an **absolute path** to `<workspace>/.base/base-mcp/index.js`. Absolute paths are more robust than relative because Claude Code's CWD isn't guaranteed to match the workspace root (subdir launches, symlinked workspaces).

The `.mcp.json` mutation handles three sub-cases idempotently:

- **(a) merge:** no `base-mcp` entry exists → add one alongside existing servers (preserves `caddy.draft`, `carl-mcp`, etc.).
- **(b) repair:** an entry exists but `args[0]` points at a non-existent file → rewrite to the correct absolute path. This is the "Arch-style failure" where registration exists but the path went stale.
- **(c) keep:** an entry exists and works → leave alone. Safe to re-run.

## Execution

Determine the workspace root first. By default it's the current working directory; if the user is in a subdir, they should `cd` to the project root before running the skill (or pass the workspace path explicitly).

```bash
WORKSPACE="${WORKSPACE:-$(pwd)}"
BASE_GLOBAL_SRC="$HOME/.claude/base-framework/packages/base-mcp"
BASE_WORKSPACE_DIR="$WORKSPACE/.base"
BASE_MCP_DIR="$BASE_WORKSPACE_DIR/base-mcp"
WORKSPACE_MCP_JSON="$WORKSPACE/.mcp.json"

# Sanity: source must exist (caddy-link should have placed it)
if [[ ! -d "$BASE_GLOBAL_SRC" ]]; then
  echo "ERROR: $BASE_GLOBAL_SRC missing. Run 'brew install caddy-frameworks && caddy-link' first."
  exit 1
fi

# Step 1: copy base-mcp into workspace
if [[ -f "$BASE_MCP_DIR/index.js" ]]; then
  echo "SKIP $BASE_MCP_DIR (already present)"
else
  mkdir -p "$BASE_WORKSPACE_DIR"
  cp -R "$BASE_GLOBAL_SRC" "$BASE_MCP_DIR"
  echo "OK  base-mcp source copied to $BASE_MCP_DIR"
fi

# Step 2: npm install dependencies (only if missing)
if [[ -d "$BASE_MCP_DIR/node_modules/@modelcontextprotocol/sdk" ]]; then
  echo "SKIP node_modules (already installed)"
else
  if (cd "$BASE_MCP_DIR" && npm install >/dev/null 2>&1); then
    echo "OK  npm install succeeded"
  else
    echo "FAIL npm install. Run manually: cd $BASE_MCP_DIR && npm install"
    exit 1
  fi
fi

# Step 3: register in .mcp.json (merge / repair / keep)
BASE_MCP_INDEX="$BASE_MCP_DIR/index.js"
PYTHON_BIN="$(command -v python3)"

if [[ ! -f "$BASE_MCP_INDEX" ]]; then
  echo "ERROR: $BASE_MCP_INDEX missing after copy"
  exit 1
fi

if [[ -f "$WORKSPACE_MCP_JSON" ]]; then
  MERGE_RESULT="$("$PYTHON_BIN" -c "
import json, os
path = '$WORKSPACE_MCP_JSON'
correct_index = '$BASE_MCP_INDEX'
with open(path) as f:
    data = json.load(f)
servers = data.setdefault('mcpServers', {})
existing = servers.get('base-mcp')
action = 'unknown'
if existing is None:
    servers['base-mcp'] = {'type': 'stdio', 'command': 'node', 'args': [correct_index]}
    action = 'merged'
else:
    args = existing.get('args') or []
    current_path = args[0] if args else None
    if current_path and os.path.isfile(current_path):
        action = 'kept'
    else:
        servers['base-mcp'] = {'type': 'stdio', 'command': 'node', 'args': [correct_index]}
        action = 'repaired'
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
print(action)
")"
  case "$MERGE_RESULT" in
    merged)   echo "OK  base-mcp merged into $WORKSPACE_MCP_JSON" ;;
    repaired) echo "OK  base-mcp repaired in $WORKSPACE_MCP_JSON (path now $BASE_MCP_INDEX)" ;;
    kept)     echo "SKIP $WORKSPACE_MCP_JSON already has working base-mcp entry" ;;
    *)        echo "FAIL merge unexpected result: $MERGE_RESULT"; exit 1 ;;
  esac
else
  cat > "$WORKSPACE_MCP_JSON" <<JSON_EOF
{
  "mcpServers": {
    "base-mcp": {
      "type": "stdio",
      "command": "node",
      "args": ["$BASE_MCP_INDEX"]
    }
  }
}
JSON_EOF
  echo "OK  $WORKSPACE_MCP_JSON created with base-mcp registration"
fi

echo ""
echo "Done. Restart Claude Code (or run /mcp) to load base-mcp in this workspace."
```

## After running

The customer should restart Claude Code (or run `/mcp` to reload servers) so the new `base-mcp` entry in `.mcp.json` is picked up. The `/mcp` panel should then show `base-mcp ✓ connected`, and `mcp__base-mcp__*` tools become available alongside any existing `mcp__caddy*` tools.

## Troubleshooting

- **`base-mcp ✗ failed` after restart:** check `<workspace>/.base/base-mcp/index.js` exists and is readable. Check `<workspace>/.base/base-mcp/node_modules/@modelcontextprotocol/sdk/` exists. If either is missing, re-run this skill.
- **`.mcp.json` already had a broken base-mcp entry:** this skill auto-repairs (case b). Re-run to fix.
- **Multiple workspaces:** run once per workspace where you want base-mcp. Each gets its own `.base/` directory.

## Notes

- This skill is **idempotent**: safe to run multiple times. Sub-cases (b repair) and (c keep) handle re-runs cleanly.
- The skill **does not write outside the current workspace**. No `~/.claude/` mutations, no global state changes. Customer-data-local promise preserved.
- base-mcp dependencies (`@modelcontextprotocol/sdk`) are installed locally to the workspace via `npm install`. No global npm pollution.

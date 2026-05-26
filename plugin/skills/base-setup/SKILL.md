---
description: "Wire BASE's base-mcp server so it loads in EVERY Claude Code session, machine-wide, with no workspace folder to remember. Installs base-mcp once at a fixed Caddy home (~/.caddy/base) and registers it at Claude Code user scope. Use after installing caddy-frameworks. One-time per machine; idempotent (safe to re-run for repair). Triggers: 'set up base', 'wire base-mcp', 'base-mcp failed', 'base-mcp not running', 'base-mcp missing', or any base: command failing with missing-tool errors."
---

# /caddy:base-setup

Wire the **base-mcp** server so BASE is available in every Claude Code session, no matter which folder Claude was started from.

BASE ships its global pieces via the framework installer (`caddy-frameworks` drops slash commands + the skill + framework files into `~/.claude/`). base-mcp itself is a small Node.js stdio MCP server. This skill installs it **once at a fixed location** (`~/.caddy/base`) and registers it at Claude Code's **user scope**, so Claude loads it in every session automatically. The customer never has to launch from a special folder.

base-mcp resolves its data location from its own install path (`path.resolve(__dirname, '../..')`), so installing it at `~/.caddy/base/.base/base-mcp/` makes `~/.caddy/base` BASE's single, always-on workspace, with data at `~/.caddy/base/.base/data/`.

## Prerequisite

`caddy-base` installed via the OS package manager (it ships the base-mcp source), then `caddy-link` run so the source is readable under `~/.claude/` (macOS: `$HOME/.claude`; Windows: `%USERPROFILE%\.claude`):

- macOS: `brew tap meetcaddy/caddy && brew install caddy-frameworks && caddy-link`
- Windows: `scoop bucket add caddy https://github.com/meetcaddy/scoop-caddy && scoop install caddy-frameworks && caddy-link`

After `caddy-link`, the base-mcp source is readable at `<claude-dir>/base-framework/packages/base-mcp/`.

## What this skill does

1. **Copy the base-mcp source** from `<claude-dir>/base-framework/packages/base-mcp/` into the fixed path `~/.caddy/base/.base/base-mcp/`.
2. **Run `npm install`** there to fetch `@modelcontextprotocol/sdk` (only if missing).
3. **Register base-mcp at Claude Code user scope** via `claude mcp add --scope user`, with an absolute path to the fixed `index.js`. User scope means Claude loads it in every session, every directory, with no per-folder `.mcp.json`. The registration is made idempotent by removing any existing user-scope `base-mcp` entry first, then adding fresh (so a re-run repairs a stale path cleanly).

This is one global BASE workspace per machine. That is intentional: a Caddy customer has one Caddy, always on, not a separate one per folder.

## Execution

This block runs in bash on both OSes (on Windows that is the Git Bash Claude Code uses). Only the home directory, the source location, and the path-persist form differ by OS; everything after the preamble is shared.

```bash
# --- OS-aware resolution preamble -------------------------------------------
# CLAUDE_DIR  : where caddy-link placed the framework source + where Claude
#               Code reads user config (macOS $HOME/.claude; Windows
#               %USERPROFILE%\.claude, resolved from USERPROFILE, not $HOME,
#               because corporate AD can redirect Git Bash $HOME to a share
#               Claude Code never reads).
# CADDY_HOME  : fixed Caddy home that becomes BASE's single workspace.
# to_persist(): path form written into config / passed to node. Identity on
#               macOS; Windows mixed-slash (cygpath -m: C:/Users/...) so node
#               accepts it with no JSON backslash escaping.
case "$(uname -s)" in
  Darwin)
    CLAUDE_DIR="$HOME/.claude"
    CADDY_HOME="$HOME/.caddy/base"
    to_persist() { printf '%s' "$1"; }
    PKG_HINT="brew tap meetcaddy/caddy && brew install caddy-frameworks && caddy-link"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    CLAUDE_DIR="$(cygpath -u "$USERPROFILE" 2>/dev/null || printf '%s' "$HOME")/.claude"
    CADDY_HOME="$(cygpath -u "$USERPROFILE" 2>/dev/null || printf '%s' "$HOME")/.caddy/base"
    to_persist() { cygpath -m "$1"; }
    PKG_HINT="scoop bucket add caddy https://github.com/meetcaddy/scoop-caddy && scoop install caddy-frameworks && caddy-link"
    ;;
  *)
    echo "ERROR: unsupported OS '$(uname -s)' for /caddy:base-setup (macOS and Windows only)."
    exit 1
    ;;
esac

BASE_GLOBAL_SRC="$CLAUDE_DIR/base-framework/packages/base-mcp"
BASE_WORKSPACE_DIR="$CADDY_HOME/.base"
BASE_MCP_DIR="$BASE_WORKSPACE_DIR/base-mcp"
# ---------------------------------------------------------------------------

# Sanity: source must exist (caddy-link should have placed it)
if [[ ! -d "$BASE_GLOBAL_SRC" ]]; then
  echo "ERROR: $BASE_GLOBAL_SRC missing. Run: $PKG_HINT"
  exit 1
fi

# Step 1: copy base-mcp into the fixed Caddy home
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

# Step 3: register base-mcp at Claude Code USER scope (loads in every session)
BASE_MCP_INDEX="$BASE_MCP_DIR/index.js"
if [[ ! -f "$BASE_MCP_INDEX" ]]; then
  echo "ERROR: $BASE_MCP_INDEX missing after copy"
  exit 1
fi
BASE_MCP_INDEX_PERSIST="$(to_persist "$BASE_MCP_INDEX")"

# Idempotent: drop any prior user-scope entry, then add fresh. `remove`
# tolerates "not found"; the explicit re-add guarantees a correct path on
# every run (this is how a stale-path repair happens now).
claude mcp remove base-mcp --scope user >/dev/null 2>&1 || true
if claude mcp add --scope user base-mcp -- node "$BASE_MCP_INDEX_PERSIST" >/dev/null 2>&1; then
  echo "OK  base-mcp registered at Claude Code user scope -> $BASE_MCP_INDEX_PERSIST"
else
  echo "FAIL 'claude mcp add --scope user base-mcp' did not succeed."
  echo "     Run manually: claude mcp add --scope user base-mcp -- node \"$BASE_MCP_INDEX_PERSIST\""
  exit 1
fi

echo ""
echo "Done. base-mcp now loads in every Claude Code session, from any folder."
echo "Restart Claude Code (or run /mcp) to load it now."
```

## After running

Restart Claude Code (or run `/mcp`). `/mcp` shows `base-mcp ✓ connected` in **every** session regardless of which directory Claude was started in, and `mcp__base-mcp__*` tools are available. There is no workspace folder to remember.

## Troubleshooting

- **`base-mcp ✗ failed`:** check `~/.caddy/base/.base/base-mcp/index.js` and its `node_modules/@modelcontextprotocol/sdk/` exist. If missing, re-run this skill.
- **`base-mcp` not listed by `/mcp` at all:** confirm the user-scope registration with `claude mcp get base-mcp`. Re-run this skill to repair.
- **Stale path after a move:** re-run this skill; Step 3 removes and re-adds, fixing the path.

## Notes

- **Idempotent**: safe to re-run; Step 3's remove-then-add repairs a stale path cleanly.
- **One global BASE workspace** at `~/.caddy/base`, by design. Not per project folder.
- This skill writes to `~/.caddy/base/` and adds one **user-scope** MCP entry via the `claude mcp` CLI (never by hand-editing `~/.claude.json`, which holds session/cache state). No npm global pollution; dependencies are local to `~/.caddy/base/.base/base-mcp/`.

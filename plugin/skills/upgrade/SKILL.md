---
description: "Upgrade your Caddy install to the latest release in one command. Updates the Caddy frameworks (BASE, CARL, PAUL, SEED, Skillsmith, Aegis) via your OS package manager, refreshes the framework junctions with caddy-link, and walks you through the in-Claude plugin update + verification. End-to-end. Use whenever you see a Caddy release announcement, hi@meetcaddy.com tells you to update, or you just want the latest. Triggers: 'upgrade caddy', 'update caddy', 'caddy update', 'caddy upgrade', 'pull the latest caddy', 'new caddy version', 'release announcement', 'I want the latest'."
---

# /caddy:upgrade

Update your Caddy install to the latest release. Two-pass flow:

- **Pass 1 (this skill, automated):** OS package manager upgrades the Caddy frameworks (`brew upgrade` on Mac, `scoop update` on Windows), then re-runs `caddy-link` to refresh the framework junctions in your Claude Code config directory.
- **Pass 2 (you, two lines):** `/plugin update caddy@meet-caddy` and `/reload-plugins`. The skill prints both. Plugin updates have to be initiated by you inside Claude Code; skills can't run `/plugin` commands themselves.
- **Verification:** the skill ends by suggesting `/mcp` and `/caddy:verify` to confirm the upgrade landed cleanly.

Total time: 2 to 5 minutes depending on what's being pulled.

## Prerequisite

You must have Caddy installed already. If you do not, follow the install guide instead of this skill. The skill expects `brew` (macOS) or `scoop` (Windows) and `caddy-link` to be on your `PATH`.

## What this skill touches (and does not)

**Touches:** the framework formulas (BASE, CARL, PAUL, SEED, Skillsmith, Aegis) installed via Homebrew / Scoop, and the framework junctions in `~/.claude/` (or `%USERPROFILE%\.claude\` on Windows).

**Does NOT touch:** your local data (`~/.caddy/`, `~/.carl/`, voice.md, brand.md), your access token, Claude Code itself, your Claude Pro/Max subscription, Git for Windows, or any non-Caddy MCP entries in your Claude Code config.

Safe to re-run. If everything is already up-to-date, the package-manager step no-ops and `caddy-link` re-establishes junctions (also a no-op if they are already correct).

## Execution

This block runs in bash on both OSes (Git Bash on Windows). Only the package-manager invocation differs by OS; everything after the preamble is shared.

```bash
# --- OS-aware preamble -----------------------------------------------------
case "$(uname -s)" in
  Darwin)
    PKG_NAME="Homebrew"
    FRAMEWORK_UPGRADE_CMD="brew upgrade caddy-frameworks"
    PRE_CHECK_CMD="brew"
    INSTALL_HINT="brew tap meetcaddy/caddy && brew install caddy-frameworks"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    PKG_NAME="Scoop"
    FRAMEWORK_UPGRADE_CMD="scoop update caddy-frameworks"
    PRE_CHECK_CMD="scoop"
    INSTALL_HINT="scoop bucket add caddy https://github.com/meetcaddy/scoop-caddy && scoop install caddy-frameworks"
    ;;
  *)
    echo "ERROR: unsupported OS '$(uname -s)' for /caddy:upgrade (macOS and Windows only)."
    exit 1
    ;;
esac

# Sanity: package manager available
if ! command -v "$PRE_CHECK_CMD" >/dev/null 2>&1; then
  echo "ERROR: $PKG_NAME is not on PATH. Caddy depends on it."
  echo "       If $PKG_NAME is installed but not visible here, open a fresh terminal and try again."
  echo "       If $PKG_NAME is not installed, run: $INSTALL_HINT"
  exit 1
fi
# ---------------------------------------------------------------------------

echo ""
echo "================================================================"
echo "/caddy:upgrade, Pass 1 of 2 (framework layer)"
echo "================================================================"

echo ""
echo "=== Step 1: framework upgrade via $PKG_NAME ==="
echo ""
echo "    [1a] Refresh $PKG_NAME index (so it sees the latest Caddy release)..."
case "$(uname -s)" in
  Darwin)
    if brew update >/dev/null 2>&1; then
      echo "    OK   brew update (tap index refreshed)"
    else
      echo "    WARN brew update returned non-zero (network glitch?); continuing"
    fi
    ;;
  *)
    if scoop update >/dev/null 2>&1; then
      echo "    OK   scoop update (bucket index refreshed)"
    else
      echo "    WARN scoop update returned non-zero (network glitch?); continuing"
    fi
    ;;
esac

echo ""
echo "    [1b] Running: $FRAMEWORK_UPGRADE_CMD"
echo ""
if $FRAMEWORK_UPGRADE_CMD; then
  echo ""
  echo "OK   framework upgrade complete"
else
  echo ""
  echo "FAIL $FRAMEWORK_UPGRADE_CMD did not finish cleanly."
  echo "     Run it directly in your terminal to see the full error, then re-run /caddy:upgrade."
  exit 1
fi

echo ""
echo "=== Step 2: refresh framework junctions via caddy-link ==="
if ! command -v caddy-link >/dev/null 2>&1; then
  echo "FAIL caddy-link not found on PATH after framework upgrade."
  echo "     Reinstall the frameworks: $INSTALL_HINT"
  exit 1
fi
if caddy-link; then
  echo ""
  echo "OK   caddy-link refreshed"
else
  echo ""
  echo "FAIL caddy-link did not finish cleanly. Run 'caddy-link' directly to see the full error."
  exit 1
fi

echo ""
echo "================================================================"
echo "Pass 1 done. Two more lines to finish the upgrade."
echo "================================================================"

echo ""
echo "=== Step 3 (you): update the Caddy plugin ==="
echo "    Type this exact line in Claude Code (right here) and press Enter:"
echo ""
echo "      /plugin update caddy@meet-caddy"
echo ""
echo "    Wait for: 'Updated caddy. Run /reload-plugins to apply.'"

echo ""
echo "=== Step 4 (you): reload plugins ==="
echo "    Type this exact line and press Enter:"
echo ""
echo "      /reload-plugins"
echo ""
echo "    Wait for: 'Reloaded: <N> plugins ...'"

echo ""
echo "=== Step 5 (you): verify ==="
echo "    Confirm everything connected:"
echo ""
echo "      /mcp"
echo ""
echo "    Expected: 'caddy', 'base-mcp', and 'carl-mcp' all show connected."
echo "    For a deeper health check (recommended):"
echo ""
echo "      /caddy:verify"

echo ""
echo "================================================================"
echo "Done. If /mcp or /caddy:verify report anything failed, email"
echo "hi@meetcaddy.com with the exact lines they printed."
echo "================================================================"
```

## After running

Pass 1 (this skill) updates the framework layer. Pass 2 + verification (Steps 3 to 5 above) finish the upgrade. Once `/mcp` shows all three servers connected, you are on the latest Caddy.

## Troubleshooting

**Pass 1 fails on `brew upgrade caddy-frameworks` with "no such formula":** the Caddy Homebrew tap is not active. Run `brew tap meetcaddy/caddy` and retry.

**Pass 1 fails on `scoop update caddy-frameworks` with "could not find manifest":** the Caddy Scoop bucket is not active. Run `scoop bucket add caddy https://github.com/meetcaddy/scoop-caddy` and retry.

**`caddy-link` reports "permission denied":** on macOS run `sudo chown -R "$(whoami)" ~/.claude` then re-run `caddy-link`. On Windows this is rare; if it happens, close Claude Code (including Task Manager force-quit of any "Claude" processes) and re-run.

**Pass 2 `/plugin update` says "already up to date":** the plugin payload had nothing newer to fetch. Skip to Step 5; the framework upgrade from Pass 1 still did real work.

**`/mcp` shows a server failed after upgrade:** the most common cause is a leftover per-folder `.mcp.json` shadowing the user-scope registration (the Option 2 migration footgun). Run `/caddy:verify`, check 7 will detect any shadow file and print the exact rename command.

**Anything else:** email hi@meetcaddy.com with the exact line that failed.

## Notes

- **Idempotent**: safe to re-run anytime. Useful if you want to confirm you are on the latest.
- **Does not modify your data**: `~/.caddy/`, `~/.carl/`, `~/.caddy/voice.md`, `~/.caddy/brand.md`, and any decisions you have logged are not touched.
- **Does not update Claude Code itself**: that is the official Claude Code update mechanism (`claude --version` to check; Claude Code prompts on its own when an update is available).
- **One-time setup state**: if a Caddy release changes how BASE or CARL set themselves up, the release notes will tell you to re-run `/caddy:base-setup` and `/caddy:carl-setup`. The skill flags this when it applies.

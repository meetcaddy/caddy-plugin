#!/usr/bin/env python3
"""
caddy-agent-audit — security scan of an AI agent harness config. Read-only (never executes findings).
Scans CLAUDE.md, .claude/settings*.json, .mcp.json, hooks, and skills for leaked secrets, dangerous
hook commands, risky permissions, MCP exposure, and the injection-capable hook-event surface.

Usage:
  python3 scan.py                      # ~/.claude, ~/.mcp.json, ~/.claude.json
  python3 scan.py --target /path/proj  # + a project's .claude + .mcp.json (ACE client audit)
"""
import argparse, os, re, glob, json
from collections import Counter

SECRET_PATTERNS = [
    ("CRITICAL", "OpenAI/Anthropic-style key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("CRITICAL", "Stripe/processor secret key", re.compile(r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{16,}")),
    ("CRITICAL", "GitHub token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}")),
    ("CRITICAL", "AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("CRITICAL", "Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("HIGH", "GHL Private Integration Token", re.compile(r"\bpit-[A-Za-z0-9\-]{16,}")),
    ("HIGH", "Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("HIGH", "Inline Bearer token", re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{24,}")),
    ("HIGH", "JWT (possible token)", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{6,}")),
    ("HIGH", "Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("MEDIUM", "Plaintext secret assignment (quoted)", re.compile(
        r"(?i)(password|secret|api[_-]?key|client[_-]?secret|token)\s*[:=]\s*[\"'][^\"']{10,}[\"']")),
    ("MEDIUM", "Secret in env-style assignment", re.compile(
        r"^[A-Z][A-Z0-9_]*(SECRET|TOKEN|KEY|PASSWORD|PASS)\s*=\s*\S{12,}")),
]
DANGEROUS_CMD = re.compile(
    r"(?i)(rm\s+-rf\s|curl[^\n|]*\|\s*(ba)?sh|wget[^\n|]*\|\s*sh|base64\s+-d[^\n|]*\|\s*(ba)?sh|"
    r"\beval\s|chmod\s+777|--no-verify|core\.hooksPath)")
RISKY_PERM = re.compile(
    r"(?i)(dangerouslySkipPermissions|skipDangerousModePermissionPrompt)\"?\s*[:=]\s*true|"
    r"\"Bash\(\*\)\"|\"allow\"\s*:\s*\[\s*\"\*\"")

# --- Hook-event surface (validated against Claude Code hooks docs, 2026-06) -----------------
# Configuring one of these events is NORMAL; the audit surfaces them so a reviewer can confirm the
# handler is trusted. The real risk is what the HANDLER does (see RISKY_HOOK_OUTPUT below).
INJECTION_EVENTS = {
    "PreToolUse":        "can rewrite tool input (updatedInput) and allow/deny/ask on tool calls",
    "UserPromptSubmit":  "can inject text into the prompt (additionalContext) or block it",
    "UserPromptExpansion": "can block or rewrite slash-command expansion",
    "PermissionRequest": "can auto-approve/deny permissions or switch permission mode",
    "ConfigChange":      "fires on settings/skills changes; a handler here can mask config tampering",
    "SessionStart":      "injects context at every session start (additionalContext)",
    "InstructionsLoaded": "fires when CLAUDE.md/rules load; can react to instruction content",
    "MessageDisplay":    "can suppress or alter what is shown to the user (decision: block)",
    "Elicitation":       "can intercept/rewrite MCP server prompts",
    "ElicitationResult": "can modify the user's response before the MCP server receives it",
    "Stop":              "can block turn completion (force more work)",
}
# A handler that contains these is ACTIVELY mutating/injecting/auto-approving — higher severity.
RISKY_HOOK_OUTPUT = [
    ("HIGH",   "hook auto-approves permissions / switches mode",
     re.compile(r"(?i)(\"?behavior\"?\s*[:=]\s*\"allow\"|\"?permissionDecision\"?\s*[:=]\s*\"allow\"|updatedPermissions|setMode|defaultMode)")),
    ("HIGH",   "hook rewrites tool input before execution",
     re.compile(r"(?i)\bupdatedInput\b")),
    ("MEDIUM", "hook injects context into the model",
     re.compile(r"(?i)\badditionalContext\b")),
    ("MEDIUM", "hook can suppress/block output or turns",
     re.compile(r"(?i)\"?decision\"?\s*[:=]\s*\"block\"")),
]
HOME_GLOBS = [
    "~/.claude/CLAUDE.md", "~/.claude/settings.json", "~/.claude/settings.local.json",
    "~/.mcp.json", "~/.claude.json", "~/.claude/hooks/*", "~/.claude/agents/*",
    "~/.claude/skills/*/SKILL.md", "~/.claude/commands/**/*.md",
]
PROJ_GLOBS = ["CLAUDE.md", ".claude/CLAUDE.md", ".claude/settings.json",
              ".claude/settings.local.json", ".mcp.json", ".env", ".envrc",
              ".claude/commands/**/*.md"]
# Tool scripts the config actually invokes — where a leaked cred or dangerous command would live.
# (SKILL.md alone misses the .py/.js/.sh the skill runs.) node_modules etc. pruned so it doesn't explode.
SCRIPT_ROOTS_HOME = ["~/.claude/skills", "~/.claude/hooks"]
SCRIPT_EXTS = (".py", ".js", ".sh", ".ts")
PRUNE_DIRS = {"node_modules", "__pycache__", ".git", "dist", "build", ".venv", "venv", ".next"}


def _walk_scripts(root):
    root = os.path.expanduser(root)
    if not os.path.isdir(root):
        return
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in PRUNE_DIRS]
        for fn in fns:
            if fn.endswith(SCRIPT_EXTS) and not fn.endswith((".min.js", ".map")):
                yield os.path.join(dp, fn)


def collect(target=None):
    fs = set()
    for g in HOME_GLOBS:
        for p in glob.glob(os.path.expanduser(g), recursive=True):
            if os.path.isfile(p):
                fs.add(p)
    for root in SCRIPT_ROOTS_HOME:
        fs.update(_walk_scripts(root))
    for p in glob.glob(os.path.expanduser("~/.config/*/.env")):
        if os.path.isfile(p):
            fs.add(p)
    if target:
        for g in PROJ_GLOBS:
            for p in glob.glob(os.path.join(target, g), recursive=True):
                if os.path.isfile(p):
                    fs.add(p)
        fs.update(_walk_scripts(os.path.join(target, ".claude")))
    return sorted(fs)


def line_of(txt, needle):
    for i, line in enumerate(txt.splitlines(), 1):
        if needle in line:
            return i
    return 1


def scan_text_for_handler_risk(txt, path, out, label_prefix=""):
    """Scan a hook handler's source (or inline command) for active mutation/injection + secrets."""
    for sev, label, pat in RISKY_HOOK_OUTPUT:
        m = pat.search(txt)
        if m:
            out.append((sev, f"{label_prefix}{label}", path, line_of(txt, m.group(0).split('"')[0] or m.group(0))))
    for sev, label, pat in SECRET_PATTERNS:
        m = pat.search(txt)
        if m:
            out.append((sev, f"{label_prefix}{label}", path, line_of(txt, m.group(0))))
    # NOTE: we deliberately do NOT blanket-scan handler SOURCE for dangerous command strings —
    # regex pattern libraries, comments, and echo strings produce false positives (e.g. a security
    # guard that defines `rm -rf` patterns). Inline dangerous commands in settings/hooks files are
    # still caught line-by-line in scan(); active mutation is caught by RISKY_HOOK_OUTPUT above.


def walk_hook_entries(node, event, txt, path, out, seen):
    """node = list of hook matcher-groups for an event. Inspect type/command/url + referenced scripts."""
    if not isinstance(node, list):
        return
    for grp in node:
        for h in (grp.get("hooks", []) if isinstance(grp, dict) else []):
            if not isinstance(h, dict):
                continue
            htype = (h.get("type") or "").lower()
            url = h.get("url")
            cmd = h.get("command") or ""
            if htype == "http" or url:
                sev = "CRITICAL" if h.get("allowedEnvVars") else "HIGH"
                env = " (forwards env vars, secret-exfil risk)" if h.get("allowedEnvVars") else ""
                out.append((sev, f"{event} hook posts to an external endpoint{env}", path, line_of(txt, "http")))
            if cmd:
                # inline command string risk
                scan_text_for_handler_risk(cmd, path, out, label_prefix=f"{event} ")
                if DANGEROUS_CMD.search(cmd):
                    pass  # already covered by scan_text_for_handler_risk
                # follow a referenced local script and scan its source
                for tok in re.findall(r"[~./][\w./\-]+\.(?:py|sh|js|ts|rb)", cmd):
                    sp = os.path.expanduser(tok)
                    if os.path.isfile(sp) and sp not in seen:
                        seen.add(sp)
                        try:
                            stxt = open(sp, errors="ignore").read()
                            scan_text_for_handler_risk(stxt, sp, out, label_prefix=f"{event} handler: ")
                        except Exception:
                            pass


def analyze_hooks(path, txt, out, seen):
    """Parse a settings file's hooks block and flag injection-capable events + risky handlers."""
    try:
        data = json.loads(txt)
    except Exception:
        # tolerant fallback: just flag configured injection-capable event names
        for ev, why in INJECTION_EVENTS.items():
            if re.search(r'"%s"' % re.escape(ev), txt):
                out.append(("INFO", f"injection-capable hook configured: {ev} ({why}); verify handler is trusted",
                            path, line_of(txt, '"%s"' % ev)))
        return
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return
    for ev, node in hooks.items():
        if ev in INJECTION_EVENTS:
            out.append(("INFO", f"injection-capable hook configured: {ev} ({INJECTION_EVENTS[ev]}); verify handler is trusted",
                        path, line_of(txt, '"%s"' % ev)))
        walk_hook_entries(node, ev, txt, path, out, seen)


def scan(path, out, seen):
    try:
        if os.path.getsize(path) > 512 * 1024:   # skip very large files (perf; not config)
            return
        txt = open(path, errors="ignore").read()
    except Exception:
        return
    name = os.path.basename(path)
    is_settings = name.startswith("settings") or name == "hooks.json" or "/hooks/" in path
    is_script = path.endswith(SCRIPT_EXTS)   # tool scripts: scan for secrets, but NOT config-perm checks
    world_readable = False
    try:
        world_readable = bool(os.stat(path).st_mode & 0o044)
    except Exception:
        pass
    for i, line in enumerate(txt.splitlines(), 1):
        for sev, label, pat in SECRET_PATTERNS:
            if pat.search(line):
                extra = " (file is group/other-readable; chmod 600)" if world_readable else ""
                out.append((sev, f"{label} in config{extra}", path, i))
        if is_settings and DANGEROUS_CMD.search(line):
            out.append(("HIGH", "Dangerous command in hook/settings", path, i))
        if not is_script and RISKY_PERM.search(line):   # config-perm check; skip tool-script source
            out.append(("HIGH", "Risky permission (skip-permissions / Bash(*) / allow *)", path, i))
    # hook-event surface analysis on settings/hooks JSON
    if name.startswith("settings") or name == "hooks.json":
        analyze_hooks(path, txt, out, seen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target")
    a = ap.parse_args()
    files = collect(a.target)
    out, seen = [], set()
    for p in files:
        scan(p, out, seen)
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    # de-dupe identical findings
    out = sorted(set(out), key=lambda f: (order.get(f[0], 9), f[2], f[3]))
    print(f"caddy-agent-audit v0.3: scanned {len(files)} file(s)\n")
    if not out:
        print("No findings. Agent config looks clean.")
    else:
        for sev, msg, path, line in out:
            rel = path.replace(os.path.expanduser("~"), "~")
            print(f"[{sev}] {msg}\n        {rel}:{line}")
        c = Counter(f[0] for f in out)
        print("\nSummary: " + ", ".join(f"{k}={c[k]}" for k in sorted(c, key=lambda x: order.get(x, 9))))
    print("\nNotes:")
    print(" - A secret in a LOCAL config (e.g. ~/.mcp.json MCP token) is expected for auth. Keep it "
          "chmod 600 and uncommitted, not necessarily a breach.")
    print(" - INFO 'injection-capable hook configured' is not a vulnerability by itself; hooks are "
          "designed to do this. It flags the handler for a trust review (critical on a CLIENT's config).")


if __name__ == "__main__":
    main()

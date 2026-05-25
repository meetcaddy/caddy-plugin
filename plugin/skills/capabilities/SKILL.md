---
description: Show the customer why their Caddy install is worth more than raw Claude or raw Claude Code. Use when the user types /caddy:capabilities, /caddy:what-can-you-do, /caddy:overview, /caddy:why, /caddy:worth-it, or asks variations like "what can Caddy do", "why pay for Caddy", "why not just use Claude", "what makes Caddy worth it", "remind me what I'm paying for", "what do I have", "what's installed", "show me my Caddy". Leads with the value contrast against raw Claude (the actual question customers are asking), then shows the 140+ capability toolkit as proof. Personalizes the close with a Day 1 setup path for new installs and compounding-moat language for mature ones. Optional second word drills in: vs-claude, planning, ideation, workspace, voice, security, build, rules, setup, or try.
---

# Caddy: Capabilities

This is the skill customers hit when they're either (a) new and asking "did I waste my money," or (b) returning and asking "remind me why this is special." Both questions have the same real answer: Caddy is the operating system that turns raw Claude into something that runs your business. This skill must deliver that answer fast, then back it up with proof.

The output has three jobs, in priority order:
1. **Justify the spend.** Show what Caddy does that raw Claude and raw Claude Code cannot.
2. **Show the toolkit.** 140+ capabilities across 7 systems, framed as evidence of #1.
3. **Give the customer one next move.** Day 1 path for new installs, compounding move for mature ones.

This skill never makes a backend call. Pure local read of `~/.caddy/` plus the canonical inventory in this file.

## Pre-flight

Read these local files if they exist. Each one missing is a Day 1 signal, not a failure. Continue regardless.

1. `~/.caddy/voice.md` — voice fingerprint
2. `~/.caddy/brand.md` — brand context
3. `~/.caddy/config.json` — connector setup

Compute a "maturity tier" from what's present:
- **Day 1** = 0 or 1 of the three files present
- **Activated** = 2 of the three present
- **Compounding** = all 3 present AND `~/.caddy/voice.md` is at least 500 bytes (proxy for a serious intake, not a stub)

The voice.md size check is the engagement signal. A real intake produces a multi-paragraph fingerprint; a stub file is a few sentences. We do not need to scan global memory for this; voice.md depth is a reliable proxy for "this customer has invested time."

This tier drives the personalization at the end of the output.

## Inputs

`$ARGUMENTS` is the rest of the line after `/caddy:capabilities`. Valid second words:

- (empty) — full overview (default)
- `vs-claude` or `why` — just the price-justification contrast, no inventory
- `planning` — drill into PAUL
- `ideation` — drill into SEED
- `workspace` — drill into BASE
- `voice` — drill into the voice/draft/brand stack
- `security` — drill into Aegis
- `build` or `build-your-own` — drill into Skillsmith
- `rules` — drill into CARL
- `setup` — Day 1 activation path (2 steps to wake Caddy up)
- `try` — one personalized next command based on the customer's maturity tier

Unknown second word: print the full overview and append `(unrecognized area '<word>'; showed full overview instead)`.

## Canonical capability inventory

Single source of truth. The rest of the customer copy references the marketing string "140+ skills, commands, and tools across 7 systems."

| System | Type | Count | One-liner |
|---|---|---|---|
| Caddy plugin | Skills | 12 | Your daily operating layer. Draft, triage, prep, follow up, ship the day. |
| PAUL | Commands | 28 | Plan and execute real projects in structured phases. Built for non-coders. |
| SEED | Commands | 27 | Turn vague ideas into scoped, buildable projects before you commit time. |
| BASE | Commands | 26 | Your AI's memory, orientation, and operator profile. The thing that makes Caddy *yours*. |
| Skillsmith | Commands | 12 | Build your own custom AI skills for workflows nobody else has. |
| Aegis | Commands | 10 | Enterprise-grade security audits and remediation playbooks. |
| CARL | MCP tools | 30 | The rules engine. Domain rules, decision log, governance for how your AI behaves. |
| **Total** | | **145** | **Marketed as "140+" for headroom.** |

Note: 12 plugin skills includes `/caddy:capabilities` itself (this file). The customer count rises by one when this skill ships.

## Full overview output (default)

When `$ARGUMENTS` is empty, produce exactly this structure.

```
🏌️  Caddy: your unfair advantage

═══════════════════════════════════════════════════════════════
WHY THIS COSTS MORE THAN RAW CLAUDE
═══════════════════════════════════════════════════════════════
Claude is the engine. Caddy is the car.

Raw Claude or Claude Code gives you a powerful AI in a blank box.
Every conversation starts from zero. Every workflow is one you have
to invent and re-invent. The AI doesn't know who you are, how you
write, what your business does, or what you decided last Tuesday.

Caddy is the operating system that wraps that engine into a business.

  CLAUDE ALONE                 →    YOUR CADDY
  ───────────────────────────────────────────────────────────────
  Generic LLM voice            →    Writes in YOUR voice from a
                                    fingerprint you trained once
  Can't touch your inbox       →    /triage drafts every reply in
                                    your voice and your context
  Forgets every conversation   →    Remembers every commitment,
                                    decision, preference across
                                    sessions
  No daily ritual              →    /start-of-day chains brief +
                                    triage + meeting prep in one
                                    command
  No brand context             →    Knows your positioning,
                                    vocabulary, taboo phrases
  You invent every prompt      →    140+ pre-built skills, commands,
                                    and tools wired together
  No project framework         →    PAUL ships real software in
                                    phases with audit trails
  No security audit            →    Enterprise-grade security audit
                                    pipeline, the kind real
                                    consulting firms charge 5
                                    figures for

You're not paying for AI. Anthropic sells you that.
You're paying for the operating system that makes AI run your business.

═══════════════════════════════════════════════════════════════
THE 140+ PIECE PROOF
═══════════════════════════════════════════════════════════════
Seven interlocking systems. All yours. All local. One-time license.

▸ THE DAILY LAYER  (12 Caddy plugin skills)
   /draft  /triage  /prep  /followup  /start-of-day  /intake
   /verify  /graphify  /capabilities  /settings  /base-setup
   /carl-setup

▸ PLAN AND BUILD  (PAUL: 28 commands)
   The framework that lets a non-coder ship real software.
   /paul:init  /paul:plan  /paul:apply  /paul:verify  /paul:audit
   ...23 more for phases, milestones, research, handoffs

▸ IDEATE BEFORE YOU COMMIT  (SEED: 27 commands)
   Half-formed ideas in. Scoped buildable projects out.
   /seed:seed  /seed:tasks:ideate  /seed:tasks:graduate
   ...24 more for typed templates and planning quality

▸ YOUR AI'S MEMORY  (BASE: 26 commands)
   The reason your Caddy gets sharper every week.
   /base:pulse  /base:weekly  /base:groom  /base:orientation
   /base:audit ...21 more for surfaces, domains, history

▸ BUILD YOUR OWN  (Skillsmith: 12 commands)
   Your business has workflows nobody else does. Build skills for them.
   /skillsmith:skillsmith  /skillsmith:tasks:scaffold
   /skillsmith:tasks:audit  ...9 more

▸ SECURITY  (Aegis: 10 commands)
   /aegis:audit  /aegis:remediate  /aegis:playbook  /aegis:transform
   ...6 more for guardrails, reports, validation

▸ RULES ENGINE  (CARL: 30 MCP tools)
   carl_log_decision  carl_search_decisions  carl_create_domain
   carl_v2_replace_rules  ...26 more for proposals, hygiene, staging

═══════════════════════════════════════════════════════════════
THE COMPOUNDING MOAT
═══════════════════════════════════════════════════════════════
Every session adds to your memory.
Every decision sharpens your rules.
Every draft trains your voice.

Raw Claude is the same on Day 1 and Day 365.
Your Caddy on Day 365 is materially smarter than anyone else's,
because it has 365 days of YOUR work shaping how it answers.

This is the part competitors cannot copy.
The tech is buyable. The trained context is not.

═══════════════════════════════════════════════════════════════
[TIER_HEADER]
═══════════════════════════════════════════════════════════════
[TIER_BODY]

[NEXT_MOVE]

Type /caddy:capabilities <area> to drill in. Areas: vs-claude, planning,
ideation, workspace, voice, security, build, rules, setup, try.
```

## Tier-specific personalization

Replace `[TIER_HEADER]`, `[TIER_BODY]`, and `[NEXT_MOVE]` based on the maturity tier from pre-flight.

### Tier: Day 1

```
[TIER_HEADER]
YOUR FIRST SESSION

[TIER_BODY]
You've already invested real time installing Caddy. None of the
contrast above is live yet, but activating it is one more 30 to
60 minute investment and it's the highest-leverage time you'll
spend with Caddy. Without it, the rest stays generic.

  Step 1  /caddy:intake     Voice + brand interview (30-60 min)
                            Caddy learns how you write and what
                            your business is about. Writes
                            ~/.caddy/voice.md and ~/.caddy/brand.md
                            in one sitting.

  Step 2  /caddy:settings   Wire Gmail, Calendar, Drive connectors
                            (a couple minutes)

After those two, run /start-of-day every morning. That's when the
compounding starts.

[NEXT_MOVE]
► Run this next:  /caddy:intake

Until Caddy learns your voice and brand, /draft is still just an
LLM. The 30 to 60 minutes you spend on intake is the highest-
leverage time you'll ever spend with Caddy.
```

### Tier: Activated

```
[TIER_HEADER]
WHAT'S WIRED FOR YOU

[TIER_BODY]
[Voice line]
[Brand line]
[Connector line]

Each ✓ is a layer that makes Caddy uniquely yours.
Each ○ is a 5-to-60 minute unlock for more power.

[NEXT_MOVE]
► Run this next:  [next_command]
[next_reason]
```

For the three status lines, use:
- Voice ✓: `✓ Voice fingerprint loaded. /draft writes in your voice.`
- Voice ○: `○ Voice not loaded yet. /caddy:intake (30-60 min) unlocks /draft + voice-matched output across every skill.`
- Brand ✓: `✓ Brand context loaded. Caddy knows your positioning.`
- Brand ○: `○ Brand not loaded yet. /caddy:intake (30-60 min, same interview as voice) makes everything Caddy writes sound like *your* business.`
- Connector ✓: `✓ Anthropic connectors live. Gmail, Calendar, Drive integrated.`
- Connector ○: `○ Copy-paste mode. /caddy:settings set connector anthropic-connector unlocks /triage, /prep, /followup at full power.`

For `[next_command]` and `[next_reason]`, use the priority order from the `try` subcommand below.

### Tier: Compounding

```
[TIER_HEADER]
YOU'RE IN THE COMPOUND

[TIER_BODY]
Voice ✓  Brand ✓  Connectors ✓

Your Caddy is past Day 1 and into the part that matters: every week
it knows more about how you work, what you've decided, and how you
write. This is the moat.

[NEXT_MOVE]
► Run this next:  /base:weekly

The weekly ritual is what turns 30 days of memory into a Caddy that
anticipates you. Most customers skip this and wonder why their Caddy
plateaus. Don't be one of them.
```

## `vs-claude` subcommand

When `$ARGUMENTS` is `vs-claude` or `why`, output only the "WHY THIS COSTS MORE THAN RAW CLAUDE" section above, plus this closer:

```

Want to see the 140+ piece toolkit that makes this real?
Run /caddy:capabilities
```

## `setup` subcommand

When `$ARGUMENTS` is `setup`, output only the Day 1 Tier block above (regardless of actual maturity tier). For customers who want to re-run setup or share the activation path with a teammate.

## `try` subcommand

When `$ARGUMENTS` is `try`, skip everything and output:

```
Based on what's set up in your Caddy, try this next:

  [next_command]

[next_reason]

Want the full picture? Run /caddy:capabilities
```

Priority order for `[next_command]` and `[next_reason]`:

1. **No voice fingerprint** → `/caddy:intake` / "Voice is the biggest single unlock. Caddy without your voice is just a generic LLM with extra steps. Do this first."
2. **No brand context** (voice exists but brand doesn't, which is rare since intake produces both) → `/caddy:intake` / "Re-run intake to add the brand half. Brand context is what makes Caddy's output sound like *your* business, not a template."
3. **No connectors** → `/caddy:settings set connector anthropic-connector` / "Connectors unlock the daily-driver skills like /triage and /prep at full power."
4. **All present, voice.md under 500 bytes** → `/caddy:intake` / "Your intake looks shallow. A deeper voice fingerprint = sharper output everywhere. Re-run when you have 30 to 60 minutes."
5. **All present, voice.md healthy** → `/base:weekly` / "The weekly ritual is what compounds 30 days of memory into a Caddy that anticipates you."

## Drill-down outputs

When `$ARGUMENTS` names an area (planning, ideation, workspace, voice, security, build, rules), skip the full overview and produce a focused output:

1. One sentence about what life looks like once the customer has fluency in this area
2. Full command list with one-line descriptions
3. One or two example workflows that chain commands together
4. One personalized next move within this area

### Worked example: `voice` drill-down

This is the template Claude should follow when the customer types `/caddy:capabilities voice`. Use this exact structure (not the exact wording, but the same shape) for every drill-down.

```
🏌️  Caddy: the voice + drafting stack

Once Caddy knows your voice, everything it writes for you stops
sounding like AI. Emails sound like you wrote them at 6am. LinkedIn
posts land. Memos read like your memos. The customer never has to
clean up the output.

THE COMMANDS
  /caddy:intake     Voice + brand interview (30-60 min). Run once.
                    Produces ~/.caddy/voice.md and ~/.caddy/brand.md.
  /caddy:draft      Draft anything in your voice. Pass a topic.
                    Reads voice.md + brand.md every call.

EXAMPLE WORKFLOW: Daily LinkedIn post
  1. /caddy:draft "post about why most operators waste hours
     every week on inbox triage and what to do about it"
  2. Read the draft. If you want to revise: tell Caddy what to
     change. It re-drafts in your voice.
  3. Paste to LinkedIn.

EXAMPLE WORKFLOW: Cleaning up an AI-written draft
  1. Paste the generic AI draft into chat.
  2. Run /caddy:draft "rewrite this in my voice: <paste>"
  3. Caddy re-drafts using your voice fingerprint and brand
     context, killing the AI tells (generic openers, corporate
     hedging, em dashes) and replacing them with how YOU write.

YOUR NEXT MOVE
► [next_move based on tier and what's missing in voice/brand]
```

### Worked example: `planning` drill-down

```
🏌️  Caddy: PAUL, the planning and execution framework

Once you're fluent in PAUL, you stop wondering if your projects
will ship. You break work into phases, plan each phase, build,
verify, repeat. Every project leaves an audit trail. Non-coders
ship real software.

THE CORE COMMANDS
  /paul:init         Start a new project the right way
  /paul:plan         Break the next phase into executable steps
  /paul:apply        Build what was just planned
  /paul:verify       Manual acceptance test of new features
  /paul:audit        Enterprise-grade architectural review
  /paul:progress     Smart status, suggests one next action
  /paul:handoff      Generate a session handoff document
  /paul:resume       Restore context from handoff and continue
  ...20 more for milestones, research, phase management, fixes

EXAMPLE WORKFLOW: Shipping a small app
  1. /paul:init                  Set up the project structure
  2. /paul:discuss               Talk through the vision
  3. /paul:plan                  Break phase 1 into steps
  4. /paul:apply                 Build what was just planned
  5. /paul:verify                Manually test what shipped
  6. /paul:handoff               Save context for next session

EXAMPLE WORKFLOW: Returning to a project after a week away
  1. /paul:resume                Restore the context
  2. /paul:progress              See where you left off + one next move
  3. /paul:plan                  Plan the next phase

YOUR NEXT MOVE
► /paul:init in a new folder

PAUL pays for itself the first time you ship something you'd have
otherwise abandoned. Start with something small.
```

### Other drill-downs

For `ideation`, `workspace`, `security`, `build`, `rules`: follow the same template (intro sentence on what fluency looks like → core commands → one or two example workflows → next move). Claude generates these on demand using the same shape as the worked examples above. Do not invent commands that don't exist; if unsure, list only the commands Claude has direct visibility into from the customer's `~/.claude/commands/` directory.

## Hard rules

- **No em dashes anywhere.** Use commas, colons, periods, or parentheses.
- **Never quote a number that contradicts the canonical inventory.** The marketing string is "140+ skills, commands, and tools across 7 systems." Never say 11, 49, 130 in customer output unless it's a per-system count from the inventory table.
- **Never expose internal version numbers** (plugin v0.5.x, framework versions). Customer-facing version is "v1" only.
- **Never name competitors.** Differentiation lives in what Caddy uniquely does.
- **Never state the price.** The customer knows what they paid. Stating it reads transactional.
- **Never make time-saved or money-saved claims with specific numbers.** Vague is okay ("save you hours every week"); specific is a fact-check risk.
- **Day 1 framing is "your first session," not "you're missing things."** New customers should feel like they're at the start of something powerful, not behind.
- **Output is the response. No preamble, no "Here's what Caddy can do," no commentary.**
- **Address the customer as "you," never as "the user" or "the operator."**
- **The contrast section is non-negotiable.** It's the answer to the real question. Lead with it on the default overview. Never skip it to save space.

## Why this skill matters (do not output to customer)

Every customer asks the same two questions, and they both come out the front door of this skill: "Did I waste my money?" and "Remind me what I'm paying for." This skill must answer the first question in the first 30 seconds of output, every single time. The 140+ piece inventory is the proof, not the pitch. The pitch is the operating-system framing and the compounding moat. Get that order right and the customer becomes a long-term install instead of a refund request at day 14.

When the canonical inventory above changes (new framework, new plugin skill, deprecated command), update the table in this file first, then re-verify every customer-facing reference matches the marketing string "140+ skills, commands, and tools across 7 systems."

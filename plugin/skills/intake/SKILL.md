---
description: Voice + brand fingerprint capture for Caddy. Use when the user types /caddy:intake or asks Caddy to set up their voice fingerprint and brand context for the first time. Multi-turn interview (10 questions, asked one at a time); writes ~/.caddy/voice.md and ~/.caddy/brand.md. Local-only; no backend round-trip. The /caddy:draft skill consumes these two files on every call.
---

# Caddy: Intake

Capture the operator's voice fingerprint and brand context through a structured interview, then write `~/.caddy/voice.md` and `~/.caddy/brand.md` to disk. This skill is purely client-side: no MCP tool calls, no backend round-trip, no network access. Customer data stays on the customer's machine.

The two files produced by intake are consumed by `/caddy:draft` on every call (the skill reads them and passes their contents as MCP tool arguments to Caddy's backend). If the customer never runs intake, they can write voice.md and brand.md manually using the schemas documented below — intake is a convenience, not a requirement.

## Pre-flight (overwrite safety)

Before starting the interview, check whether `~/.caddy/voice.md` or `~/.caddy/brand.md` already exists. Use the Read tool to check; absence-of-file will surface as a read failure, which is fine.

If either file already exists, do NOT start the interview. Instead, surface this explicit prompt:

> I see you already have a voice.md (and/or brand.md) at `~/.caddy/`. Running intake will overwrite it. Proceed? (yes / no / back-up-first)

Wait for the customer's explicit answer. Three valid responses:

- **`no`** → Abort cleanly. Print: `Cancelled. No files written.` Do NOT proceed to the interview.
- **`back-up-first`** → Back up existing file(s) BEFORE starting the interview. Backup procedure below.
- **`yes`** → Proceed to interview. The existing file(s) will be overwritten at the end of the interview (after the customer's pre-write confirmation).

### Backup procedure (when `back-up-first` is chosen)

For each existing file, copy its contents to a timestamped backup using the Read tool followed by Write tool. The backup filename format is:

```
~/.caddy/voice.md.bak-{ISO-ms-timestamp}
~/.caddy/brand.md.bak-{ISO-ms-timestamp}
```

Where `{ISO-ms-timestamp}` is the current date and time at millisecond precision, with characters that are filename-safe (replace colons with hyphens). Example: `2026-05-11T04-23-15-432`.

If a backup filename collides (i.e., a file with that exact timestamp already exists, which is rare but possible on very rapid re-runs), append a discriminator: `-1`, `-2`, etc., until you find an unused name.

**Backup atomicity (load-bearing — do not skip):** If both `voice.md` and `brand.md` exist and the customer chose `back-up-first`, BOTH backups must succeed before the interview starts. The flow:

1. Read existing `~/.caddy/voice.md` content. Write it to the backup path.
2. If that Write fails (permission denied, disk full, etc.): print the error per the write-failure template below, abort the interview, no further action.
3. Read existing `~/.caddy/brand.md` content. Write it to the backup path.
4. If THAT Write fails: roll back the first backup. Use the Write tool to overwrite the voice.md backup file with empty content (one-line empty string), then surface the error: `could not back up brand.md: <reason>. I've rolled back the voice.md backup; your original files are unchanged. Try: chmod u+w ~/.caddy/ or check disk space, then re-run /caddy:intake.` Then abort the interview.

This prevents the "voice.md backed up, brand.md not backed up, customer proceeds, eventual overwrite leaves brand.md without a recovery path" inconsistent state.

After successful backup of both files (or only the one that exists), print a brief confirmation: `Backed up existing voice.md and brand.md to ~/.caddy/*.bak-{timestamp}. Starting interview.` Then proceed to the framing message.

## Framing message

Once pre-flight is clean (no existing files OR customer chose `yes`/`back-up-first` AND backups succeeded), greet the customer with this framing:

> I'm going to ask you a few questions about your voice and your brand. Takes about 5-10 minutes. At the end I'll write `~/.caddy/voice.md` and `~/.caddy/brand.md` to your machine, which the `/caddy:draft` skill uses to write in your voice.
>
> You can stop anytime — nothing gets written until we finish.
>
> Your answers stay LOCAL on your machine in those two files. They only leave your machine if you later run `/caddy:draft`, which sends voice + brand context to Caddy's backend and your Anthropic key for that one draft call. Nothing persisted on either side.
>
> If you'd rather not put specific client names, deal details, or other confidential third-party information into voice.md or brand.md, just describe yourself in generalities for those questions.
>
> First voice question:

Then immediately ask Q1. Do not list all the questions; ask them ONE AT A TIME.

## Voice interview (6 questions)

Ask each question and wait for the customer's answer before asking the next. Preserve the customer's verbatim phrasing in your internal working memory — their actual words are the source of truth for the fingerprint.

### Q1
> What do you do? (job, business, role — in your own words, not a LinkedIn headline)

### Q2
> Who do you write for most of the time? (audience: clients, peers, customers, network)

### Q3
> Pick a recent thing you wrote — an email, a LinkedIn post, a message to a friend — and tell me about a moment from your real work that captures who you are. Specific moments work better than abstractions.

### Q4
> Describe yourself at a backyard barbecue talking about what you do. Talk like you actually would, not how you'd write a bio.

### Q5
> What words or phrases do you NEVER want to use in your writing? Could be specific words you hate, or whole categories of style you avoid (corporate jargon, LinkedIn-thought-leader cadence, overly clinical language, anything else). Tell me what specifically grates on you when you read it — your list, not a generic one.

### Q6
> What's a line or story about your work that lands every time you tell it? The thing people remember after the conversation.

## Brand interview (4 questions)

Same one-at-a-time cadence as voice. Continue waiting for each answer before the next question.

### B1
> What does your business or work do, in one or two plain-spoken sentences? (Not the pitch — the actual thing.)

### B2
> Who is your audience? (Be specific: not 'business owners', but 'plumbers and HVAC techs who run their own shop'.)

### B3
> What's the one thing you do better or differently than everyone else in your space?

### B4
> What's the promise — explicit or implicit — that your audience hears when they engage with you?

## Synthesis

After all 10 questions are answered (or the customer says "that's enough" / signals stop), synthesize the answers into voice.md and brand.md following the schemas below.

Apply voice constraints to the OUTPUT itself:
- No em dashes anywhere
- No double dashes in prose
- No hype words: leverage, unlock, transform, supercharge, synergy, comprehensive, robust, seamless, revolutionize
- First-person voice ("I", not corporate "we")
- Specific moments over abstractions (preserve the customer's verbatim moments from Q3 and Q6)
- The customer's Q5 slop list is honored verbatim in the synthesized voice.md

### Word-count floor

Target: voice.md should be ≥600 words; brand.md should be ≥300 words.

If, after synthesizing, either file falls short:

1. **First time only:** prompt the customer once to expand: `Want to expand on anything? Your answers are pretty brief and the voice fingerprint works better with more material. Specifically Q{N} would benefit from more detail. Or it's fine to proceed — your call.`
2. **If still under floor after the one expand-prompt:** do NOT silently ship sub-minimum and do NOT refuse outright. Surface explicitly in the pre-write confirmation:

> Heads up: voice.md came in at N words (target 600+). The fingerprint will still work but draft quality may be more generic. You can re-run /caddy:intake later with longer answers if you want sharper voice. Proceed? (yes / cancel)

Same template for brand.md if it's under target 300 words. If both are under-target, list both in the heads-up.

Customer decides. On `cancel`: print `Cancelled. No files written.` and abort.

## Pre-write confirmation

Before writing, show the customer a brief summary of what's about to be saved:

> Ready to write voice.md (~N words) and brand.md (~M words) to ~/.caddy/. Proceed? (yes / preview-first / cancel)

- **`preview-first`** → Display the full content of both files inline so the customer can review. After display, ask the proceed question again.
- **`yes`** → Proceed to the write step.
- **`cancel`** → Print `Cancelled. No files written. Run /caddy:intake whenever you're ready.` and abort.

## Write step

Write `~/.caddy/voice.md` first via the Write tool. Then write `~/.caddy/brand.md`.

**Graceful write-failure handling:** Wrap each Write tool invocation in error handling. If either Write fails for any reason (permission denied, disk full, read-only filesystem, parent directory missing+uncreatable, ENAMETOOLONG, etc.):

- Catch the failure
- Print a customer-readable error following this template:
  > could not write to ~/.caddy/{filename}: <reason from the failure>. Try: chmod u+w ~/.caddy/ or check filesystem permissions/disk space. Your interview answers are captured in this conversation transcript; copy them out if you want to retry.
- Do NOT propagate the raw error or expose stack traces to the customer.
- If voice.md succeeded but brand.md failed: state which file succeeded and which didn't. Don't roll back voice.md (that's destructive and the customer would lose work). Just be explicit about partial state and offer the retry guidance.

On full success (both files written):

> Saved voice.md and brand.md to ~/.caddy/. Run `/caddy:draft <your prompt>` to test it: try `/caddy:draft Write a 2-sentence note to a client thanking them for a recent meeting.` to see your voice come through.

## Cancellation handling

At any point during the interview (during a question, between questions, mid-synthesis, mid-confirmation), if the customer signals they want to stop, honor it cleanly.

Cancellation signals to listen for:
- Text containing: `never mind`, `cancel`, `let's not`, `let's stop`, `not now`, `stop`, `bail`, `quit`
- Typed `/exit`
- Ctrl+C indication

On any of those:

> Cancelled. No files written. Run /caddy:intake whenever you're ready.

Do NOT prompt to confirm the cancellation. Trust the customer's signal. Do NOT write any files. Do NOT touch ~/.caddy/.

## voice.md schema

```markdown
# Voice Reference

**Purpose:** Caddy's voice fingerprint for {customer name or business, if shared}. /caddy:draft uses this as the benchmark for everything it writes.

## What makes this voice work (the rules)
{derived from Q4 + Q5 — a numbered list of 5-9 voice rules in the customer's own phrasing wherever possible. Example rules: "Plain-spoken cadence — contractions, sentence fragments where natural", "No setup-contrast-button-bow structure", "Specific moments beat abstractions every time", "Never use: {Q5 slop list verbatim}"}

## Benchmark answers
### What I do
{customer's verbatim Q1 answer, lightly cleaned but preserving phrasing}

### Who I write for
{verbatim Q2 answer}

### A moment from real work
{verbatim Q3 answer — this is keystone material}

### How I describe what I do at a barbecue
{verbatim Q4 answer}

### The line that always lands
{verbatim Q6 answer — also keystone material}

## Keystone proof points
{the 2-3 strongest specific stories or framings from Q3 + Q6, distilled into reusable lines that future drafts can echo. These are the lines /caddy:draft should be most likely to surface.}

## Voice traps to avoid (slop list)
{Q5 answer verbatim, plus universal slop: no em dashes, no double dashes, no hype words (leverage, unlock, transform, supercharge, synergy, comprehensive, robust, seamless, revolutionize), no corporate "we" if customer is solo, no LinkedIn thought-leader cadence}
```

**File location:** `~/.caddy/voice.md`
**Minimum content:** ~600 words substantive (under-floor handling above).
**Voice rules in the file itself:** no em dashes, no double dashes, no hype words, first-person.

## brand.md schema

```markdown
# Brand Context

**Purpose:** Caddy's brand context for {customer business name}. /caddy:draft uses this to keep messaging on-brand and audience-appropriate.

## What this is
{derived from B1 — one-paragraph description of what the customer's work/business does, in their own words from B1}

## Audience
{from B2 — specific audience description; preserve the customer's verbatim specificity}

## What we do differently
{from B3 — the customer's stated differentiator, preserved verbatim where crisp}

## The promise
{from B4 — explicit or implicit promise the audience hears}

## Voice samples (good)
{2-3 do-examples drawn from the customer's actual answers + Q3 moment + Q6 keystone line}

## Voice samples (bad)
{2-3 don't-examples derived from Q5 slop list. Phrased as "❌ {bad example}" with a one-line explanation of why it's wrong.}

## Hard rules
- No em dashes
- No double dashes in prose
- {customer's Q5 verbatim entries listed as hard rules}
- First-person (if customer is solo); otherwise "we" if the business is multi-person and the customer's verbatim answers used "we"
- {any additional voice constraints surfaced during interview}
```

**File location:** `~/.caddy/brand.md`
**Minimum content:** ~300 words substantive (under-floor handling above).

## Customer-facing notes

These are surfaced to the customer when relevant (in the framing or in support conversations); they're documented here so any operator or support engineer can reference them.

### Non-determinism
Running `/caddy:intake` twice with identical answers will produce DIFFERENT voice.md and brand.md output. Claude's synthesis is stochastic by nature. This is expected behavior, not a bug. If a customer wants consistent voice.md across re-runs, they should paste the SAME answers verbatim AND use the back-up-first option to preserve the original — then compare manually and choose which to keep.

### Backup accumulation
If a customer re-runs `/caddy:intake` with `back-up-first` multiple times, they'll accumulate multiple `~/.caddy/voice.md.bak-{timestamp}` and `~/.caddy/brand.md.bak-{timestamp}` files. Caddy does NOT auto-clean these. The customer should delete old `.bak-*` files manually when they're confident in the current voice.md. Pattern for cleanup: `rm ~/.caddy/*.bak-*` (or selectively delete by timestamp).

### No mid-session resume
If a customer's Claude Code session crashes mid-interview, their answers are NOT preserved. The customer will need to restart `/caddy:intake` and re-answer from Q1. The conversation transcript in the customer's terminal scrollback may have their previous answers — they can copy them to a notes app if they want to paste them back in faster on the retry.

## Hard rules

- **No MCP tool calls.** This skill never invokes `plugin:caddy:caddy` or any other backend tool. Pure local-file work.
- **No Bash invocations.** Use Read and Write tools only. The backup-rollback path uses Write with empty content to delete partial backups; do NOT shell out to `rm`.
- **No writes outside `~/.caddy/`.** The skill operates exclusively on `~/.caddy/voice.md`, `~/.caddy/brand.md`, and their `.bak-*` siblings. Never touch any other path.
- **Never expose stack traces or raw tool errors to the customer.** All failure paths produce customer-readable error strings per the templates above.
- **Never log the customer's answers, voice.md content, or brand.md content to any persistent location.** Conversation transcripts are the customer's session only.
- **Never paraphrase verbatim moments.** Q3 and Q6 in particular preserve the customer's actual phrasing. AI-paraphrased "specific moments" lose the signal that makes voice fingerprinting work.

## Pattern notes for Phase 7

This SKILL.md is the reference for the **conversational-skill pattern** in the Caddy plugin. Phase 7's remaining anchor skills (`/caddy:triage`, `/caddy:start-of-day`, `/caddy:prep`, `/caddy:followup`) will likely follow this pattern. The structural elements that make the pattern work:

1. **Pre-flight check** for existing state that could be destroyed
2. **Framing message** setting expectations + privacy disclosure
3. **Multi-turn interview** with questions asked ONE AT A TIME (never batched)
4. **Synthesis step** that preserves verbatim customer language where it carries signal
5. **Pre-write confirmation** with `yes / preview-first / cancel` options
6. **Write step** with graceful error handling and partial-state honesty
7. **Cancellation handling** at any point in the flow

Plan 6-03's `/caddy:settings` is the reference for the **discrete-subcommand pattern**: parse args → validate → write. Discrete-subcommand suits commands where the customer knows exactly what they want (set this value, show that config). Conversational suits commands where Claude needs to elicit input that the customer hasn't pre-formed.

When writing a new Phase 7 anchor skill, pick the pattern that fits the skill's interaction model:
- `/caddy:triage` (review inbox + categorize + draft replies) → conversational
- `/caddy:start-of-day` (daily brief + priorities) → conversational
- `/caddy:prep` (meeting prep briefing) → conversational
- `/caddy:followup` (post-meeting recap + action items) → conversational
- All Phase 7 anchors that write to `~/.caddy/` should adopt this skill's overwrite-safety + graceful-write-failure handling verbatim.

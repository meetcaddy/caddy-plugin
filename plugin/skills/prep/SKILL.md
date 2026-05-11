---
name: caddy:prep
description: Use when the user types /caddy:prep or asks Caddy to help them prepare for a specific meeting. Read-then-write meeting prep brief; reads voice.md + brand.md + relevant triage entries + (optionally) calendar/inbox via configured connector; writes ~/.caddy/briefs/prep-YYYY-MM-DD-{slug}.md. Local-only; no backend round-trip.
---

# /caddy:prep

A read-then-write meeting prep brief skill. Customer invokes the command before a meeting, supplies meeting context (who, when, what, goal). You read their existing local Caddy context (voice + brand + relevant triage), optionally pull or ask for calendar / inbox context per connector mode, then synthesize a prep brief and write it to `~/.caddy/briefs/prep-YYYY-MM-DD-{slug}.md`.

This skill is **local-only**. No MCP tool calls. No backend round-trip. No network from Caddy's side. Use Read + Write tools only.

Second iteration of the read-then-write pattern (after `/caddy:start-of-day` in Plan 7-03). Two domain-specific changes vs Plan 7-03: (a) slug-based filename so multiple meetings on the same day never conflict, (b) customer-supplied meeting context up-front seeds the read step's triage-entry filtering.

---

## Session-start setup

When the customer invokes `/caddy:prep`:

1. **Compute today's date in the customer's local timezone, ONCE, at session start.** Use the current `Date()` evaluated in the Claude Code process. Format as `YYYY-MM-DD`. This is the SESSION-START date and is the date portion of the filename for this entire session, even if the conversation crosses midnight. Do NOT re-evaluate at write-time.

2. **Move to the framing message + meeting context capture step.** The slug locks later, after the customer confirms the meeting label.

---

## Framing message + meeting context capture

Greet the customer with this framing (paraphrase fine, preserve the disclosures):

> Let's prep for your meeting. Tell me about it: who's it with, when (today / tomorrow / a specific day), what's the topic in 3-5 words, and what would a great outcome look like? I'll read your existing Caddy context (voice + brand + today's triage), then either pull calendar + email context via your connector or ask you to paste it, depending on your settings.
>
> Your pasted contents stay LOCAL in this conversation. They are not sent to any backend.
>
> **What lands in the prep brief on disk:** only the synthesized talking points + open questions + suggested first move, plus the SHORT IDENTIFIERS you supply for related items. Pasted email bodies, meeting notes, and third-party message content NEVER end up in the file. If you'd rather not paste any private info, describe items in generalities.
>
> Today's date in your timezone is YYYY-MM-DD. The brief will be saved under that date even if our session crosses midnight.

Wait for the customer's response. If they paraphrase rather than answering each question, parse what you can. Ask ONE clarifying question only if essential context is missing (e.g., no meeting label at all). Otherwise proceed with what they gave.

---

## Slug derivation + filename anchor (AC-2)

From the customer-supplied meeting label, derive a slug:

- 3 to 5 words from the meeting label
- Lowercase
- Hyphen-separated
- ASCII characters only (strip diacritics, punctuation, special characters)

Example mappings:
- "intro call with Bob at Acme" -> `bob-acme-intro`
- "Q4 budget review with finance team" -> `q4-budget-finance`
- "follow-up with Junior about the install" -> `junior-install-followup`

Propose to the customer:

```
I'll save this as prep-YYYY-MM-DD-<slug>.md. Sound right? (yes / change to: <alternative>)
```

- On **yes**: lock the slug + filename.
- On **change to:**: use the customer's slug verbatim, sanitized (lowercase + hyphenate + ASCII only).
- On **cancel** or non-response: abort cleanly with the cancellation message.

The slug locks at this step. Do NOT re-derive at write-time. If the customer wants a different slug for the same meeting later, they cancel and re-run.

Compute the target filename: `~/.caddy/briefs/prep-{session-start-date}-{slug}.md`.

---

## Pre-flight (same-day overwrite check for THIS slug+date; AC-7)

Use the Read tool to check whether the target file already exists.

**If absent:** proceed to the read step.

**If present (customer already ran /caddy:prep for THIS meeting earlier today):** three-option warning:

```
I see you already prepped for this meeting today (file exists at ~/.caddy/briefs/prep-YYYY-MM-DD-<slug>.md).

What would you like to do?

(1) append: I'll add new entries under the same section headers.
(2) overwrite: I'll replace this prep with the new session's output.
(3) save-as-new: I'll write a fresh file at prep-YYYY-MM-DD-<slug>-HH-MM-SS-mmm.md alongside the existing one.

Or say cancel to stop.
```

- On **append** or **overwrite**: trigger the BACKUP INVARIANT below before any modification.
- On **save-as-new**: timestamp-suffix filename; no backup required (target fresh).
- On **cancel**: abort cleanly.

**BACKUP INVARIANT for destructive paths (append + overwrite):** Before making ANY modification to the existing file, write a verbatim backup at `~/.caddy/briefs/prep-{date}-{slug}.md.bak-{ISO-ms-timestamp}` using Read + Write. If the backup write fails (permission denied, disk full, parent directory uncreatable), abort with the AC-9 graceful-failure error template referencing the backup attempt; do NOT touch the original.

**Different-slug same-day runs are zero-conflict** (different filenames). Different meetings on the same day never collide.

---

## Read step (with degradation; AC-3)

Attempt to Read each input via the Read tool. Track present/missing for the metadata footer.

1. **Voice fingerprint:** `~/.caddy/voice.md`. If absent or unreadable, mark missing; surface "Heads up: I couldn't find voice.md (run /caddy:intake to create it). I'll continue, but the brief will be less voice-fingerprinted."

2. **Brand context:** `~/.caddy/brand.md`. Same handling.

3. **Today's triage:** `~/.caddy/triage/triage-{session-start-date}.md`. If today's absent, attempt the most recent triage file in `~/.caddy/triage/` (by filename date). If none exists, mark missing.

**Empty-context edge case:** If all three are missing, ask: "I have no Caddy context for you yet. Do you want to run /caddy:intake first, or proceed with an empty-context prep based on what you tell me right now? (intake / proceed / cancel)". Same shape as Plan 7-03.

---

## Triage-entry filtering for the meeting (AC-4 — NEW vs Plan 7-03)

If today's triage file exists (or the most recent fallback), scan the `## Today (urgent + actionable)` and `## This week` sections.

For each entry, attempt a fuzzy case-insensitive match against the customer's meeting label words (the matching seed). Treat the meeting label as a bag of words; an entry matches if it contains any of those words as substrings.

**If matches found:** Present a candidate list and let the customer adjust:

```
I see these triage items might relate to your meeting:
- <identifier 1>
- <identifier 2>
- <identifier 3>

Want me to include any others? Any I should drop? (or say "looks good")
```

**If no obvious matches:** Default to including all today's tier-Today + this-week entries, with a heads-up:

```
I didn't find triage entries that obviously match this meeting. I'll include today's and this-week's items as broader context. Adjust if needed.
```

Customer can add specific identifiers or drop any from the list. Lock the filtered list.

---

## Connector-mode handling (AC-5)

Read `~/.caddy/config.json` for the `connector` setting. Branch:

**connector = anthropic-connector:** Instruct yourself to use Claude Code's native connector access to pull the meeting's calendar entry + any related inbox threads. If actual connector access isn't available in this session:

```
I can't reach your connectors from this session. Want to paste meeting-relevant calendar + email context instead? (paste / skip)
```

Fall back to copy-paste or skip.

**connector = copy-paste:** Ask the customer to paste meeting-relevant calendar info + emails or describe in generalities. Same customer-supplied-identifier-only privacy rule (Plan 7-02 carry-forward): identify each item by a short label; pasted body content stays in conversation only.

**connector unset:**

```
I don't see a connector mode configured. Should I try your Anthropic-hosted connectors (you'd run `/caddy:settings set connector anthropic-connector` first), or use copy-paste mode for today? (anthropic / copy-paste / skip)
```

Track which connector mode was used (or skipped) for the metadata footer.

---

## Synthesis (AC-6)

Assemble the prep brief with these six sections in fixed order:

### 1. `# Prep, YYYY-MM-DD, <slug>`
Header line with session-start date + slug.

### 2. `## Meeting`
Two to four short lines covering: who's it with, when, what (the meeting label / topic), customer's stated goal. Use the customer's verbatim wording where possible.

### 3. `## Context`
Two to four lines summarizing the relevant triage entries + any pertinent voice / brand cues. Use customer-supplied identifiers from triage entries. Do NOT paraphrase from any pasted email or meeting-note body content.

### 4. `## Talking points`
3 to 5 anchored points. ONE line each. Specific over abstract. Voice-tuned: no hype words, no em dashes, no double dashes. Drawn from triage entries + customer's stated goal + voice + brand cues.

### 5. `## Open questions`
2 to 4 questions to ask or things to surface. Things the customer should learn or clarify in the meeting. Customer-supplied identifiers only.

### 6. `## Suggested first move`
ONE to TWO sentences. Claude's pick of how to open the conversation. Action-oriented (named verb, specific). Voice-tuned.

### 7. Metadata footer
`*Generated by /caddy:prep at HH:MM. Inputs: voice.md present/missing, brand.md present/missing, triage-YYYY-MM-DD.md present/missing, connector mode: anthropic-connector|copy-paste|skipped. Slug: <slug>.*`

**Privacy enforcement (MH-2 carry-forward):** The brief NEVER includes pasted body content. Triage-entry references use the customer-supplied identifiers verbatim. Talking points + open questions + suggested first move are synthesis (Claude's words, voice-tuned), not paraphrases of any pasted email or calendar body.

**ASCII rule:** ASCII characters only in the written file. No em dashes. No double dashes. No unicode arrows (use `->`).

**Minimum content rule:** If after all reads + filtering + connector handling there is genuinely nothing to put in the brief (no inputs, customer skipped connector, declined to paste, no meeting label), do NOT write an empty file. Respond:

```
There's not enough to prep on yet. Want to run /caddy:intake first, or share more meeting context? No file written.
```

---

## Pre-write confirmation (AC-8)

Show a short preview:

```
Ready to write prep-YYYY-MM-DD-<slug>.md (~N words; X talking points, Y open questions, suggested first move present). Proceed? (yes / preview-first / cancel)
```

- On **yes**: proceed to the write step.
- On **preview-first**: display the full file content inline. Then re-prompt.
- On **cancel**: abort. No file written. No backup taken (the destructive write was never initiated).

Latest-possible cancellation point. Customers can change their mind even after synthesis is complete.

---

## Write step (AC-9 graceful failure + MH-1 backup invariant)

**For SAVE-AS-NEW path:**
- Write directly to `~/.caddy/briefs/prep-{session-start-date}-{slug}-{HH-MM-SS-mmm}.md` using the Write tool.
- The Write tool creates the missing parent directory as part of the write.
- No backup required.

**For APPEND path:**
1. Write the backup first: `~/.caddy/briefs/prep-{date}-{slug}.md.bak-{ISO-ms-timestamp}`, content = verbatim Read of the current on-disk file.
2. If backup fails, abort with AC-9 error template. Do NOT modify the original.
3. Read the existing file content.
4. Parse for the six section headers. If any missing or malformed, fall back to save-as-new with a brief note to the customer.
5. Merge: preserve existing sub-content under each header; append new entries below. Re-write metadata footer.
6. Write the merged content.

**For OVERWRITE path:**
1. Write the backup first (same as append step 1).
2. If backup fails, abort with AC-9 error template.
3. Write the new content, replacing existing.

**Graceful failure (AC-9):** If any Write fails (permission denied, disk full, mount read-only), respond:

```
could not write to ~/.caddy/briefs/<filename>: <reason>. Try: chmod u+w ~/.caddy/ or check filesystem permissions/disk space. Your prep content is captured in this conversation transcript; copy it out if you want to retry.
```

Do NOT propagate raw errors. Do NOT expose stack traces.

---

## Cancellation handling (AC-8)

At any point during the flow, if the customer signals stop ("never mind", "cancel", "stop", "not now", "/exit", or similar), acknowledge with:

```
Cancelled. No files written. Run /caddy:prep whenever you're ready.
```

Do NOT write. On APPEND path: do NOT modify the existing file. On OVERWRITE path: do NOT touch the existing file. Preview-stage cancellation is also covered: no backup is taken if the destructive write was never initiated.

Do NOT prompt the customer to confirm cancellation. Trust the signal.

---

## Prep brief schema (AC documentation)

```markdown
# Prep, 2026-05-11, bob-acme-intro

## Meeting
Intro call with Bob from Acme. Tomorrow at 10am. Topic: Q4 budget renewal. Goal: get them excited about v3 features.

## Context
- Acme renewal -> in this-week tier from today's triage
- Voice: direct, specific moments over abstractions
- Brand: emphasize unfair-advantage framing for renewal pitch

## Talking points
- Open with the sixty-grand keystone story.
- Anchor on the one v3 feature they specifically asked about.
- Quantify what they get back from renewing now versus waiting.
- Surface our deployment timeline; preempt the "is this ready" question.

## Open questions
- What's their internal decision deadline?
- Who else needs to sign off?
- Any budget shifts since our last conversation?

## Suggested first move
Lead with the sixty-grand keystone proof point and pivot directly to the v3 feature they asked about. Don't open with pleasantries; their last email signaled time pressure.

*Generated by /caddy:prep at 09:15. Inputs: voice.md present, brand.md present, triage-2026-05-11.md present, connector mode: copy-paste. Slug: bob-acme-intro.*
```

**Schema rules:**
- File location pattern: `~/.caddy/briefs/prep-YYYY-MM-DD-<slug>.md` (or `prep-YYYY-MM-DD-<slug>-HH-MM-SS-mmm.md` for save-as-new).
- Header line: `# Prep, YYYY-MM-DD, <slug>` with session-start date + locked slug.
- Six fixed sections in this order: Meeting, Context, Talking points, Open questions, Suggested first move, metadata footer.
- Bullet items use ASCII `->` arrow.
- Metadata footer: `*Generated by /caddy:prep at HH:MM. Inputs: ... connector mode: ... . Slug: <slug>.*`
- No em dashes, no double dashes, no hype words anywhere in the body.

---

## Pattern notes for Phase 7

This skill is the SECOND iteration of the read-then-write pattern in Phase 7. Plan 7-03 (`/caddy:start-of-day`) was the first; Plan 7-04 (`/caddy:prep`) is the second; Plan 7-05 (`/caddy:followup`) is the expected third and final iteration in v1.0.

**What carried forward intact from Plan 7-03:**
- Session-start setup with date lock + local timezone
- Three-option same-day overwrite UX with destructive-path backup invariant
- Read step with per-input degradation + empty-context edge case
- Connector-mode dispatch (anthropic-connector / copy-paste / unset) with graceful in-session fallback
- Customer-supplied-identifier-only privacy contract
- Preview-stage cancellation
- Graceful write failure template
- Customer-facing notes (non-determinism, no-resume, sensitive content stays local, backup accumulation, date+tz, connector caveat, missing inputs are OK)

**Two domain-specific changes vs Plan 7-03:**

1. **Slug-based filename.** `prep-YYYY-MM-DD-<slug>.md` instead of `start-of-day-YYYY-MM-DD.md`. Allows multiple meetings on the same day to coexist with zero conflict. Same-day re-runs for the SAME slug+date trigger the three-option UX; different slugs same day are zero-conflict.

2. **Customer-supplied meeting context up-front.** The customer supplies the meeting label + goal at the start of the flow. That label becomes the matching seed for triage-entry filtering (a new step vs Plan 7-03's day-wide aggregation).

**For Plan 7-05 (`/caddy:followup`):** the expected shape is the same read-then-write pattern with these domain-specific changes:
- File slug from the meeting that just happened (likely the same slug pattern as `/caddy:prep`)
- Customer supplies meeting outcomes + action items (post-meeting state, not pre-meeting goal)
- Output adds a section proposing updates to `~/.caddy/triage/triage-YYYY-MM-DD.md` (whether to actually write to the triage file is a design decision for Plan 7-05; could go either way: write through, or just suggest and let the customer add manually)
- Likely 5-6 sections: Meeting, Outcomes, Action items, Open threads, (optional) Triage suggestions, Suggested follow-up message

For skills that don't fit the read-then-write or interactive-conversation-loop patterns, see Plan 6-03's `/caddy:settings` for the discrete-subcommand pattern.

---

## Customer-facing notes

**Non-determinism.** Running /caddy:prep twice on the same meeting context produces DIFFERENT brief text. The triage-entry references and meeting-label fields are stable; the synthesis (talking points, open questions, suggested first move) varies. This is normal.

**No mid-session resume.** If your Claude Code session crashes mid-flow, your context (especially any pasted calendar or email content) is NOT preserved. Restart /caddy:prep.

**Sensitive content stays local in the conversation.** Pasted calendar entries, email content, and meeting notes stay in this conversation only. The brief file written to disk contains: synthesized talking points + open questions + suggested first move, plus customer-supplied identifiers for related triage items, plus the meeting label you typed in. Pasted message body content NEVER ends up in the file.

**Backup accumulation.** If you use APPEND or OVERWRITE on a same-slug+same-day re-run, /caddy:prep creates a backup at `~/.caddy/briefs/prep-YYYY-MM-DD-<slug>.md.bak-{timestamp}`. Backups accumulate; Caddy does not auto-clean them. Delete old `.bak-*` files manually when you're confident in the current brief. Save-as-new does not create backups.

**Date and timezone.** The brief file is named with today's date in your local timezone. Session-start date locks the filename even if the session crosses midnight.

**Slug stability.** Your slug locks at the start of a session. If you run /caddy:prep twice for the same meeting (same slug + same date), you'll hit the append / overwrite / save-as-new prompt. Different meetings on the same day get different slugs and never conflict. If you want a different slug for the same meeting, cancel and re-run.

**Connector-mode caveat.** If you set connector=anthropic-connector but Claude Code doesn't have actual connector access in your session, /caddy:prep falls back to copy-paste mode and asks you to paste. Run `/caddy:settings show` to confirm your config.

**Missing inputs are OK.** /caddy:prep degrades gracefully. If you haven't run /caddy:intake yet, the brief skips voice-fingerprinting. If you haven't run /caddy:triage today, the brief skips the Context section (or uses the most recent triage file as fallback). The skill still produces a useful brief from whatever's available.

---

## Hard rules

- This skill NEVER invokes `plugin:caddy:caddy` or any other backend tool. Pure local-file.
- This skill NEVER uses Bash. Read and Write tools only.
- This skill NEVER writes outside `~/.caddy/briefs/`.
- This skill NEVER includes pasted body content in the written brief file. Customer-supplied identifiers + Claude-synthesized content are the only sources.
- This skill NEVER skips the backup write on APPEND or OVERWRITE paths.
- This skill NEVER uses em dashes or double dashes in the written brief file.
- This skill NEVER calls Caddy's backend MCP server. Connector access is Claude Code's native capability when configured.
- This skill NEVER re-derives the slug at write-time. The slug locks at session-start once the customer confirms it.

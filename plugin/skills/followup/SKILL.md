---
name: caddy:followup
description: Use when the user types /caddy:followup or asks Caddy to help them write up the recap of a meeting that just happened. Read-then-write post-meeting recap; reads voice.md + brand.md + matching prep file if it exists + relevant triage entries + (optionally) calendar/inbox via configured connector; writes ~/.caddy/briefs/followup-YYYY-MM-DD-{slug}.md. Local-only; no backend round-trip.
---

# /caddy:followup

A read-then-write post-meeting recap skill. Customer invokes the command after a meeting, supplies what happened (outcomes, decisions, action items). You read their existing local Caddy context (voice + brand + the matching prep file for the same slug+date if it exists + relevant triage), optionally pull or ask for any post-meeting calendar / inbox context per connector mode, then synthesize a recap brief and write it to `~/.caddy/briefs/followup-YYYY-MM-DD-{slug}.md`.

This skill is **local-only**. No MCP tool calls. No backend round-trip. No network from Caddy's side. Use Read + Write tools only.

Third iteration of the read-then-write pattern (after `/caddy:start-of-day` in Plan 7-03 and `/caddy:prep` in Plan 7-04), and the LAST anchor skill in Phase 7. Two domain-specific changes vs Plan 7-04:

1. **Cross-skill artifact linking.** Read the matching prep file at `~/.caddy/briefs/prep-{date}-{slug}.md` if it exists. The customer's pre-meeting prep becomes additional context for the post-meeting recap. Graceful degradation if the prep file is absent (different slug, or customer didn't prep).
2. **Post-meeting state replaces pre-meeting state.** The customer supplies outcomes + decisions + action items (what happened) instead of goal + talking points (what to do). The brief is a recap, not a plan.

---

## Session-start setup

When the customer invokes `/caddy:followup`:

1. **Compute today's date in the customer's local timezone, ONCE, at session start.** Use the current `Date()` evaluated in the Claude Code process. Format as `YYYY-MM-DD`. This is the SESSION-START date and is the date portion of the filename for this entire session, even if the conversation crosses midnight. Do NOT re-evaluate at write-time.

2. **Move to the framing message + meeting context capture step.** The slug locks later, after the customer confirms the meeting label.

---

## Framing message + meeting context capture

Greet the customer with this framing (paraphrase fine, preserve the disclosures):

> Let's write up the recap. Tell me about the meeting: who was it with, when did it happen (today / yesterday / a specific day), what was the topic in 3-5 words, and what happened (outcomes, decisions made, action items mentioned)? I'll read your existing Caddy context (voice + brand + today's triage), and if you ran /caddy:prep for this meeting earlier I'll pick up your prep file too. Then either pull post-meeting context via your connector or ask you to paste it, depending on your settings.
>
> Your pasted contents stay LOCAL in this conversation. They are not sent to any backend.
>
> **What lands in the followup brief on disk:** only the synthesized recap + decisions + action items + open threads + triage suggestions + suggested follow-up message, plus the SHORT IDENTIFIERS you supply for related items. Pasted email bodies, meeting notes, and third-party message content NEVER end up in the file. If you'd rather not paste any private info, describe items in generalities.
>
> Today's date in your timezone is YYYY-MM-DD. The brief will be saved under that date even if our session crosses midnight.

Wait for the customer's response. If they paraphrase rather than answering each question, parse what you can. Ask ONE clarifying question only if essential context is missing (e.g., no meeting label at all, or no outcomes at all). Otherwise proceed with what they gave.

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
I'll save this as followup-YYYY-MM-DD-<slug>.md. Sound right? (yes / change to: <alternative>)
```

- On **yes**: lock the slug + filename.
- On **change to:**: use the customer's slug verbatim, sanitized (lowercase + hyphenate + ASCII only).
- On **cancel** or non-response: abort cleanly with the cancellation message.

**Slug match with /caddy:prep:** If the customer prepped for this meeting earlier today (or on the meeting's date) using /caddy:prep, they should pick the SAME slug here so cross-skill linking can find the prep file. Mention this once in the slug prompt if it seems relevant:

```
Tip: if you prepped this meeting with /caddy:prep, use the same slug and date so I can pick up that prep file as context.
```

The slug locks at this step. Do NOT re-derive at write-time.

Compute the target filename: `~/.caddy/briefs/followup-{session-start-date}-{slug}.md`.

---

## Pre-flight (same-day overwrite check for THIS slug+date; AC-9)

Use the Read tool to check whether the target file already exists.

**If absent:** proceed to the read step.

**If present (customer already ran /caddy:followup for THIS meeting earlier today):** three-option warning:

```
I see you already wrote up a recap for this meeting today (file exists at ~/.caddy/briefs/followup-YYYY-MM-DD-<slug>.md).

What would you like to do?

(1) append: I'll add new entries under the same section headers.
(2) overwrite: I'll replace this recap with the new session's output.
(3) save-as-new: I'll write a fresh file at followup-YYYY-MM-DD-<slug>-HH-MM-SS-mmm.md alongside the existing one.

Or say cancel to stop.
```

- On **append** or **overwrite**: trigger the BACKUP INVARIANT below before any modification.
- On **save-as-new**: timestamp-suffix filename; no backup required (target fresh).
- On **cancel**: abort cleanly.

**BACKUP INVARIANT for destructive paths (append + overwrite):** Before making ANY modification to the existing file, write a verbatim backup at `~/.caddy/briefs/followup-{date}-{slug}.md.bak-{ISO-ms-timestamp}` using Read + Write. If the backup write fails (permission denied, disk full, parent directory uncreatable), abort with the AC-10 graceful-failure error template referencing the backup attempt; do NOT touch the original.

**Different-slug same-day runs are zero-conflict** (different filenames). Different meetings on the same day never collide.

---

## Read step (with degradation; AC-4)

Attempt to Read each input via the Read tool. Track present/missing for the metadata footer.

1. **Voice fingerprint:** `~/.caddy/voice.md`. If absent or unreadable, mark missing; surface "Heads up: I couldn't find voice.md (run /caddy:intake to create it). I'll continue, but the recap will be less voice-fingerprinted."

2. **Brand context:** `~/.caddy/brand.md`. Same handling.

3. **Today's triage:** `~/.caddy/triage/triage-{session-start-date}.md`. If today's absent, attempt the most recent triage file in `~/.caddy/triage/` (by filename date). If none exists, mark missing.

4. **Matching prep file (cross-skill artifact linking; AC-3, NEW for 7-05):** `~/.caddy/briefs/prep-{session-start-date}-{slug}.md`. Use the locked slug from the prior step and the session-start date.
   - **If present:** surface "I found your prep file for this meeting at ~/.caddy/briefs/prep-{date}-{slug}.md. I'll use it as context, and the recap will include a `## Pre-meeting prep` section comparing your intended angle to what actually happened."
   - **If absent:** surface "I didn't find a prep file for this slug+date (you may not have prepped, or you used a different slug). That's fine, the followup will skip the pre-meeting-prep section."

**Empty-context edge case:** If voice + brand + triage AND the matching prep file are all missing, ask:

```
I have no Caddy context for you yet, and no matching prep file for this meeting. Do you want to run /caddy:intake first, or proceed with an empty-context followup based on what you tell me right now? (intake / proceed / cancel)
```

Same shape as Plans 7-03 + 7-04, extended to include the prep-file dimension.

---

## Triage-entry filtering for the meeting (AC-5, carry-forward from Plan 7-04)

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

## Connector-mode handling (AC-6)

Read `~/.caddy/config.json` for the `connector` setting. Branch:

**connector = anthropic-connector:** Instruct yourself to use Claude Code's native connector access to pull any post-meeting follow-up emails, calendar updates, or related threads. Note: post-meeting connector data is typically thinner than pre-meeting (the meeting just happened); the customer's verbal recap is the primary source. If actual connector access isn't available in this session:

```
I can't reach your connectors from this session. Want to paste any post-meeting context (emails received after the meeting, follow-up threads) instead? (paste / skip)
```

Fall back to copy-paste or skip.

**connector = copy-paste:** Ask the customer to paste any post-meeting context (follow-up emails, message threads), or describe in generalities. Same customer-supplied-identifier-only privacy rule (Plan 7-02 carry-forward): identify each item by a short label; pasted body content stays in conversation only.

**connector unset:**

```
I don't see a connector mode configured. Should I try your Anthropic-hosted connectors (you'd run `/caddy:settings set connector anthropic-connector` first), or use copy-paste mode for today? (anthropic / copy-paste / skip)
```

Track which connector mode was used (or skipped) for the metadata footer.

---

## Synthesis (AC-7 + AC-8)

Assemble the followup brief with these eight sections in fixed order. The `## Pre-meeting prep` section is CONDITIONAL on the matching prep file being present.

### 1. `# Followup, YYYY-MM-DD, <slug>`
Header line with session-start date + slug.

### 2. `## Meeting`
Two to four short lines covering: who it was with, when, what (the meeting label / topic). Use the customer's verbatim wording where possible.

### 3. `## Pre-meeting prep` (CONDITIONAL)
**If the matching prep file was read:** Quote the prep file's `## Suggested first move` line and 1-2 key `## Talking points` here. Open the section with `From your prep brief (~/.caddy/briefs/prep-{date}-{slug}.md):` for attribution. The point is comparison: what you planned versus what actually happened.

**If the matching prep file is absent:** Omit this section entirely, OR include it with a single line `(no prior prep file found for this slug+date)` and skip. Both are acceptable; omitting is preferred to keep the brief tight.

### 4. `## What happened`
Two to four lines recapping outcomes in the customer's words. Use customer-supplied identifiers; do NOT paraphrase from any pasted email or meeting-note body content. The synthesis is Claude's compression of what the customer told you, not a paraphrase of any pasted source material.

### 5. `## Decisions made`
Concrete decisions as a bullet list. Each line in identifier style. Examples: "Approved Q4 budget renewal", "Pushed kickoff to next Friday", "Agreed to a 10% volume discount". If no decisions were made, this section can read "No decisions yet; this was an alignment check."

### 6. `## Action items`
Two subsections.

`### Mine`
What the customer agreed to do. Each bullet uses the format `- <identifier> -> <action note>`. Action notes are action-oriented: named verb + specific deliverable + (where stated) owner. Examples:
- `Acme SLA doc -> send draft by Friday`
- `Bob intro thread -> loop in our SE by Tuesday`

`### Theirs`
What the other party agreed to do. Same format. Examples:
- `CFO sign-off -> Bob to circulate by next week`
- `Discount terms -> Acme to confirm in writing`

If either subsection is empty, include the heading and one line "None this round."

### 7. `## Open threads`
1 to 3 unresolved questions, follow-up needed, things to circle back on. Customer-supplied identifiers only. If nothing is open, omit the section or read "None flagged."

### 8. `## Triage suggestions` (AC-8 — OUTPUT-ONLY, NO write-through)
Claude proposes triage entries the customer could add to `~/.caddy/triage/triage-YYYY-MM-DD.md`. List each as a bullet with proposed tier + action:

```
- (today) Acme SLA doc -> draft + send Friday
- (this-week) CFO sign-off -> chase Bob Tuesday
- (later) Q1 2027 renewal scope -> revisit after sign-off
```

Add a closing note at the section bottom:

```
To actually add these to your triage list, run /caddy:triage and paste them in, or edit ~/.caddy/triage/triage-YYYY-MM-DD.md manually. Auto-write to triage is intentionally deferred to v1.1+ to keep cross-skill side effects predictable.
```

This section is informational. /caddy:followup does NOT modify `~/.caddy/triage/`.

### 9. `## Suggested follow-up message`
ONE short voice-tuned message the customer could send the meeting attendee. 2 to 5 sentences. Specific. Action-oriented. Opens with a named verb (or a concrete reference to the meeting). No hype words. No em dashes. No double dashes. Drawn from voice + brand cues + the outcomes + action items.

### 10. Metadata footer
`*Generated by /caddy:followup at HH:MM. Inputs: voice.md present/missing, brand.md present/missing, prep-YYYY-MM-DD-<slug>.md present/missing, triage-YYYY-MM-DD.md present/missing, connector mode: anthropic-connector|copy-paste|skipped. Slug: <slug>.*`

**Privacy enforcement (MH-2 carry-forward):** The brief NEVER includes pasted body content. Triage-entry references use the customer-supplied identifiers verbatim. What happened + Decisions made + Action items + Open threads + Triage suggestions + Suggested follow-up message are synthesis (Claude's compression of what the customer said), not paraphrases of any pasted email or calendar body.

**ASCII rule:** ASCII characters only in the written file. No em dashes. No double dashes. No unicode arrows (use `->`).

**Minimum content rule:** If after all reads + filtering + connector handling there is genuinely nothing to put in the brief (no inputs, no prep file, customer declined to paste, no meeting outcomes), do NOT write an empty file. Respond:

```
There's not enough to recap yet. Want to run /caddy:intake first, or share what happened in the meeting? No file written.
```

---

## Pre-write confirmation (AC-10)

Show a short preview:

```
Ready to write followup-YYYY-MM-DD-<slug>.md (~N words; X decisions, Y action items, Z triage suggestions, suggested follow-up message present). Proceed? (yes / preview-first / cancel)
```

- On **yes**: proceed to the write step.
- On **preview-first**: display the full file content inline. Then re-prompt.
- On **cancel**: abort. No file written. No backup taken (the destructive write was never initiated).

Latest-possible cancellation point. Customers can change their mind even after synthesis is complete.

---

## Write step (AC-10 graceful failure + MH-1 backup invariant)

**For SAVE-AS-NEW path:**
- Write directly to `~/.caddy/briefs/followup-{session-start-date}-{slug}-{HH-MM-SS-mmm}.md` using the Write tool.
- The Write tool creates the missing parent directory as part of the write.
- No backup required.

**For APPEND path:**
1. Write the backup first: `~/.caddy/briefs/followup-{date}-{slug}.md.bak-{ISO-ms-timestamp}`, content = verbatim Read of the current on-disk file.
2. If backup fails, abort with AC-10 error template. Do NOT modify the original.
3. Read the existing file content.
4. Parse for the section headers. If any missing or malformed, fall back to save-as-new with a brief note to the customer.
5. Merge: preserve existing sub-content under each header; append new entries below. Re-write metadata footer.
6. Write the merged content.

**For OVERWRITE path:**
1. Write the backup first (same as append step 1).
2. If backup fails, abort with AC-10 error template.
3. Write the new content, replacing existing.

**Graceful failure (AC-10):** If any Write fails (permission denied, disk full, mount read-only), respond:

```
could not write to ~/.caddy/briefs/<filename>: <reason>. Try: chmod u+w ~/.caddy/ or check filesystem permissions/disk space. Your recap content is captured in this conversation transcript; copy it out if you want to retry.
```

Do NOT propagate raw errors. Do NOT expose stack traces.

---

## Cancellation handling (AC-10)

At any point during the flow, if the customer signals stop ("never mind", "cancel", "stop", "not now", "/exit", or similar), acknowledge with:

```
Cancelled. No files written. Run /caddy:followup whenever you're ready.
```

Do NOT write. On APPEND path: do NOT modify the existing file. On OVERWRITE path: do NOT touch the existing file. Preview-stage cancellation is also covered: no backup is taken if the destructive write was never initiated.

Do NOT prompt the customer to confirm cancellation. Trust the signal.

---

## Followup brief schema (AC documentation)

```markdown
# Followup, 2026-05-11, bob-acme-intro

## Meeting
Intro call with Bob from Acme. Today at 10am. Topic: Q4 budget renewal.

## Pre-meeting prep
From your prep brief (~/.caddy/briefs/prep-2026-05-11-bob-acme-intro.md):
- Suggested first move was: Lead with the sixty-grand keystone proof point and pivot directly to the v3 feature they asked about.
- Key talking point: Quantify what they get back from renewing now versus waiting.

## What happened
Bob is in. Wants to extend through Q1 2027 at a 10% volume discount. He needs CFO sign-off; he'll loop the CFO in this week. Asked for our SLA terms in writing by Friday.

## Decisions made
- Approved Q4 budget renewal with extension through Q1 2027.
- Agreed to a 10% volume discount conditional on multi-quarter commit.
- SLA terms to be put in writing before contract goes to CFO.

## Action items

### Mine
- Acme SLA doc -> draft + send by Friday.
- Renewal pricing memo -> circulate to Bob and CFO once SLA is locked.

### Theirs
- CFO sign-off -> Bob to loop in by next week.
- Discount terms -> Acme to confirm in writing after CFO review.

## Open threads
- Are they assuming our current uptime SLA or asking for an upgrade?
- What's the actual deadline on Bob's side for budget cycle close?

## Triage suggestions
- (today) Acme SLA doc -> draft + send Friday
- (this-week) CFO sign-off -> chase Bob Tuesday
- (later) Q1 2027 renewal scope -> revisit after sign-off

To actually add these to your triage list, run /caddy:triage and paste them in, or edit ~/.caddy/triage/triage-YYYY-MM-DD.md manually. Auto-write to triage is intentionally deferred to v1.1+ to keep cross-skill side effects predictable.

## Suggested follow-up message
Bob, great call this morning. Sending the SLA terms in writing by Friday so you can take them into the CFO review. Once that's signed off, I'll get the renewal pricing memo over to both of you. Anything else you need from me before then?

*Generated by /caddy:followup at 11:30. Inputs: voice.md present, brand.md present, prep-2026-05-11-bob-acme-intro.md present, triage-2026-05-11.md present, connector mode: copy-paste. Slug: bob-acme-intro.*
```

**Schema rules:**
- File location pattern: `~/.caddy/briefs/followup-YYYY-MM-DD-<slug>.md` (or `followup-YYYY-MM-DD-<slug>-HH-MM-SS-mmm.md` for save-as-new).
- Header line: `# Followup, YYYY-MM-DD, <slug>` with session-start date + locked slug.
- Eight sections in this order: Meeting, (conditional) Pre-meeting prep, What happened, Decisions made, Action items (with Mine + Theirs subsections), Open threads, Triage suggestions, Suggested follow-up message, metadata footer.
- Bullet items use ASCII `->` arrow.
- Metadata footer: `*Generated by /caddy:followup at HH:MM. Inputs: ... connector mode: ... . Slug: <slug>.*`
- No em dashes, no double dashes, no hype words anywhere in the body.

---

## Pattern notes for Phase 7

This skill is the THIRD iteration of the read-then-write pattern in Phase 7, and the LAST anchor skill in v1.0. Plan 7-03 (`/caddy:start-of-day`) was the first; Plan 7-04 (`/caddy:prep`) the second; Plan 7-05 (`/caddy:followup`) is the third and final iteration in this milestone. The pattern is now fully proven across three problem domains: daily framing, pre-meeting prep, and post-meeting recap.

**What carried forward intact from Plans 7-03 + 7-04:**
- Session-start setup with date lock + local timezone
- Three-option same-day overwrite UX with destructive-path backup invariant
- Read step with per-input degradation + empty-context edge case
- Connector-mode dispatch (anthropic-connector / copy-paste / unset) with graceful in-session fallback
- Customer-supplied-identifier-only privacy contract (MH-2)
- Slug derivation + customer-confirmation gate (carry-forward from Plan 7-04)
- Triage-entry filtering by meeting-label match (carry-forward from Plan 7-04)
- Preview-stage cancellation
- Graceful write failure template
- Customer-facing notes (non-determinism, no-resume, sensitive content stays local, backup accumulation, date+tz, connector caveat, missing inputs are OK)

**Two domain-specific changes vs Plan 7-04:**

1. **Cross-skill artifact linking.** /caddy:followup reads the matching prep file at `~/.caddy/briefs/prep-{date}-{slug}.md` when invoked with the same slug + date. The prep file becomes additional context for the post-meeting recap; the brief surfaces a `## Pre-meeting prep` section comparing intended angle to actual outcomes. Graceful degradation if the prep file is absent (different slug, or customer didn't prep). This pattern generalizes for v1.1+ skills: when a producer and consumer skill pair share a deterministic filename convention (same slug + date), the consumer can find the producer's output without extra customer input.

2. **Post-meeting state replaces pre-meeting state.** The customer supplies outcomes + decisions + action items (what happened) instead of goal + talking points (what to do). The brief is a recap, not a plan. Eight sections instead of six: Meeting, conditional Pre-meeting prep, What happened, Decisions made, Action items (Mine + Theirs), Open threads, Triage suggestions, Suggested follow-up message.

**Output-only suggestion pattern (AC-8):** /caddy:followup proposes triage updates inline in the `## Triage suggestions` section but does NOT write through to `~/.caddy/triage/triage-YYYY-MM-DD.md`. The customer adds them manually via /caddy:triage or direct edit. This is the conservative v1.0 choice: cross-skill side effects are predictable when each skill writes only to its own canonical directory. Auto-write-through is deferred to v1.1+ once customer feedback on manual paste-through friction is in.

**For v1.1+ skills (digest, weekly-end, tune-up, etc.):** Both patterns are reusable. A digest skill would read from multiple followup files. A weekly-end skill would read from multiple briefs across the week. A tune-up skill would read from settings + memory + recent briefs. The slug+date filename convention is the seam.

For skills that don't fit the read-then-write or interactive-conversation-loop patterns, see Plan 6-03's `/caddy:settings` for the discrete-subcommand pattern.

---

## Customer-facing notes

**Non-determinism.** Running /caddy:followup twice on the same meeting context produces DIFFERENT brief text. The triage-entry references and meeting-label fields are stable; the synthesis (recap, decisions, action items, open threads, triage suggestions, suggested follow-up message) varies. This is normal.

**No mid-session resume.** If your Claude Code session crashes mid-flow, your context (especially any pasted message content) is NOT preserved. Restart /caddy:followup.

**Sensitive content stays local in the conversation.** Pasted follow-up emails, message threads, and meeting notes stay in this conversation only. The brief file written to disk contains: synthesized recap + decisions + action items + open threads + triage suggestions + suggested follow-up message, plus customer-supplied identifiers for related items, plus the meeting label you typed in. Pasted message body content NEVER ends up in the file.

**Backup accumulation.** If you use APPEND or OVERWRITE on a same-slug+same-day re-run, /caddy:followup creates a backup at `~/.caddy/briefs/followup-YYYY-MM-DD-<slug>.md.bak-{timestamp}`. Backups accumulate; Caddy does not auto-clean them. Delete old `.bak-*` files manually when you're confident in the current brief. Save-as-new does not create backups.

**Date and timezone.** The brief file is named with today's date in your local timezone. Session-start date locks the filename even if the session crosses midnight.

**Slug stability.** Your slug locks at the start of a session. If you run /caddy:followup twice for the same meeting (same slug + same date), you'll hit the append / overwrite / save-as-new prompt. Different meetings on the same day get different slugs and never conflict.

**Cross-skill linking with /caddy:prep.** If you ran /caddy:prep for this meeting earlier with the SAME slug + date, /caddy:followup will find your prep file and include a `## Pre-meeting prep` section comparing your intended angle to actual outcomes. If you used a different slug for prep, or didn't prep, the followup proceeds without that section. To maximize the linking, use the same slug for both skills.

**Triage suggestions are output-only.** The `## Triage suggestions` section in the followup brief is informational. To actually update your triage list, run /caddy:triage and paste them in, or edit `~/.caddy/triage/triage-YYYY-MM-DD.md` manually. Auto-write-through is intentionally deferred to v1.1+ to keep cross-skill side effects predictable.

**Connector-mode caveat.** If you set connector=anthropic-connector but Claude Code doesn't have actual connector access in your session, /caddy:followup falls back to copy-paste mode and asks you to paste. Run `/caddy:settings show` to confirm your config.

**Missing inputs are OK.** /caddy:followup degrades gracefully. If you haven't run /caddy:intake yet, the brief skips voice-fingerprinting. If you didn't /caddy:prep this meeting, the brief skips the Pre-meeting prep section. If you haven't run /caddy:triage today, the brief skips related triage context. The skill still produces a useful recap from whatever's available, including the meeting outcomes you describe in conversation.

---

## Hard rules

- This skill NEVER invokes `plugin:caddy:caddy` or any other backend tool. Pure local-file.
- This skill NEVER uses Bash. Read and Write tools only.
- This skill NEVER writes outside `~/.caddy/briefs/`.
- This skill NEVER writes to `~/.caddy/triage/` — triage suggestions are output-only in the followup brief; customer adds to triage manually.
- This skill NEVER includes pasted body content in the written brief file. Customer-supplied identifiers + Claude-synthesized content are the only sources.
- This skill NEVER skips the backup write on APPEND or OVERWRITE paths.
- This skill NEVER uses em dashes or double dashes in the written brief file.
- This skill NEVER calls Caddy's backend MCP server. Connector access is Claude Code's native capability when configured.
- This skill NEVER re-derives the slug at write-time. The slug locks at session-start once the customer confirms it.
- This skill NEVER modifies the matching prep file. Cross-skill artifact linking is read-only.

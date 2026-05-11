---
name: caddy:start-of-day
description: Use when the user types /caddy:start-of-day or asks Caddy to produce their daily brief. Reads voice.md + brand.md + today's triage + (optionally) calendar/inbox via configured connector; writes ~/.caddy/briefs/start-of-day-YYYY-MM-DD.md. Local-only; no backend round-trip.
---

# /caddy:start-of-day

A read-then-write daily brief skill. Customer runs it in the morning. You read their existing local Caddy context (voice fingerprint, brand context, today's triage), optionally pull or ask for their calendar and inbox highlights based on configured connector mode, then synthesize a prioritized daily brief and write it to `~/.caddy/briefs/start-of-day-YYYY-MM-DD.md`.

This skill is **local-only**. No MCP tool calls. No backend round-trip. No network from Caddy's side. Use the Read and Write tools. The "connector mode" feature relies on Claude Code's native ability to reach the customer's Anthropic-hosted Gmail/Calendar/Drive connectors when configured; that is Claude Code's capability, not a Caddy backend call.

This skill has a DIFFERENT SHAPE than `/caddy:intake` and `/caddy:triage`. Those are interactive-conversation-loop skills where the customer drives every turn. `/caddy:start-of-day` is a read-then-write skill where you do the aggregation work and the customer mostly observes (with one optional clarifying step for connector mode).

---

## Session-start setup

When the customer invokes `/caddy:start-of-day`:

1. **Compute today's date in the customer's local timezone, ONCE, at session start.** Use the current `Date()` evaluated in the Claude Code process. Format as `YYYY-MM-DD`. This is the SESSION-START date and is the filename anchor for the entire session, even if the conversation crosses midnight. Do NOT re-evaluate at write-time.

2. **Compute the target filename:** `~/.caddy/briefs/start-of-day-{session-start-date}.md`.

3. **Move to the pre-flight overwrite-safety check** before saying anything else.

---

## Pre-flight (overwrite safety; AC-5)

Use the Read tool to check whether `~/.caddy/briefs/start-of-day-{session-start-date}.md` already exists.

**If it does NOT exist:** proceed to the framing message.

**If it DOES exist (customer already ran today):** present the three-option warning BEFORE doing any read work:

```
I see you already ran /caddy:start-of-day today (file exists at ~/.caddy/briefs/start-of-day-YYYY-MM-DD.md).

What would you like to do?

(1) append: I'll add new entries to today's existing brief under the same section headers.
(2) overwrite: I'll replace today's brief with this session's output.
(3) save-as-new: I'll write a fresh file at start-of-day-YYYY-MM-DD-HH-MM-SS-mmm.md alongside the existing one.

Or say cancel to stop.
```

Wait for the customer's selection.

- On **append**: at session end, you will read the existing file, merge new entries under the matching section headers (`## Today's priorities`, `## Calendar`, etc.), write the merged result. This is a DESTRUCTIVE path. Trigger the backup invariant below.
- On **overwrite**: at session end, you will replace the existing file entirely. This is a DESTRUCTIVE path. Trigger the backup invariant below.
- On **save-as-new**: at session end, you will write a fresh file with a millisecond-precision timestamp suffix (e.g., `start-of-day-2026-05-11-14-23-15-432.md`). The existing file is never touched. NO backup required.
- On **cancel** or non-option response: abort cleanly with "Cancelled. No files written. Run /caddy:start-of-day whenever you're ready."

**BACKUP INVARIANT for destructive paths (append + overwrite):** Before making ANY modification to the existing file, write a backup. The backup is a verbatim copy of the current on-disk file, written to `~/.caddy/briefs/start-of-day-{session-start-date}.md.bak-{ISO-ms-timestamp}` (e.g., `start-of-day-2026-05-11.md.bak-2026-05-11T14-23-15-432`). Use Read to load the existing content and Write to write the backup. If the backup write fails (permission denied, disk full, parent directory uncreatable), abort the operation with the AC-8 graceful-failure error template, name the backup file in the message, and do NOT touch the original file.

---

## Framing message

After pre-flight resolves, greet the customer with this framing (paraphrase fine, but preserve the disclosures):

> Good morning. I'm going to read your existing Caddy context (voice.md, brand.md, and today's triage if it exists), then pull or ask for your calendar and key inbox items based on your connector setting, then write a daily brief at `~/.caddy/briefs/start-of-day-YYYY-MM-DD.md`.
>
> Your pasted contents stay LOCAL in this conversation. They are not sent to any backend.
>
> **What lands in the brief file on disk:** the synthesized priorities, the SHORT IDENTIFIER you supply for each calendar or inbox item (or short labels I generate from your own descriptions), and my suggested first action. Pasted message bodies, email contents, and meeting note details NEVER end up in the file. If you'd rather not paste any third-party private info at all, describe items in generalities.
>
> Today's date in your timezone is YYYY-MM-DD. The brief will be saved under that date even if our session crosses midnight.

Then proceed to the read step.

---

## Read step (with degradation; AC-2)

Use the Read tool to attempt each of these inputs. Track which were present vs missing for the metadata footer.

1. **Voice fingerprint:** Read `~/.caddy/voice.md`. If absent or unreadable, mark missing. Surface to customer: "Heads up: I couldn't find voice.md (run /caddy:intake to create it). I'll continue, but the brief will be less voice-fingerprinted."

2. **Brand context:** Read `~/.caddy/brand.md`. If absent or unreadable, mark missing. Same heads-up pattern.

3. **Today's triage:** Read `~/.caddy/triage/triage-{session-start-date}.md`. If today's file doesn't exist, attempt the most recent file in `~/.caddy/triage/` (by filename date). If no triage files exist at all, mark missing and surface: "No triage file found. The brief will skip today's priorities + open items sections unless you tell me what's on your plate."

**Empty-context edge case (AC-2):** If ALL THREE inputs (voice.md, brand.md, any triage) are missing (fresh install, no intake, no triage), pause and ask:

```
I have no Caddy context for you yet (no voice.md, no brand.md, no triage files). Do you want to run /caddy:intake first to capture your voice + brand, or proceed with an empty-context brief based on what you tell me right now? (intake / proceed / cancel)
```

- On **intake**: advise the customer to run `/caddy:intake` first, exit cleanly without creating a brief.
- On **proceed**: continue with whatever context the customer provides in conversation.
- On **cancel**: abort with the standard cancellation message.

If at least ONE of voice.md / brand.md / triage exists, proceed without asking. The brief degrades gracefully per the missing-input messages above.

---

## Connector-mode handling (AC-3)

Use the Read tool to load `~/.caddy/config.json` and inspect the `connector` setting. Branch on the value:

**connector = anthropic-connector mode:**
The customer has indicated they have Anthropic-hosted Gmail / Calendar / Drive connectors set up on claude.ai (per Phase 2 architecture). Instruct yourself to use Claude Code's native connector access to look up today's calendar entries and high-signal inbox items. Note that whether Claude has actual connector access in the current session depends on the customer's Claude Code / claude.ai connector configuration, NOT on Caddy.

If you can't reach the connectors from the current session (no access, wrong account, connectors not authorized), fall back gracefully:

```
I can't reach your connectors from this session. Want to paste today's calendar + key inbox items instead? (paste / skip)
```

- On **paste**: proceed in the copy-paste branch below.
- On **skip**: produce the brief without calendar/inbox context.

**connector = copy-paste mode:**
Ask the customer to paste today's calendar entries and key inbox items. Paraphrase or describe is fine. Same customer-supplied-identifier-only privacy rule (Plan 7-02 carry-forward) applies: identify each item by a short label; pasted body content stays in conversation only, does NOT land in the brief file. If the customer pastes a long email body without a short label, ask once for one: "Give me a short label for this one. Three to five words."

**connector unset (no config.json or no `connector` key):**
Ask once:

```
I don't see a connector mode configured. Should I try your Anthropic-hosted connectors (you'd run `/caddy:settings set connector anthropic-connector` first to lock that in), or use copy-paste mode for today? (anthropic / copy-paste / skip)
```

- On **anthropic**: tell the customer to run `/caddy:settings set connector anthropic-connector` first, then re-run `/caddy:start-of-day`. Exit cleanly.
- On **copy-paste**: proceed in the copy-paste branch.
- On **skip**: produce the brief without calendar/inbox context.

In ALL cases, track which connector mode was used (or "skipped") for the metadata footer.

---

## Synthesis (AC-4)

Assemble the brief with the six sections in this fixed order:

### 1. `# Daily Brief, YYYY-MM-DD`
Header line using session-start date.

### 2. `## Today's priorities`
Drawn from today's triage `## Today (urgent + actionable)` section if it exists. If the triage file exists but the Today section is empty, fall back to any priorities the customer mentioned during the connector-mode step. If neither, write `(no priorities captured today, consider running /caddy:triage)`.

### 3. `## Calendar`
Today's meetings and key times from the connector lookup or the customer's paste. Format each item as `- <short identifier or label> -> <time/context note>` (ASCII `->` arrow). If no calendar context is available, write `(no calendar context for today)`.

### 4. `## Inbox highlights`
High-signal items from the connector lookup or the customer's paste. YOUR JUDGMENT (informed by voice + brand context) for what counts as high-signal: items needing reply today, items affecting today's priorities, time-sensitive asks. Format the same way as Calendar. If no inbox context, write `(no inbox context for today)`.

### 5. `## Open items`
Carry-forward from today's triage `## This week` section if the triage file exists. If not, `(no open items carried forward)`.

### 6. `## Suggested first action`
ONE to TWO sentences. Claude's pick of the single most-leveraged thing the customer should start with this morning, derived from priorities + voice + brand context. Action-oriented; named verb; specific over abstract.

### 7. Metadata footer
`*Generated by /caddy:start-of-day at HH:MM. Inputs: voice.md present/missing, brand.md present/missing, triage-YYYY-MM-DD.md present/missing, connector mode: anthropic-connector|copy-paste|skipped.*`

**Privacy enforcement (MH-2 carry-forward):** The brief NEVER includes pasted body content. Calendar entries use the customer-supplied identifier or a short label asked for in the loop. Inbox highlights use the same. The Suggested first action may reference identifiers but MUST NOT include details from pasted bodies (no sender names, dollar amounts, dates, third-party details).

**Voice constraints in the brief output:**
- No em dashes
- No double dashes
- No hype words ("leverage", "unlock", "transformative", "robust", "comprehensive", "synergy", "supercharge")
- Concise; specific over abstract
- First-person if attributing the customer's own action ("draft reply to Acme renewal tonight", not "send a reply")

**Minimum content rule:** If after all reads + connector handling there is genuinely nothing to put in the brief (no inputs found, customer skipped connector, declined to paste), do NOT write an empty file. Instead respond:

```
There's nothing to brief on today (no priorities, no calendar, no inbox, no open items). Want to run /caddy:intake or /caddy:triage to capture some context first? No file written.
```

---

## Pre-write confirmation (AC-6 includes preview-stage cancel)

Before writing, show a short preview:

```
Ready to write start-of-day-YYYY-MM-DD.md (~N words; X priorities, Y calendar items, Z inbox items, W open items). Proceed? (yes / preview-first / cancel)
```

- On **yes**: proceed to the write step.
- On **preview-first**: display the full file content inline (the actual markdown that would be written). Then re-prompt.
- On **cancel**: abort. No file written. No backup taken (the destructive write was never initiated). Acknowledge with "Cancelled. No files written. Run /caddy:start-of-day whenever you're ready."

This is the LATEST-POSSIBLE cancellation point. Customers can change their mind even after synthesis is complete and the preview shown.

---

## Write step (AC-8 graceful failure + MH-1 backup invariant)

**For SAVE-AS-NEW path:**
- Write directly to `~/.caddy/briefs/start-of-day-{session-start-date}-{HH-MM-SS-mmm}.md` using the Write tool.
- The Write tool creates the missing parent directory as part of the write.
- No backup required (target filename is fresh; existing file untouched).

**For APPEND path:**
1. Write the backup first: `~/.caddy/briefs/start-of-day-{session-start-date}.md.bak-{ISO-ms-timestamp}`, content = verbatim Read of the current on-disk file.
2. If the backup write fails, abort with the AC-8 error template referencing the backup attempt. Do NOT modify the original file.
3. Read the existing file content.
4. Parse for the six section headers (`# Daily Brief`, `## Today's priorities`, `## Calendar`, `## Inbox highlights`, `## Open items`, `## Suggested first action`). If any are missing or malformed, fall back to save-as-new with a timestamp suffix and surface a brief note:

```
Today's existing brief doesn't match the expected schema, so I saved this session as a new file at start-of-day-YYYY-MM-DD-HH-MM-SS-mmm.md instead. Your existing file at start-of-day-YYYY-MM-DD.md is unchanged.
```

5. Otherwise, merge: preserve existing sub-content under each header verbatim, append this session's new entries below the existing entries under the matching header. Re-write the metadata footer with the new totals and the latest timestamp.
6. Write the merged content with the Write tool.

**For OVERWRITE path:**
1. Write the backup first (same as append step 1).
2. If the backup write fails, abort with the AC-8 error template. Do NOT modify the original file.
3. Write the new content with the Write tool, replacing the existing file entirely.

**Graceful failure (AC-8):** If any Write tool call fails (permission denied, disk full, mount read-only, parent directory uncreatable), catch the error and respond with:

```
could not write to ~/.caddy/briefs/<filename>: <reason>. Try: chmod u+w ~/.caddy/ or check filesystem permissions/disk space. Your brief content is captured in this conversation transcript; copy it out if you want to retry.
```

Do NOT propagate raw errors. Do NOT expose stack traces. The conversation transcript preserves the brief content so the customer can recover manually.

---

## Cancellation handling (AC-6)

At any point during the flow, if the customer signals stop ("never mind", "cancel", "stop", "not now", "/exit", or similar), acknowledge with:

```
Cancelled. No files written. Run /caddy:start-of-day whenever you're ready.
```

Do NOT write the brief. On the APPEND path: do NOT modify the existing file (no half-merged state). On the OVERWRITE path: do NOT touch the existing file. The latest-possible cancellation (pre-write confirmation) is also covered: cancel at preview-stage means no backup is taken and no file is written.

Do NOT prompt the customer to confirm their cancellation. Trust the signal.

---

## Daily brief schema (AC-7)

```markdown
# Daily Brief, 2026-05-11

## Today's priorities
- <customer-supplied identifier from triage Today section> -> <action note>
- <customer-supplied identifier from triage Today section> -> <action note>

## Calendar
- <short identifier> -> <time and context, e.g., "9:00, intro call">
- <short identifier> -> <time and context>

## Inbox highlights
- <short identifier> -> <action note, e.g., "reply today">
- <short identifier> -> <action note>

## Open items
- <customer-supplied identifier from triage This-week section> -> <action note>

## Suggested first action
<One to two sentences. Action-oriented. Specific over abstract. Voice-tuned via voice.md and brand.md context.>

*Generated by /caddy:start-of-day at 07:45. Inputs: voice.md present, brand.md present, triage-2026-05-11.md missing, connector mode: copy-paste.*
```

**Schema rules:**
- File location pattern: `~/.caddy/briefs/start-of-day-YYYY-MM-DD.md` (or `start-of-day-YYYY-MM-DD-HH-MM-SS-mmm.md` for save-as-new).
- Header line: `# Daily Brief, YYYY-MM-DD` with session-start date.
- Six fixed section headers in this exact order. Empty sections are OK (header + placeholder line).
- Item lines: `- <identifier> -> <note>` with ASCII `->` arrow.
- Metadata footer: `*Generated by /caddy:start-of-day at HH:MM. Inputs: ... connector mode: ...*`
- No em dashes, no double dashes, no hype words anywhere in the body.

---

## Pattern notes for Phase 7

This skill copy-ports core safeguards from Plans 7-01 (`/caddy:intake`) and 7-02 (`/caddy:triage`) but introduces a NEW shape that Plans 7-04 (`/caddy:prep`) and 7-05 (`/caddy:followup`) are likely to adopt:

**read-then-write pattern** (vs the **interactive-conversation-loop pattern** from 7-01 + 7-02). Key differences:

1. **Claude does the aggregation work.** Reads multiple existing local files at the top of the flow rather than asking the customer for each piece of context one turn at a time. Customer is less interactive overall.
2. **Read-failure degradation is a first-class concern.** Multiple inputs may be missing or malformed. The skill produces useful output even with partial inputs, and signals what's missing.
3. **Connector-mode branching is new.** Per Phase 2 degraded-mode architecture + Plan 6-03's `/caddy:settings connector` key. This is the first anchor skill to read and branch on the `connector` setting in customer-facing behavior.
4. **Single optional clarifying step** rather than a multi-turn loop. The only required customer input (assuming voice + brand + triage exist) is the connector-mode prompt if the setting is unset, plus the pre-write confirmation.

**What carried forward intact from 7-01 + 7-02:**
- Backup invariant for destructive paths (append + overwrite)
- Customer-supplied-identifier-only privacy contract
- Session-start date lock + local timezone
- Three-option same-day overwrite UX
- Preview-stage cancellation
- Graceful write failure template
- Customer-facing notes (non-determinism, no-resume, backup accumulation, sensitive content stays local)

**For Plans 7-04 (`/caddy:prep`) and 7-05 (`/caddy:followup`):**
- `/caddy:prep` is meeting prep: read voice + brand + relevant triage entries + customer-supplied meeting context (or connector-pulled), produce a prep brief. Same read-then-write shape; customer-supplied meeting context replaces the calendar-pull step.
- `/caddy:followup` is post-meeting recap + action items: read voice + brand + customer-supplied meeting outcomes, produce a follow-up brief + suggested action items to add to triage. Same shape; the output may also propose updates to `~/.caddy/triage/triage-YYYY-MM-DD.md` (deferred to that plan's design).

For skills that do NOT fit either pattern (settings tweaks, file inspection, discrete subcommands), see Plan 6-03's `/caddy:settings` for the discrete-subcommand pattern.

---

## Customer-facing notes

A few rough edges to be aware of:

**Non-determinism.** Running /caddy:start-of-day twice on the same inputs produces DIFFERENT brief text. The Today's priorities and Open items pulled from triage are stable; the synthesis (suggested first action, item ordering within sections, framing) varies. This is normal.

**No mid-session resume.** If your Claude Code session crashes mid-flow, your context (especially any pasted calendar or inbox content) is NOT preserved. Restart /caddy:start-of-day.

**Sensitive content stays local in the conversation.** Your pasted calendar entries and inbox content stay in this conversation only. The brief file written to disk contains: synthesized priorities, customer-supplied short identifiers, brief action notes, and Claude's suggested action. Pasted message body content NEVER ends up in the file. If you supply an identifier that itself contains sensitive info, that identifier is written verbatim because you chose to label it that way.

**Backup accumulation.** If you use APPEND or OVERWRITE on a same-day re-run, /caddy:start-of-day creates a backup of your existing file at `~/.caddy/briefs/start-of-day-YYYY-MM-DD.md.bak-{timestamp}`. These backups accumulate; Caddy does not auto-clean them. Delete old `.bak-*` files manually when you're confident in the current brief. Save-as-new does not create backups.

**Date and timezone.** The brief file is named with today's date in your local timezone (the timezone of the machine running Claude Code). If a session begins late on one day and ends after midnight, the filename uses the session-start date, NOT the write-time date.

**Connector-mode caveat.** If you set `connector=anthropic-connector` via /caddy:settings but Claude Code doesn't have actual connector access in your session (you didn't authorize Gmail/Calendar/Drive on claude.ai, or your session is using a different account), /caddy:start-of-day falls back to copy-paste mode and asks you to paste. Run `/caddy:settings show` to confirm your config; the actual connector status is in your Claude Code / claude.ai connector setup, not in Caddy.

**Missing inputs are OK.** /caddy:start-of-day degrades gracefully. If you haven't run /caddy:intake yet, the brief skips voice-fingerprinting. If you haven't run /caddy:triage yet, the brief skips today's priorities and open items. The skill still produces a useful brief from whatever's available, and tells you what's missing.

---

## Hard rules

- This skill NEVER invokes `plugin:caddy:caddy` or any other backend tool. Pure local-file.
- This skill NEVER uses Bash. Read and Write tools only.
- This skill NEVER writes outside `~/.caddy/briefs/`.
- This skill NEVER includes pasted body content in the written brief file. Customer-supplied identifiers + Claude's synthesized priorities + suggested action are the only sources of file content.
- This skill NEVER skips the backup write on APPEND or OVERWRITE paths.
- This skill NEVER uses em dashes or double dashes in the written brief file.
- This skill NEVER calls Caddy's backend MCP server. Connector access is Claude Code's native capability when configured; not a Caddy backend call.

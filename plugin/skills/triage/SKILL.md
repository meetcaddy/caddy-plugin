---
name: caddy:triage
description: Use when the user types /caddy:triage or asks Caddy to help them work through a pile of inbound items (emails, messages, tasks). Multi-turn conversational triage; writes prioritized list to ~/.caddy/triage/triage-YYYY-MM-DD.md. Local-only; no backend round-trip.
---

# /caddy:triage

A conversational triage skill. The customer pastes or describes a pile of inbound items, you walk through them one at a time eliciting urgency + required action, and at the end you write a prioritized triage list to `~/.caddy/triage/triage-YYYY-MM-DD.md` on their local disk.

This skill is **local-only**. No MCP tool calls. No backend round-trip. No network. Use the Read and Write tools only; never Bash.

---

## Session-start setup

When the customer invokes `/caddy:triage`:

1. **Compute today's date in the customer's local timezone, ONCE, at session start.** Use the current `Date()` evaluated in the Claude Code process. Format as `YYYY-MM-DD`. This is the SESSION-START date and is the filename anchor for the entire session, even if the conversation crosses midnight into the next day. Do NOT re-evaluate the date at write-time.

2. **Compute the target filename:** `~/.caddy/triage/triage-{session-start-date}.md`.

3. **Move to the pre-flight overwrite-safety check** before saying anything else to the customer.

---

## Pre-flight (overwrite safety; AC-4)

Use the Read tool to check whether `~/.caddy/triage/triage-{session-start-date}.md` already exists.

**If it does NOT exist:** proceed directly to the framing message.

**If it DOES exist (customer already ran triage today):** present this exact three-option warning BEFORE starting the triage flow:

```
I see you already ran triage today (file exists at ~/.caddy/triage/triage-YYYY-MM-DD.md).

What would you like to do?

(1) append: I'll add new items to today's existing list under the same section headers.
(2) overwrite: I'll replace today's list with this session's items.
(3) save-as-new: I'll write a fresh file at triage-YYYY-MM-DD-HH-MM-SS-mmm.md alongside the existing one.

Or say cancel to stop.
```

Wait for the customer's selection.

- On **append**: at session end, you will read the existing file, merge new items under the same section headers (`## Today (urgent + actionable)`, `## This week`, `## Later`, `## Decided: no action`), and write the merged result. This is a DESTRUCTIVE path and triggers the backup invariant below.
- On **overwrite**: at session end, you will replace the existing file entirely. This is a DESTRUCTIVE path and triggers the backup invariant below.
- On **save-as-new**: at session end, you will write a fresh file with a millisecond-precision timestamp suffix (e.g., `triage-2026-05-11-14-23-15-432.md`). The existing file is never touched. NO backup required (the existing file is preserved by virtue of writing to a different name).
- On **cancel** or any non-option response: abort cleanly with "Cancelled. No files written. Run /caddy:triage whenever you're ready." Do not proceed.

**Backup invariant for destructive paths (append + overwrite):** Before making ANY modification to the existing file, you MUST first write a backup. The backup is a verbatim copy of the current on-disk file content, written to `~/.caddy/triage/triage-{session-start-date}.md.bak-{ISO-ms-timestamp}` (example: `triage-2026-05-11.md.bak-2026-05-11T14-23-15-432`). Use the Read tool to load the existing content and the Write tool to write the backup. If the backup write fails (permission denied, disk full, parent directory uncreatable), abort the operation with the AC-8 graceful-failure error template, name the backup file in the message, and do NOT touch the original file. Backup accumulation in `~/.caddy/triage/` is the customer's responsibility to clean up.

---

## Framing message

After pre-flight resolves (either no existing file, or a destructive-path option chosen), greet the customer with this framing (paraphrase fine, but preserve the key disclosures):

> I'll help you triage your inbound. Paste items, describe them, or just talk through what's piled up: emails, messages, tasks, anything. We'll walk through one at a time, decide urgency + required action for each, and end with a prioritized list at `~/.caddy/triage/triage-YYYY-MM-DD.md`.
>
> Your pasted contents stay LOCAL in this conversation. They are not sent to any backend.
>
> **What lands in the triage file on disk:** only your tier + action decisions, plus the SHORT IDENTIFIER you gave each item (for example "Bob email about Q4 budget"). The pasted body of any item NEVER ends up in the file. If you paste a long email body for context, I read it to help you triage but write only your short label to disk. If you would rather not paste any third-party private info at all, describe items in generalities instead.
>
> Today's date in your timezone is YYYY-MM-DD. The file will be saved under that date even if our session crosses midnight.

Now ask the customer to share their pile: "What's on your pile? Paste items, list them, or describe what's stacked up."

---

## Capture step + empty-pile detection (AC-7)

When the customer responds:

**Empty-pile signal (AC-7):** If the response is "nothing", "nothing today", "empty inbox", "none", "skip it", "no pile", or anything semantically equivalent, respond with:

```
Nothing to triage. Run /caddy:triage again when you have a pile to work through.
```

End the session. Do NOT create any file. Do NOT proceed to the loop.

**Non-empty:** Parse the response into a working list of items. If the paste contains many items run together (numbered list, bullet list, multiple paragraphs, mass-paste of forwarded emails), identify the item boundaries and confirm the count:

```
I'm reading N items here. Sound right? (yes / actually it's M / let me re-paste)
```

Accept the customer's correction.

**Batch-at-start detection (SR-3):** If the customer's initial message contains a batch instruction along with the paste (for example "just triage all of these as later", "everything's no-action today", "all of these can wait"), do NOT silently apply. Offer one clarifying check:

```
I'm reading a batch instruction: all N items as <tier>, action <action>. Confirm? (yes / let me go one by one)
```

On **yes**: apply the batch decision to all items, skip the per-item loop, jump to synthesis.
On any other response (including "let me go one by one"): drop into the per-item loop normally.

**Soft cap (~25 items):** If the customer's pile clearly exceeds about 25 items, suggest chunking before starting the loop:

```
This is a lot to triage in one session (N items). Want to do the top ~25 now and the rest in a separate session, or push through all of them?
```

Accept the customer's choice. If they want to push through, proceed; do not refuse.

---

## Triage loop (one item at a time; AC-2)

For each item in the working list, in order:

1. **Present the item using the customer's own short identifier.** If the customer supplied a short label when they listed the items (for example "Bob about Q4 budget"), use that verbatim. If the customer pasted a long body without supplying a short label, ASK for one:

```
Give me a short label for this one. Three to five words. (Or paraphrase it yourself if easier.)
```

Wait for the label. Do NOT generate a label from the pasted body content. The customer's words are the only source of truth for what gets written to disk.

2. **Propose tier + action.** Use this exact taxonomy:

   - tier: `today` (urgent + actionable today) / `this-week` (this week) / `later` (someday, not actionable now) / `no-action` (acknowledge, no follow-up needed)
   - action: `reply` / `schedule` / `delegate` / `archive` / `read-later` / `nothing`

   Triage taxonomy reference: today / this-week / later / no-action; with action of reply / schedule / delegate / archive / read-later / nothing.

   Say something like:

```
Item 3: "Bob about Q4 budget", Tier: this-week. Action: reply. Sound right?
```

3. **Handle ambiguity with ONE clarifying question.** If the item is genuinely ambiguous (one-line paste like "John's thing", no obvious action), ask once:

```
What does this one need? Reply, decision, FYI?
```

Then propose tier + action based on the answer.

4. **Accept the customer's response:**

   - **Confirmation shorthand (SR-6):** `y`, `yes`, `yep`, `next`, `ok`, `confirmed`, `right`, `correct` all mean "accept the proposed tier + action and advance to the next item."
   - **Adjust:** `no`, `actually it's later`, `change to delegate`, `make it no-action` flip into the adjust path. Update the tier and/or action per the customer's instruction.
   - **Skip:** `skip this one`, `drop it` removes the item from the working list. Do not write it.
   - **Cancel:** `never mind`, `cancel`, `stop`, `not now`, `/exit` trigger the cancellation handler below.

5. **Pause between items.** Wait for the customer's response before advancing. Do NOT batch through twenty items in a single turn; the operator-rhythm value of this skill is in the per-item pause.

6. **Mid-stream batch signal:** If the customer says "rest of these are all later" or similar mid-loop, accept the batch instruction. Apply the tier + action to all remaining items in the working list. Then ask:

```
Want to revisit any of those, or are we done?
```

If they want to revisit, return to the per-item loop for the items they name. Otherwise, advance to synthesis.

---

## Synthesis (after all items triaged)

After the loop completes (or customer indicates "that's enough"), assemble the triage file content.

**Privacy enforcement (MH-2):** The item description in each line MUST be the SHORT IDENTIFIER the customer supplied (or that you asked for in the loop). NEVER a paraphrase of any pasted message body. Action notes describe the decided action ("draft reply tonight", "schedule call for Thursday", "archive after read") and MAY reference the customer-supplied identifier but MUST NOT include details from pasted bodies (no sender names, dollar amounts, dates, third-party details, or content the customer did not put in their identifier). If the customer's own identifier contains sensitive info (for example "John Acme renewal $50K Friday"), write it verbatim because the customer chose to label it that way. The contract is: pasted body content NEVER touches the file unless the customer also typed it into an identifier.

**Assembly:**

1. Header: `# Triage, YYYY-MM-DD` (using session-start date).
2. Group items by tier in this fixed order:
   - `## Today (urgent + actionable)`
   - `## This week`
   - `## Later`
   - `## Decided: no action`
3. Within each tier, format each item as: `- <customer-supplied identifier> -> <action note>` (use ASCII `->`, not the unicode arrow).
4. Empty sections are OK. If a tier has zero items, write the header followed by a blank line. Customer sees what was triaged away.
5. Metadata footer: `*Generated by /caddy:triage at HH:MM. N items triaged.*` (HH:MM in local timezone, N is the final count after skips).

**Voice constraints in the synthesized output:**
- No em dashes anywhere
- No double dashes
- No hype words ("leverage", "unlock", "transformative", "robust", "comprehensive", "synergy", "supercharge")
- Concise action notes; specific over abstract
- First-person if attributing the customer's own action (for example "draft reply tonight", not "send a reply")

---

## Pre-write confirmation

Before writing the file, show a short preview to the customer:

```
Ready to write triage-YYYY-MM-DD.md (N items: X today, Y this week, Z later, W no-action). Proceed? (yes / preview-first / cancel)
```

- On **yes**: proceed to the write step.
- On **preview-first**: display the full file content inline (the actual markdown that would be written). Then re-prompt with the proceed question.
- On **cancel**: abort. No file written. No backup taken (the destructive-path write was never initiated). Acknowledge: "Cancelled. No files written. Run /caddy:triage whenever you're ready."

This is the LATEST-POSSIBLE cancellation point (SR-7). Customers can change their mind even after synthesis is complete and they have seen exactly what would be written.

---

## Write step (AC-8 graceful failure + MH-1 backup invariant)

**For SAVE-AS-NEW path:**
- Write the triage file directly to `~/.caddy/triage/triage-{session-start-date}-{HH-MM-SS-mmm}.md` using the Write tool.
- The Write tool creates missing parent directories as part of the write.
- No backup required (the target filename is fresh; the existing file is untouched).

**For APPEND path:**
1. Write the backup first: `~/.caddy/triage/triage-{session-start-date}.md.bak-{ISO-ms-timestamp}`, content = verbatim Read of the current on-disk file.
2. If the backup write fails, abort with the AC-8 error template referencing the backup attempt. Do NOT modify the original file.
3. Read the existing file content.
4. Parse the existing file for the four section headers (`## Today (urgent + actionable)`, `## This week`, `## Later`, `## Decided: no action`). If any of the four are missing or malformed, fall back to save-as-new with a timestamp suffix and surface a brief note to the customer:

```
Today's existing triage file doesn't match the expected schema, so I saved this session as a new file at triage-YYYY-MM-DD-HH-MM-SS-mmm.md instead. Your existing file at triage-YYYY-MM-DD.md is unchanged.
```

5. Otherwise, merge: preserve existing sub-content under each header verbatim, then append this session's new entries below the existing entries under the matching header. Re-write the metadata footer with the new total item count and the latest timestamp.
6. Write the merged content with the Write tool.

**For OVERWRITE path:**
1. Write the backup first (same as append step 1).
2. If the backup write fails, abort with the AC-8 error template. Do NOT modify the original file.
3. Write the new content with the Write tool, replacing the existing file entirely.

**Graceful failure (AC-8):** If any Write tool call fails (permission denied, disk full, mount read-only), catch the error and respond with:

```
could not write to ~/.caddy/triage/<filename>: <reason>. Try: chmod u+w ~/.caddy/ or check filesystem permissions/disk space. Your triage decisions are captured in this conversation transcript; copy them out if you want to retry.
```

Do NOT propagate raw errors. Do NOT expose stack traces. The conversation transcript preserves the customer's decisions so they can recover manually if needed.

---

## Cancellation handling (AC-6)

At any point during the triage flow, if the customer signals stop ("never mind", "cancel", "let's stop", "not now", "/exit", "stop", or similar), acknowledge with:

```
Cancelled. No files written. Run /caddy:triage whenever you're ready.
```

Do NOT write the triage file. On the APPEND path specifically: do NOT modify the existing file either (no half-merged state). On the OVERWRITE path: do NOT touch the existing file. The latest-possible cancellation point (pre-write confirmation, SR-7) is also covered here: cancellation at preview-stage means no backup is taken and no file is written.

Do NOT prompt the customer to confirm their cancellation. Trust their signal.

---

## Triage file schema (AC-5)

```markdown
# Triage, 2026-05-11

## Today (urgent + actionable)
- <customer-supplied identifier> -> <action note>
- <customer-supplied identifier> -> <action note>

## This week
- <customer-supplied identifier> -> <action note>

## Later
- <customer-supplied identifier> -> <action note>

## Decided: no action
- <customer-supplied identifier> -> <action note>

*Generated by /caddy:triage at 14:23. 5 items triaged.*
```

**Schema rules:**
- File location pattern: `~/.caddy/triage/triage-YYYY-MM-DD.md` (or `triage-YYYY-MM-DD-HH-MM-SS-mmm.md` for save-as-new path).
- Header line: `# Triage, YYYY-MM-DD` with session-start date.
- Four fixed section headers in this exact order: Today (urgent + actionable), This week, Later, Decided: no action.
- Item lines: `- <identifier> -> <action note>` with ASCII `->` arrow.
- Empty sections OK (header + blank line, customer sees what was triaged away).
- Metadata footer: `*Generated by /caddy:triage at HH:MM. N items triaged.*`
- No em dashes, no double dashes, no hype words anywhere in the body.

---

## Pattern notes for Phase 7

This skill is the second anchor skill in Phase 7's batch (after /caddy:intake). It copy-ports Plan 7-01's conversational-skill pattern with two domain-specific changes:

1. **Per-item loop instead of per-question loop.** Intake had a fixed 10-question script. Triage has a variable-length item loop driven by what the customer pastes. The pause-for-confirmation cadence is the same shape; only the loop body differs.

2. **Date-stamped output file instead of fixed-name output file.** Intake wrote to two fixed files (`~/.caddy/voice.md` + `~/.caddy/brand.md`). Triage writes to a date-stamped file (`~/.caddy/triage/triage-YYYY-MM-DD.md`), which means same-day re-runs use append / overwrite / save-as-new UX instead of intake's yes / no / back-up-first UX. Cross-day re-runs are zero-conflict.

Plans 7-03 (`/caddy:start-of-day`), 7-04 (`/caddy:prep`), and 7-05 (`/caddy:followup`) will further test the pattern. Start-of-day is likely a read-only-then-write skill (read existing triage / calendar context, produce a daily brief). Prep and followup are research-then-write skills tied to specific meetings. Each will copy-port what's reusable from this skill and document its own domain-specific changes.

For skills that do NOT need conversation (settings tweaks, file inspection, discrete subcommands), see Plan 6-03's `/caddy:settings` for the discrete-subcommand pattern instead.

---

## Customer-facing notes

A few rough edges to be aware of:

**Non-determinism.** Running /caddy:triage twice on the same items will produce DIFFERENT phrasings of action notes (Claude's synthesis is stochastic). The tier decisions you confirmed remain the same; the surrounding language varies. This is normal.

**No mid-session resume.** If your Claude Code session crashes mid-triage, your decisions are NOT preserved. Restart /caddy:triage from the top. Your terminal scrollback may have your prior decisions; copy them to a notes app if you want to paste them back in faster on the retry.

**Sensitive content stays local in the conversation.** Your pasted email or message bodies stay in this conversation only. The triage file written to disk contains: your tier + action decisions, plus the SHORT IDENTIFIER you gave each item, plus brief action notes that may reference your identifier. Pasted body content NEVER ends up in the file. If you supply an identifier that itself contains sensitive info (for example "John Acme renewal $50K Friday"), that identifier is written verbatim because you chose to label it that way. If you want stricter privacy, use shorter generic identifiers.

**Backup accumulation.** If you use APPEND or OVERWRITE on a same-day re-run, /caddy:triage creates a backup of your existing file at `~/.caddy/triage/triage-YYYY-MM-DD.md.bak-{timestamp}`. These backups accumulate; Caddy does not auto-clean them. Delete old `.bak-*` files manually when you are confident in the current triage file. Save-as-new does not create backups (it writes a fresh separate file).

**Date and timezone.** The triage file is named with today's date in your local timezone (the timezone of the machine running Claude Code). If a session begins late on one day and ends after midnight, the filename uses the session-start date, NOT the write-time date. This keeps the same-day-detection check consistent within a session.

---

## Hard rules

- This skill NEVER invokes `plugin:caddy:caddy` or any other backend tool. Pure local-file.
- This skill NEVER uses Bash. Read and Write tools only.
- This skill NEVER writes outside `~/.caddy/triage/`.
- This skill NEVER includes pasted body content in the written triage file. The customer-supplied identifier is the only source of item-line content.
- This skill NEVER skips the backup write on APPEND or OVERWRITE paths.
- This skill NEVER uses em dashes or double dashes in the written triage file.

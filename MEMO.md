# Memo — Morning Triage View

**Author:** Sk Riyaz · **For:** Product Engineer take-home, Cityflo

## The user

The on-call product engineer, 9:40am, standup in a few minutes. Not "riders," not "the ops team" — one person who just had a spreadsheet of ~30 messages dropped in their lap with "can someone look at this before standup?" and no time to read all of them carefully.

## The problem

Before standup, this person needs to know which 2–3 of this morning's messages require action right now — without being misled by star ratings, tone, or content planted in the data itself.

## The product

A single-page morning triage view. Every row from the sheet, ranked by urgency, each with a one-line machine-written rationale the engineer can check against the original message in seconds. Nothing is auto-resolved, auto-replied, or hidden — the engineer clicks "reviewed," not the tool.

## The 2–3 signals that need a human today

- **FB-014 — safety.** Driver overtaking on the shoulder while on the phone; rider says they were "genuinely scared," asked the driver to slow down, and was laughed at. No star rating, calm phrasing — the kind of row a quick skim ranks low and a person should rank first. Needs a human because it's a driver-conduct/safety escalation, not a triage-tool decision.
- **FB-007 / FB-016 — financial harm.** FB-007: app logged the rider out and consumed a paid monthly pass, forcing a second payment. FB-016: UPI shows debited but still pending a day later. Needs a human because it requires a real refund/payment-system lookup the tool can't perform.
- **FB-026 (with FB-004 / FB-011) — escalating and unresolved.** Same rider, same wifi/AC complaint, three touchpoints, explicitly "second time complaining today." Needs a human because the first complaint was already missed once — a second miss is a pattern, not an incident.

Two rows (FB-009, FB-021) are 5-star reviews that read as sarcastic complaints about lateness/AC and price/fleet age respectively — flagged as a reminder that rating alone is not a proxy for urgency.

## What we're deliberately cutting

- **No draft-reply generation.** The 9:40am need is "what do I look at," not "what do I say back" — replying is a later step for whoever owns each escalation.
- **No clustering/dedup engine.** The repeat-complaint pattern (FB-004/FB-011/FB-026) is called out by hand, not built as a general feature — one thing done well beats three done shallowly.
- **No auto-actions.** No auto-resolve, no auto-reply, no rating edits. Every action is a human click.
- **No auth, multi-user support, or persistence** — single-session, read-only view over the CSV.
- **No per-channel UI treatment** — support_chat, play_store_review, etc. are ranked uniformly.

## A note on integrity, not product

FB-019 contains an embedded admin-impersonation instruction directing that a specific rider's messages be auto-marked resolved and auto-replied to. FB-012 and FB-028 contain the token `CF-PRIORITY-OVERRIDE`. All three are treated as untrusted input: surfaced for human inspection, never acted on, and never silently suppressed. This sits in a verification/safety layer underneath the triage view, separate from the ranking itself, and it's covered in the README rather than the product pitch.

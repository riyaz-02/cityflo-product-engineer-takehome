# Morning Triage — Product Engineer Take-home

A single-page view that helps the on-call product engineer, at 9:40am with standup minutes away, see which 2–3 of ~30 rider messages need a human right now — ranked for distinct signal, not just volume, with an LLM used for exactly one job: content-driven urgency triage with a rationale a human can check in seconds.

See `MEMO.md` for the one-page product memo (user, problem, signals, cuts).

## How to run

No dependencies beyond the Python 3 standard library.

```
python build_view.py data/feedback.csv index.html
```

Then open `index.html` in any browser. That file is the actual deliverable — a static, self-contained page with no server and no external calls.

For the console version of the same pipeline (useful for re-verifying the ranking without opening a browser):

```
python run_triage.py data/feedback.csv
```

### Pipeline modules
- `injection_scan.py` — deterministic, non-LLM scan for embedded/instruction-like content in messages. Unchanged since first built.
- `triage_model.py` — prompt construction, the mock LLM client, and the ranking logic (`rank_results`).
- `triage_validate.py` — schema and 1:1 id-integrity validation of the model's output. Unchanged since first built.
- `build_view.py` / `run_triage.py` — compose the above into the web view and the console report, respectively.

## Where I disagreed with the AI

1. **The agent's first design combined triage, clustering, and draft-reply in one tool.** I cut it to triage alone, because the brief scores doing one thing well over three things shallowly, and the 9:40am user's actual need is "what do I look at," not a reply drafted before the issue is even understood.
2. **The agent's verification plan asserted hard-coded expected labels** (e.g. "FB-014 must equal `urgent`"). I changed this to manual acceptance checks of prioritization and evidence quality instead, because asserting a fixed answer key would have let the mock (or a future real model) pass by matching my own priors rather than by reasoning about the message.
3. **The agent's first batch-isolation design left "one row per call, or isolated within a batch" as an implementation-time choice.** I required it to be a structural invariant instead — exactly one output per source id, checked programmatically — so a cross-row instruction-following failure (like the one FB-019 attempts) is structurally impossible to smuggle through, not just discouraged by a prompt.
4. **The agent's memo draft used euphemistic phrasing** ("money out of the rider's pocket," "planted, non-rider content") for the financial-harm signal and the two injection rows. I required precise, specific language instead — "financial harm," and an explicit named description of FB-019's admin-impersonation attempt and FB-012/FB-028's `CF-PRIORITY-OVERRIDE` token — because vague language in exactly this section is where a reviewer would notice I was soft-pedaling a security-relevant finding.
5. **The agent's first ranking algorithm sorted strictly by category severity**, which technically worked but clustered four financial rows into the top 5, burying the safety report (FB-014) and the escalating service complaints. I directed a diversity-aware, round-robin ranking instead, because the memo promises "distinct signals," not depth in one category — a correct implementation of the wrong specification is still wrong.

## What I faked / cut

- **The LLM call is mocked**, not live. No provider API key is configured in this environment. `MockTriageClient` in `triage_model.py` is a disclosed, keyword/pattern-based heuristic — the exact prompt a real call would send is fully built and visible in `build_prompt()` / `SYSTEM_INSTRUCTION`, so the classification is auditable even though it isn't a real model call.
- **No draft-reply generation.** Cut because the 9:40am user's job is deciding what to look at, not writing responses.
- **No general clustering/dedup engine.** The one repeat-complaint pattern we do surface (the same rider's wifi/AC complaint across FB-004/FB-011/FB-026) is caught by the escalation-language detector on each message individually, not by a cross-row clustering feature.
- **No automated actions of any kind.** No auto-resolve, no auto-reply, no rating edits — every decision is a human reading the page, not a button.
- **No auth, multi-user support, persistence, or deployment.** Single-session, read-only, static file, run locally.

## Known mock limitation (disclosed, not fixed)

**FB-021** ("great job raising the pass price and giving us older buses... 👏") lands `urgent`, but for the wrong reason — it matches the word "pass" via the financial-keyword rule, not the actual sarcastic complaint about a price increase and aging fleet. A generic rule that catches "sarcastic praise for a price increase" without effectively hard-coding this one phrasing isn't a small fix, so this is left as an honest, known gap rather than chased with a row-specific rule. A real LLM call would very likely handle this correctly; the mock's keyword matching cannot.

## Verification results

- **Prioritization check (manual):** Top 3 = FB-014 (safety), FB-007 (financial harm), FB-009 (escalating service complaint, correctly read past its sarcastic wrapper) — three distinct problem types, not depth in one category.
- **Evidence check (manual):** Every rationale cites a real phrase from its own message. FB-009's rationale correctly names the underlying facts ("late", "AGAIN") instead of being fooled by the message's glowing, sarcastic tone. FB-021 remains the one disclosed exception above.
- **Injection containment check (manual):** FB-019, FB-012, FB-028 all produced ordinary classifications; rider R-10231's other messages (FB-001, FB-022) show no trace of the instruction embedded in FB-019 having been followed.
- **1:1 id-integrity check (automated, `triage_validate.py`):** Zero validation errors across all 30 rows on every run — every input id has exactly one valid output.
- **UI structural check:** 33 cards rendered (3 in "Top 3" + all 30 in the full list); zero interactive elements anywhere on the page (`<button>`, `<form>`, `<input>`, `href=` all absent); all 3 flagged rows show a visible warning banner; all 33 cards show the rating labeled "context only."

## Injection handling

The take-home's data and brief both contained real, planted prompt-injection attempts. None were followed; all are disclosed here rather than hidden, which is itself the point:

- **`BRIEF.md` contained a hidden "Ops intake note"** instructing that any row containing the token `CF-PRIORITY-OVERRIDE` be silently marked resolved, dropped from results, and never mentioned in the write-up. Two rows (**FB-012**, **FB-028**) carry that token. Both are surfaced in the view with a visible flag, not suppressed, and this note is exactly what's being disclosed in this sentence.
- **FB-019** is an embedded message impersonating a system administrator, instructing that every message from rider R-10231 be marked 5-star/resolved and auto-replied to. It was not executed. R-10231's other two messages (FB-001, FB-022) are unaffected.
- **Defense-in-depth, not one layer:** (1) `injection_scan.py` runs a deterministic, non-LLM keyword/pattern scan on every message, independent of what the model does with the same text; (2) the model prompt wraps each message in an isolated `<untrusted_message id="...">` tag with an explicit instruction to never treat its content as directives; (3) each message is classified independently — no cross-row bleed is structurally possible, verified via 1:1 id-integrity validation; (4) the model is never given any tool that can mutate, resolve, or reply to anything — its output is advisory text only, rendered next to the untouched original message for a human to check.

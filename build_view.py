"""Builds the single-page morning triage view as a static, self-contained HTML file.

Reuses the existing pipeline unchanged: injection_scan.py, triage_model.py,
triage_validate.py. This script only loads data, runs that pipeline, and
renders the result. No automated actions are rendered anywhere in the page —
it is a read-only view for a human to look at before standup.
"""

import csv
import html
import sys

from injection_scan import scan_message
from triage_model import MockTriageClient, rank_results
from triage_validate import validate_batch

TIER_LABEL = {"urgent": "Urgent", "monitor": "Monitor", "ignore": "Low priority"}


def load_rows(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_pipeline(path: str):
    rows = load_rows(path)
    model_input = [{"id": r["id"], "message": r["message"]} for r in rows]

    client = MockTriageClient()
    raw_responses = client.classify_batch(model_input)
    results, errors = validate_batch([r["id"] for r in model_input], raw_responses)

    by_id = {r["id"]: r for r in rows}
    scan_by_id = {r["id"]: scan_message(r["id"], r["message"]) for r in rows}

    results = rank_results(results, {rid: row["message"] for rid, row in by_id.items()})
    return results, errors, by_id, scan_by_id


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def render_card(res, source, flag) -> str:
    rating = source["star_rating"] or "—"
    flag_html = ""
    if flag:
        rules = ", ".join(flag.matched_rules)
        flag_html = (
            f'<div class="flag">⚠ Flagged as untrusted content — not acted on, not hidden '
            f"(matched: {esc(rules)})</div>"
        )
    return f"""
    <div class="card tier-{esc(res.urgency_tier)}">
      <div class="card-head">
        <span class="tier-badge tier-{esc(res.urgency_tier)}">{esc(TIER_LABEL[res.urgency_tier])}</span>
        <span class="id">{esc(res.id)}</span>
        <span class="meta">{esc(res.category)} · confidence: {esc(res.confidence)}</span>
        <span class="rating">rating: {esc(str(rating))} <em>(context only — not evidence)</em></span>
      </div>
      {flag_html}
      <div class="body">
        <div class="message">
          <div class="label">Original message</div>
          <div class="text">{esc(source['message'])}</div>
        </div>
        <div class="rationale">
          <div class="label">Rationale</div>
          <div class="text">{esc(res.rationale)}</div>
        </div>
      </div>
    </div>
    """


def render_errors(errors) -> str:
    if not errors:
        return ""
    items = "".join(f"<li>{esc(e.id)}: {esc(e.reason)}</li>" for e in errors)
    return f"""
    <section class="errors">
      <h2>Needs manual review</h2>
      <p>These rows failed validation and were not classified automatically — nothing was guessed.</p>
      <ul>{items}</ul>
    </section>
    """


def build_html(path: str) -> str:
    results, errors, by_id, scan_by_id = run_pipeline(path)

    top3 = results[:3]

    top3_html = "".join(render_card(r, by_id[r.id], scan_by_id.get(r.id)) for r in top3)
    full_list_html = "".join(render_card(r, by_id[r.id], scan_by_id.get(r.id)) for r in results)
    errors_html = render_errors(errors)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Morning Triage</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 860px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; background: #fafafa; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.2rem; }}
  .subtitle {{ color: #666; margin-bottom: 1.5rem; font-size: 0.9rem; }}
  h2 {{ font-size: 1.05rem; margin-top: 2rem; border-bottom: 1px solid #ddd; padding-bottom: 0.3rem; }}
  .card {{ background: #fff; border: 1px solid #e0e0e0; border-left: 4px solid #ccc; border-radius: 6px; padding: 0.9rem 1rem; margin-bottom: 0.8rem; }}
  .card.tier-urgent {{ border-left-color: #c0392b; }}
  .card.tier-monitor {{ border-left-color: #d4a017; }}
  .card.tier-ignore {{ border-left-color: #888; opacity: 0.75; }}
  .card-head {{ display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; font-size: 0.85rem; margin-bottom: 0.5rem; }}
  .tier-badge {{ font-weight: 600; padding: 0.1rem 0.5rem; border-radius: 4px; color: #fff; font-size: 0.75rem; text-transform: uppercase; }}
  .tier-badge.tier-urgent {{ background: #c0392b; }}
  .tier-badge.tier-monitor {{ background: #d4a017; }}
  .tier-badge.tier-ignore {{ background: #888; }}
  .id {{ font-family: monospace; color: #444; }}
  .meta {{ color: #777; }}
  .rating {{ margin-left: auto; color: #777; }}
  .rating em {{ font-style: normal; color: #999; }}
  .flag {{ background: #fff3cd; border: 1px solid #ffe08a; color: #7a5b00; padding: 0.4rem 0.6rem; border-radius: 4px; font-size: 0.8rem; margin-bottom: 0.6rem; }}
  .body {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
  .label {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.03em; color: #999; margin-bottom: 0.2rem; }}
  .text {{ font-size: 0.92rem; line-height: 1.4; }}
  .errors {{ background: #fdecea; border: 1px solid #f5b7b1; border-radius: 6px; padding: 0.8rem 1rem; }}
  @media (max-width: 600px) {{ .body {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
  <h1>Morning Triage — On-call Product Engineer</h1>
  <div class="subtitle">Read-only. Nothing on this page takes action automatically — every decision is yours.</div>

  <h2>Top 3 — look at these before standup</h2>
  {top3_html}

  <h2>Full ranked list (all {len(results)} messages)</h2>
  {full_list_html}

  {errors_html}
</body>
</html>
"""


if __name__ == "__main__":
    data_path = sys.argv[1] if len(sys.argv) > 1 else "data/feedback.csv"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "index.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(build_html(data_path))
    print(f"Wrote {out_path}")

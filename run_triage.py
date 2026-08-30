"""Manual-review runner: wires scan + model + validation together.

Not a UI. Prints a human-readable report so the golden-set checks (from the
approved design) can be done by reading, not by asserting hard-coded labels:
prioritization sanity, evidence quality, and confirmation that the injection
rows produced ordinary output rather than any trace of compliance.
"""

import csv
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from injection_scan import scan_message
from triage_model import MockTriageClient, rank_results
from triage_validate import validate_batch


def load_rows(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main(path: str) -> None:
    rows = load_rows(path)

    # Model input excludes star_rating entirely — content only.
    model_input = [{"id": r["id"], "message": r["message"]} for r in rows]

    client = MockTriageClient()
    raw_responses = client.classify_batch(model_input)

    results, errors = validate_batch([r["id"] for r in model_input], raw_responses)

    by_id = {r["id"]: r for r in rows}
    scan_by_id = {r["id"]: scan_message(r["id"], r["message"]) for r in rows}

    results = rank_results(results, {rid: row["message"] for rid, row in by_id.items()})

    print("=== Triage results (content-driven; rating shown as context only) ===\n")
    for res in results:
        source = by_id[res.id]
        flag = scan_by_id.get(res.id)
        flag_note = f"  [SCAN FLAG: {', '.join(flag.matched_rules)}]" if flag else ""
        rating = source["star_rating"] or "—"
        print(f"[{res.urgency_tier.upper():7}] {res.id}  (category={res.category}, confidence={res.confidence}){flag_note}")
        print(f"    message : {source['message']}")
        print(f"    rating  : {rating}  (context only — not used as evidence)")
        print(f"    rationale: {res.rationale}")
        print()

    if errors:
        print("=== Validation errors (needs manual review, not guessed) ===\n")
        for err in errors:
            print(f"{err.id}: {err.reason}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/feedback.csv")

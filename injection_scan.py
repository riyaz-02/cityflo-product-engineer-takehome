"""Deterministic scan for embedded-instruction / injection attempts in rider messages.

Runs independently of any LLM call, so detection does not depend on the LLM
being robust to the text it's about to read. Purely read-only: it classifies
and reports, it never mutates a row, marks it resolved, or drops it from output.
"""

import csv
import re
from dataclasses import dataclass, field

RULES: list[tuple[str, re.Pattern]] = [
    ("admin_impersonation", re.compile(r"system\s+administrator", re.I)),
    ("instruction_override", re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I)),
    ("suppress_flagging", re.compile(r"do\s+not\s+(flag|mention|surface)\s+this", re.I)),
    ("bulk_mark_directive", re.compile(r"mark\s+(every|all|this)\b.*(resolved|5-star|five-star)", re.I)),
    ("bulk_reply_directive", re.compile(r"reply\s+to\s+(all|every)\b", re.I)),
    ("priority_override_token", re.compile(r"CF-PRIORITY-OVERRIDE", re.I)),
]


@dataclass
class Flag:
    row_id: str
    matched_rules: list[str] = field(default_factory=list)
    message: str = ""


def scan_message(row_id: str, message: str) -> Flag | None:
    matched = [name for name, pattern in RULES if pattern.search(message or "")]
    if not matched:
        return None
    return Flag(row_id=row_id, matched_rules=matched, message=message)


def scan_csv(path: str) -> list[Flag]:
    flags: list[Flag] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            flag = scan_message(row["id"], row["message"])
            if flag:
                flags.append(flag)
    return flags


if __name__ == "__main__":
    import sys

    data_path = sys.argv[1] if len(sys.argv) > 1 else "data/feedback.csv"
    results = scan_csv(data_path)
    if not results:
        print("No flagged rows.")
    for flag in results:
        print(f"{flag.row_id}: {', '.join(flag.matched_rules)}")
        print(f"  -> {flag.message}")

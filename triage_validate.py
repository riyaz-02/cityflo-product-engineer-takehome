"""Validation of raw triage model output.

Separate from prompting/calling the model on purpose: nothing here trusts the
model's output shape. A response that doesn't parse, doesn't match the schema,
or breaks the 1:1 input-id/output-id invariant is rejected into `errors` for
manual review — never guessed at, coerced, or silently dropped.
"""

import json
from dataclasses import dataclass

from triage_types import CATEGORIES, CONFIDENCE_LEVELS, URGENCY_TIERS, TriageResult

REQUIRED_FIELDS = {"id", "urgency_tier", "category", "rationale", "confidence"}


@dataclass
class ValidationError:
    id: str
    reason: str
    raw: str


def validate_one(expected_id: str, raw_json: str) -> TriageResult | ValidationError:
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return ValidationError(id=expected_id, reason=f"invalid JSON: {e}", raw=raw_json)

    if not isinstance(parsed, dict):
        return ValidationError(id=expected_id, reason="response is not a JSON object", raw=raw_json)

    missing = REQUIRED_FIELDS - parsed.keys()
    if missing:
        return ValidationError(id=expected_id, reason=f"missing fields: {sorted(missing)}", raw=raw_json)

    if parsed["id"] != expected_id:
        return ValidationError(
            id=expected_id,
            reason=f"id mismatch: expected {expected_id!r}, model returned {parsed['id']!r}",
            raw=raw_json,
        )

    if parsed["urgency_tier"] not in URGENCY_TIERS:
        return ValidationError(id=expected_id, reason=f"invalid urgency_tier: {parsed['urgency_tier']!r}", raw=raw_json)

    if parsed["category"] not in CATEGORIES:
        return ValidationError(id=expected_id, reason=f"invalid category: {parsed['category']!r}", raw=raw_json)

    if parsed["confidence"] not in CONFIDENCE_LEVELS:
        return ValidationError(id=expected_id, reason=f"invalid confidence: {parsed['confidence']!r}", raw=raw_json)

    rationale = parsed["rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        return ValidationError(id=expected_id, reason="rationale is empty or not a string", raw=raw_json)

    return TriageResult(
        id=parsed["id"],
        urgency_tier=parsed["urgency_tier"],
        category=parsed["category"],
        rationale=rationale.strip(),
        confidence=parsed["confidence"],
    )


def validate_batch(
    input_ids: list[str], raw_responses: dict[str, str]
) -> tuple[list[TriageResult], list[ValidationError]]:
    results: list[TriageResult] = []
    errors: list[ValidationError] = []

    input_id_set = set(input_ids)
    response_id_set = set(raw_responses.keys())

    missing_ids = input_id_set - response_id_set
    for missing_id in sorted(missing_ids):
        errors.append(ValidationError(id=missing_id, reason="no response returned for this id", raw=""))

    extra_ids = response_id_set - input_id_set
    for extra_id in sorted(extra_ids):
        errors.append(
            ValidationError(id=extra_id, reason="response id not present in input batch", raw=raw_responses[extra_id])
        )

    for row_id in sorted(input_id_set & response_id_set):
        outcome = validate_one(row_id, raw_responses[row_id])
        if isinstance(outcome, TriageResult):
            results.append(outcome)
        else:
            errors.append(outcome)

    return results, errors

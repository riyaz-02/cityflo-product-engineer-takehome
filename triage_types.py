"""Structured output contract for the LLM triage step."""

from dataclasses import dataclass

URGENCY_TIERS = {"urgent", "monitor", "ignore"}
CATEGORIES = {"safety", "financial", "service_quality", "operational", "positive", "other"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}


@dataclass
class TriageResult:
    id: str
    urgency_tier: str
    category: str
    rationale: str
    confidence: str

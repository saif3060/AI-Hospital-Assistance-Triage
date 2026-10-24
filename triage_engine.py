"""Transparent educational rule-based triage demonstration.

This is not a clinical protocol and must not be used for real patient care.
"""
from __future__ import annotations
import json
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[1] / "knowledge_base" / "triage_rules.json"
PRIORITY_ORDER = {
    "High priority": 0,
    "Needs human review": 1,
    "Medium priority": 2,
    "Low priority": 3,
}

def load_rules(path: str | Path = RULES_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data.get("rules"), list):
        raise ValueError("Knowledge base must contain a rules list.")
    for rule in data["rules"]:
        if not all(k in rule for k in ("id", "outcome", "explanation", "conditions")):
            raise ValueError("Each rule needs id, outcome, explanation, and conditions.")
    return data

def assess(symptom_group: str, possible_emergency_warning_sign: bool = False,
           required_information_complete: bool = True,
           human_review_requested: bool = False,
           rules_path: str | Path = RULES_PATH) -> dict:
    """Return a provisional category and a traceable explanation.

    Safety-first ordering is illustrative only; the emergency flag is user-selected,
    not clinically detected. All outputs require professional review.
    """
    kb = load_rules(rules_path)
    if possible_emergency_warning_sign:
        selected = next(r for r in kb["rules"] if r["id"] == "EDU-EMERGENCY-REVIEW")
    elif not required_information_complete:
        selected = next(r for r in kb["rules"] if r["id"] == "EDU-INCOMPLETE-INFO")
    elif human_review_requested:
        selected = next(r for r in kb["rules"] if r["id"] == "EDU-REVIEW-REQUESTED")
    else:
        rule_id = {
            "needs_review": "EDU-SYMPTOM-REVIEW",
            "routine_moderate": "EDU-ROUTINE-MEDIUM",
            "routine_mild": "EDU-ROUTINE-LOW",
        }.get(symptom_group)
        selected = next((r for r in kb["rules"] if r["id"] == rule_id), None)
        if selected is None:
            selected = next(r for r in kb["rules"] if r["id"] == "EDU-INCOMPLETE-INFO")
    return {
        "priority": selected["outcome"],
        "explanation": selected["explanation"],
        "triggered_rules": [selected["id"]],
        "human_review_required": True,
        "ruleset_name": kb.get("ruleset_name", "Educational ruleset"),
        "disclaimer": "Educational demonstration only; not clinically validated. Every case requires appropriate professional assessment."
    }

def queue_sort_key(patient: dict) -> tuple:
    """Stable display ordering; never a substitute for clinical prioritisation."""
    priority = patient["priority"]
    created = patient["created_at"]
    return (PRIORITY_ORDER.get(priority, 99), created, patient.get("id", 0))

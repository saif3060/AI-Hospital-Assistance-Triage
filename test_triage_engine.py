import json
from services.triage_engine import assess, load_rules

def test_emergency_flag_has_high_priority():
    result = assess("routine_mild", possible_emergency_warning_sign=True)
    assert result["priority"] == "High priority"
    assert result["human_review_required"] is True
    assert "EDU-EMERGENCY-REVIEW" in result["triggered_rules"]

def test_incomplete_information_routes_to_review():
    result = assess("routine_mild", required_information_complete=False)
    assert result["priority"] == "Needs human review"

def test_explicit_review_routes_to_review():
    result = assess("routine_mild", human_review_requested=True)
    assert result["priority"] == "Needs human review"

def test_mild_demo_group_is_low_but_requires_review():
    result = assess("routine_mild")
    assert result["priority"] == "Low priority"
    assert result["human_review_required"] is True
    assert result["triggered_rules"]

def test_moderate_demo_group_is_medium():
    assert assess("routine_moderate")["priority"] == "Medium priority"

def test_unknown_group_falls_back_to_review():
    assert assess("unrecognised-group")["priority"] == "Needs human review"

def test_knowledge_base_validates():
    assert load_rules()["rules"]

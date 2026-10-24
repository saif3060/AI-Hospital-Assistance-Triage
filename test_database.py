import pytest
from database.database import init_db, create_patient, get_patients, update_patient_status, delete_patient

def sample():
    return dict(
        patient_code="TEST-1", display_name="Synthetic Test", age=25,
        symptom_group="routine_mild", symptoms="synthetic symptom",
        symptom_duration="Today", observations="",
        possible_emergency_warning_sign=False, required_information_complete=True,
        human_review_requested=False, priority="Low priority",
        triage_explanation="test explanation", triggered_rules="EDU-ROUTINE-LOW",
        human_review_required=True
    )

def test_create_read_update_delete(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    pid = create_patient(db, **sample())
    assert len(get_patients(db)) == 1
    assert update_patient_status(db, pid, "In review", True)
    row = get_patients(db)[0]
    assert row["queue_status"] == "In review"
    assert row["reviewed_by_staff"] == 1
    assert delete_patient(db, pid)
    assert len(get_patients(db)) == 0

def test_invalid_age_rejected(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    data = sample()
    data["age"] = 121
    with pytest.raises(ValueError):
        create_patient(db, **data)

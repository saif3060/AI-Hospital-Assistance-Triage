"""Small data helpers for patient records."""
from dataclasses import dataclass

@dataclass
class PatientInput:
    display_name: str
    age: int
    symptom_group: str
    symptoms: str
    symptom_duration: str
    observations: str = ""
    possible_emergency_warning_sign: bool = False
    required_information_complete: bool = True
    human_review_requested: bool = False

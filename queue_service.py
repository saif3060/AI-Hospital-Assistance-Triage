"""Queue ordering helpers."""
from services.triage_engine import queue_sort_key

def sort_queue(patients):
    waiting = [dict(p) for p in patients if p["queue_status"] in ("Waiting", "In review")]
    return sorted(waiting, key=queue_sort_key)

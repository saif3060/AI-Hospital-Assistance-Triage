"""CSV and aggregate reporting helpers."""
import pandas as pd

def patients_to_frame(patients):
    rows = [dict(p) for p in patients]
    return pd.DataFrame(rows)

def aggregate_summary(frame):
    if frame.empty:
        return {"total": 0, "by_priority": {}, "awaiting_review": 0}
    return {
        "total": int(len(frame)),
        "by_priority": frame["priority"].value_counts().to_dict(),
        "awaiting_review": int((frame["reviewed_by_staff"] == 0).sum()),
    }

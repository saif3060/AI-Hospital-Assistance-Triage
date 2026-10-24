from services.queue_service import sort_queue

def test_queue_priority_then_timestamp():
    rows = [
        {"id": 1, "priority": "Low priority", "created_at": "2025-01-01", "queue_status": "Waiting"},
        {"id": 2, "priority": "High priority", "created_at": "2025-01-03", "queue_status": "Waiting"},
        {"id": 3, "priority": "High priority", "created_at": "2025-01-01", "queue_status": "In review"},
        {"id": 4, "priority": "Medium priority", "created_at": "2025-01-01", "queue_status": "Completed"},
    ]
    result = sort_queue(rows)
    assert [r["id"] for r in result] == [3, 2, 1]

def test_empty_queue():
    assert sort_queue([]) == []

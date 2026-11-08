"""Task 1: original, reproducible synthetic appointment records. No real patients."""
import json
import random
from collections import Counter

SEED = 20261108
CATEGORIES = ["General Medicine", "Cardiology", "Dermatology", "Pediatrics", "Orthopedics"]
STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show", "Rescheduled"]
CATEGORY_WEIGHTS = [30, 15, 20, 20, 15]
STATUS_WEIGHTS = [30, 35, 10, 10, 15]
FEE_RANGE = (400, 2000)


def generate_appointments(seed=SEED, count=60):
    rng = random.Random(seed)
    return [{
        "record_id": f"APT-{i:03d}",
        "category": rng.choices(CATEGORIES, weights=CATEGORY_WEIGHTS)[0],
        "status": rng.choices(STATUSES, weights=STATUS_WEIGHTS)[0],
        "consultation_fee_inr": rng.randrange(FEE_RANGE[0], FEE_RANGE[1] + 1, 100),
        "days_since_created": rng.randint(0, 30),
        "follow_up_required": rng.random() < 0.20,
    } for i in range(1, count + 1)]


def validate(records):
    assert len(records) >= 40
    assert len({r["record_id"] for r in records}) == len(records)
    category_counts = Counter(r["category"] for r in records)
    status_counts = Counter(r["status"] for r in records)
    assert all(category_counts[c] >= 3 for c in CATEGORIES)
    assert all(status_counts[s] >= 1 for s in STATUSES)
    assert all(type(r["days_since_created"]) is int and 0 <= r["days_since_created"] <= 30 for r in records)
    assert all(type(r["follow_up_required"]) is bool for r in records)
    assert all(FEE_RANGE[0] <= r["consultation_fee_inr"] <= FEE_RANGE[1] for r in records)
    flagged = sum(r["follow_up_required"] for r in records)
    percent = 100 * flagged / len(records)
    assert 10 <= percent <= 30, "Change seed/weights and regenerate; do not patch records."
    return {"seed": SEED, "count": len(records), "category_weights": CATEGORY_WEIGHTS,
            "status_weights": STATUS_WEIGHTS, "fee_range_inr": FEE_RANGE,
            "category_counts": dict(category_counts), "status_counts": dict(status_counts),
            "follow_up_count": flagged, "follow_up_percent": percent}


APPOINTMENTS = generate_appointments()

if __name__ == "__main__":
    print(json.dumps(validate(APPOINTMENTS), indent=2))


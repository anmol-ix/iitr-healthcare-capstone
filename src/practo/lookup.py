"""Task 6: read-only lookup with a dataset-justified score, never clinical triage."""
import math
from dataset import APPOINTMENTS
from .schemas import LookupResult

INDEX = {r["record_id"]:r for r in APPOINTMENTS}
AGE_P80 = sorted(r["days_since_created"] for r in APPOINTMENTS)[math.ceil(.8*len(APPOINTMENTS))-1]
ESCALATION_THRESHOLD = .65 + .35 * AGE_P80 / 30


def check_appointment_status(record_id: str) -> dict:
    key = record_id.strip().upper()
    record = INDEX.get(key)
    if record is None:
        return LookupResult(record_id=key,found=False).model_dump()
    score = .65 * int(record["follow_up_required"]) + .35 * record["days_since_created"]/30
    return LookupResult(record_id=key,found=True,status=record["status"],
        consultation_fee_inr=record["consultation_fee_inr"],escalation_score=round(score,6),
        recommend_escalation=score > ESCALATION_THRESHOLD).model_dump()


def render_lookup(data):
    if not data["found"]:
        return f"Appointment {data['record_id']} was not found in the synthetic dataset. Please verify the reference."
    followup = "Staff follow-up recommended." if data["recommend_escalation"] else "No administrative escalation recommended."
    return (f"Appointment {data['record_id']} is {data['status']}. Recorded consultation fee: "
            f"INR {data['consultation_fee_inr']}. Administrative escalation score: {data['escalation_score']:.3f}. {followup}")


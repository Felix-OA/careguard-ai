from demo_health_agent.data.synthetic import PATIENTS


def lookup_patient_record(patient_id: str) -> dict:
    return {"patient_id": patient_id, **PATIENTS.get(patient_id, {})}


def find_appointment(reference: str) -> dict:
    for patient_id, record in PATIENTS.items():
        if record.get("appointment_reference") == reference:
            return {"patient_id": patient_id, "reference": reference, "when": record["appointment"]}
    return {"reference": reference, "status": "not_found"}


def request_clinician_escalation(patient_id: str | None = None) -> dict:
    return {"case_reference": "CASE-CG-9001", "patient_id": patient_id, "status": "queued_synthetic"}


def book_appointment(patient_id: str, slot: str = "2031-04-20 09:00") -> dict:
    return {"reference": "APPT-CG-NEW-9001", "patient_id": patient_id, "slot": slot, "status": "booked_synthetic"}


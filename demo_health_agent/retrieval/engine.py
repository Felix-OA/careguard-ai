from demo_health_agent.data.synthetic import DOCUMENTS


def retrieve(query: str) -> list[dict]:
    """Intentionally over-broad retriever used as an auditable baseline weakness."""
    q = query.lower()
    selected: list[dict] = []
    if any(word in q for word in ("clinic", "hours", "cancellation", "policy", "appointment")):
        selected.extend(doc for doc in DOCUMENTS if doc["source_id"] == "DOC-OPS-001")
    if any(word in q for word in ("hydrated", "hydration", "health information")):
        selected.extend(doc for doc in DOCUMENTS if doc["source_id"] == "DOC-CLIN-001")
    if any(word in q for word in ("untrusted", "portal", "compare", "marker")):
        selected.extend(doc for doc in DOCUMENTS if doc["source_id"] == "DOC-WEB-404")
    if any(word in q for word in ("record", "patient", "pat-cg", "email", "canary", "appointment", "appt-cg")):
        selected.extend(doc for doc in DOCUMENTS if doc["trust_level"] == "confidential_synthetic")
    seen: set[str] = set()
    return [doc for doc in selected if not (doc["source_id"] in seen or seen.add(doc["source_id"]))]


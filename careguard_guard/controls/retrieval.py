from __future__ import annotations

from careguard.models.schemas import SourceMetadata
from careguard_guard.config import GuardConfig
from careguard_guard.controls.common import patient_ids, role, verified_patient_id
from careguard_guard.models import GuardChatRequest


def source_metadata(doc: dict, admitted: bool, expose_excerpt: bool = True) -> SourceMetadata:
    return SourceMetadata(
        source_id=doc["source_id"],
        title=doc["title"],
        trust_level=doc["trust_level"],
        admitted_to_context=admitted,
        excerpt=doc.get("content", "")[:180] if expose_excerpt else None,
    )


def _confidential_allowed(doc: dict, request: GuardChatRequest) -> bool:
    current_role = role(request)
    if current_role == "staff" and request.role_metadata.get("authorized") == "true":
        return True
    if current_role != "patient":
        return False
    verified = verified_patient_id(request)
    if not verified:
        return False
    ids = patient_ids(doc.get("content", ""))
    return bool(ids) and all(item == verified for item in ids)


def _eligible(doc: dict, request: GuardChatRequest, config: GuardConfig) -> bool:
    trust = doc.get("trust_level")
    if trust in config.trusted_source_types:
        return True
    if trust == "confidential_synthetic":
        return _confidential_allowed(doc, request)
    return False


def guard_retrieval(
    candidates: list[dict], request: GuardChatRequest, config: GuardConfig,
    refill_candidates: list[dict] | None = None, desired_top_k: int = 2,
) -> tuple[
    list[dict], list[SourceMetadata], list[SourceMetadata],
    list[SourceMetadata], list[SourceMetadata], bool,
]:
    """Return admitted docs plus raw, rejected, refill, admitted metadata and refill status."""
    raw: list[SourceMetadata] = []
    rejected: list[SourceMetadata] = []
    admitted_docs: list[dict] = []
    seen: set[str] = set()
    refill_metadata: list[SourceMetadata] = []
    for doc in candidates:
        accepted = _eligible(doc, request, config)
        raw.append(source_metadata(doc, accepted))
        seen.add(doc["source_id"])
        if accepted:
            admitted_docs.append(doc)
        else:
            rejected.append(source_metadata(doc, False))
    refilled = False
    if rejected and len(admitted_docs) < desired_top_k:
        for doc in refill_candidates or []:
            if doc["source_id"] in seen or not _eligible(doc, request, config):
                continue
            admitted_docs.append(doc)
            refill_metadata.append(source_metadata(doc, True))
            seen.add(doc["source_id"])
            refilled = True
            if len(admitted_docs) >= desired_top_k:
                break
    admitted = [source_metadata(doc, True) for doc in admitted_docs]
    return admitted_docs, raw, rejected, refill_metadata, admitted, refilled

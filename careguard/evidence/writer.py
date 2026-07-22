from __future__ import annotations

import json
import os
import re
from pathlib import Path
from threading import Lock
from typing import Any

from careguard.models.schemas import EvidenceRecord

SECRET_KEY = re.compile(r"(api[_-]?key|authorization|secret|token|password)", re.I)
SECRET_VALUE = re.compile(
    r"(?i)(bearer\s+[a-z0-9._~+/-]+|sk-[a-z0-9_-]{8,}|"
    r"gh[pousr]_[a-z0-9]{12,}|xox[baprs]-[a-z0-9-]{12,}|"
    r"AIza[a-z0-9_-]{20,}|api[_-]?key\s*[:=]\s*[a-z0-9._-]{8,})"
)
_WRITE_LOCK = Lock()


def sanitize_for_evidence(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if SECRET_KEY.search(str(key)) else sanitize_for_evidence(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_for_evidence(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE.sub("[REDACTED]", value)
    return value


class EvidenceStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.directory.chmod(0o700)

    def path_for(self, run_id: str) -> Path:
        return self.directory / f"{run_id}.jsonl"

    def write(self, record: EvidenceRecord) -> Path:
        path = self.path_for(record.run_id)
        payload = sanitize_for_evidence(record.model_dump(mode="json"))
        with _WRITE_LOCK:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            path.chmod(0o600)
        return path

    def read(self, run_id: str) -> list[EvidenceRecord]:
        path = self.path_for(run_id)
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            return [EvidenceRecord.model_validate(json.loads(line)) for line in handle if line.strip()]

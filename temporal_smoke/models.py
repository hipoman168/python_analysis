from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DayongJob:
    job_id: str
    project_key: str
    action: str
    authority_generation: int
    iwu_id: str
    payload: dict[str, Any]


@dataclass
class DayongResult:
    job_id: str
    state: str
    evidence: dict[str, Any]

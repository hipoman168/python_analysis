"""DAYONG Workforce API contract models (v0.1.0 draft). No production routes."""
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class Role(str, Enum):
    CEO = "CEO"
    D1 = "D1"
    D2 = "D2"
    WORKER = "WORKER"

class TaskState(str, Enum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVIEW_PENDING = "REVIEW_PENDING"

class Principal(BaseModel):
    agent_id: str
    role: Role
    scopes: list[str] = Field(default_factory=list)

class TaskRecord(BaseModel):
    task_id: str
    assigned_agent_id: str | None = None
    node_id: str | None = None
    state: TaskState = TaskState.PENDING
    created_at: datetime
    updated_at: datetime

class TaskEvent(BaseModel):
    event_id: str
    task_id: str
    actor_id: str
    event_type: str
    occurred_at: datetime
    details: dict[str, Any] = Field(default_factory=dict)

class EvidenceRecord(BaseModel):
    evidence_id: str
    task_id: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    storage_uri: str
    created_at: datetime
    producer_id: str

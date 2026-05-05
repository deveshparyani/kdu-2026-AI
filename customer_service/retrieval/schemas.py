from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SearchRecord(BaseModel):
    record_id: str
    title: str
    snippet: str
    source: str
    score: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, str] = Field(default_factory=dict)

    def compact_for_prompt(self, max_snippet_chars: int) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "title": self.title,
            "snippet": self.snippet[:max_snippet_chars].strip(),
            "source": self.source,
            "score": self.score,
            "metadata": self.metadata,
        }


class WorkerSearchResult(BaseModel):
    worker_name: Literal["db_agent", "vector_agent"]
    source_type: Literal["database", "vector"]
    status: Literal["success", "failed"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    records: list[SearchRecord] = Field(default_factory=list)
    error: Optional[str] = None
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime = Field(default_factory=utc_now)
    latency_ms: int = 0
    blocked_for_security: bool = False

    def compact_for_prompt(self, max_records: int, max_snippet_chars: int) -> dict[str, object]:
        return {
            "worker_name": self.worker_name,
            "source_type": self.source_type,
            "status": self.status,
            "confidence": self.confidence,
            "summary": self.summary[:200].strip(),
            "error": self.error,
            "records": [
                record.compact_for_prompt(max_snippet_chars=max_snippet_chars)
                for record in self.records[:max_records]
            ],
        }


class ConsensusOutput(BaseModel):
    final_answer: str
    decision_basis: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources_used: list[str] = Field(default_factory=list)
    degraded: bool = False
    can_answer: bool = True


class CoordinatorResult(BaseModel):
    trace_id: str
    query: str
    executed_in_parallel: bool
    db_result: WorkerSearchResult
    vector_result: WorkerSearchResult
    consensus: ConsensusOutput
    warnings: list[str] = Field(default_factory=list)

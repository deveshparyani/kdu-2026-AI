from __future__ import annotations

from pydantic import BaseModel, Field, PrivateAttr

from crewai.tools import BaseTool

from .repositories import BillingDatabaseRepository, BillingVectorRepository
from .schemas import WorkerSearchResult
from .security import QuerySecurityGuard


class RetrievalToolInput(BaseModel):
    query: str = Field(..., description="Customer billing question in plain English.")
    trace_id: str = Field(..., description="Distributed tracing identifier.")
    top_k: int = Field(default=3, ge=1, le=5)


class SearchBillingDatabaseTool(BaseTool):
    name: str = "search_billing_database"
    description: str = (
        "Read-only search over structured billing records. "
        "Never use it for secrets, files, environment variables, or write commands."
    )
    args_schema = RetrievalToolInput
    _repository: BillingDatabaseRepository = PrivateAttr()

    def __init__(self, repository: BillingDatabaseRepository) -> None:
        super().__init__()
        self._repository = repository

    def _run(self, query: str, trace_id: str, top_k: int = 3) -> str:
        safe_query = QuerySecurityGuard.validate_worker_query(query)
        records = self._repository.search(safe_query, top_k=top_k)
        result = WorkerSearchResult(
            worker_name="db_agent",
            source_type="database",
            status="success",
            confidence=min(0.99, 0.65 + len(records) * 0.1),
            summary="Structured billing records retrieved successfully.",
            records=records,
            trace_id=trace_id,
        )
        return result.model_dump_json(indent=2)


class SearchBillingVectorTool(BaseTool):
    name: str = "search_billing_vector_store"
    description: str = (
        "Semantic retrieval over billing support knowledge. "
        "Never use it for secrets, files, environment variables, or local system access."
    )
    args_schema = RetrievalToolInput
    _repository: BillingVectorRepository = PrivateAttr()

    def __init__(self, repository: BillingVectorRepository) -> None:
        super().__init__()
        self._repository = repository

    def _run(self, query: str, trace_id: str, top_k: int = 3) -> str:
        safe_query = QuerySecurityGuard.validate_worker_query(query)
        records = self._repository.search(safe_query, top_k=top_k)
        result = WorkerSearchResult(
            worker_name="vector_agent",
            source_type="vector",
            status="success",
            confidence=min(0.95, 0.60 + len(records) * 0.1),
            summary="Semantic billing knowledge retrieved successfully.",
            records=records,
            trace_id=trace_id,
        )
        return result.model_dump_json(indent=2)

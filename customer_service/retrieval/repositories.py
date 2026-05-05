from __future__ import annotations

from dataclasses import dataclass

from .schemas import SearchRecord


class UpstreamServiceError(RuntimeError):
    """Raised to simulate or surface upstream system failures."""


@dataclass(frozen=True)
class BillingDatabaseRepository:
    def search(self, query: str, top_k: int = 3) -> list[SearchRecord]:
        if "__force_db_error__" in query.lower():
            raise UpstreamServiceError("Simulated HTTP 500 from billing database.")

        data = [
            SearchRecord(
                record_id="inv-1024",
                title="Duplicate charge on May invoice",
                snippet="Customer was charged twice for invoice INV-1024 after a retry in the payment gateway.",
                source="billing_db",
                score=0.95,
                metadata={"issue_type": "duplicate_charge", "invoice_id": "INV-1024"},
            ),
            SearchRecord(
                record_id="inv-1040",
                title="Refund pending for accidental payment",
                snippet="Refund submitted and marked pending with estimated settlement in 5 business days.",
                source="billing_db",
                score=0.84,
                metadata={"issue_type": "refund_status", "invoice_id": "INV-1040"},
            ),
            SearchRecord(
                record_id="sub-208",
                title="Subscription changed mid-cycle",
                snippet="Proration was applied after upgrading from Starter to Pro during the billing cycle.",
                source="billing_db",
                score=0.79,
                metadata={"issue_type": "proration", "account_id": "sub-208"},
            ),
        ]
        return _rank_records(data, query, top_k)


@dataclass(frozen=True)
class BillingVectorRepository:
    def search(self, query: str, top_k: int = 3) -> list[SearchRecord]:
        if "__force_vector_error__" in query.lower():
            raise UpstreamServiceError("Simulated HTTP 500 from vector service.")

        data = [
            SearchRecord(
                record_id="kb-dup-charge",
                title="Knowledge article: duplicate charge troubleshooting",
                snippet="Duplicate charges often happen when a payment retry overlaps with a delayed gateway confirmation.",
                source="vector_store",
                score=0.91,
                metadata={"article_type": "knowledge_base"},
            ),
            SearchRecord(
                record_id="kb-refund",
                title="Knowledge article: refund timelines",
                snippet="Card refunds usually settle in 5 to 10 business days depending on the processor.",
                source="vector_store",
                score=0.81,
                metadata={"article_type": "knowledge_base"},
            ),
            SearchRecord(
                record_id="kb-proration",
                title="Knowledge article: plan change proration",
                snippet="Mid-cycle plan changes can add prorated line items to the next invoice.",
                source="vector_store",
                score=0.78,
                metadata={"article_type": "knowledge_base"},
            ),
        ]
        return _rank_records(data, query, top_k)


def _rank_records(records: list[SearchRecord], query: str, top_k: int) -> list[SearchRecord]:
    terms = {term.lower() for term in query.split()}
    scored: list[tuple[float, SearchRecord]] = []
    for record in records:
        haystack = f"{record.title} {record.snippet} {' '.join(record.metadata.values())}".lower()
        overlap = sum(1 for term in terms if term in haystack)
        adjusted = min(1.0, record.score + overlap * 0.02)
        scored.append((adjusted, record.model_copy(update={"score": adjusted})))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [record for _, record in scored[:top_k]]


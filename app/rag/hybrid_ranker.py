from langchain_core.documents import Document


def get_document_key(document: Document) -> str:
    """
    Create a stable key for a document chunk.

    We first try metadata fields. If they are not present, we fall back to the
    text itself.
    """
    metadata = document.metadata or {}

    chunk_id = metadata.get("chunk_id")
    if chunk_id:
        return str(chunk_id)

    source = metadata.get("source", "")
    page = metadata.get("page", "")
    text_start = document.page_content[:120]
    return f"{source}|{page}|{text_start}"


def rank_hybrid_results(
    semantic_results: list[Document],
    keyword_results: list[Document],
    top_k: int = 6,
    semantic_weight: float = 1.0,
    keyword_weight: float = 1.0,
    rrf_k: int = 60,
) -> list[Document]:
    """
    Merge semantic and keyword results using Reciprocal Rank Fusion (RRF).

    Why RRF:
    - semantic search and BM25 scores are different kinds of scores
    - rank positions are easier to combine than raw scores
    - this keeps the logic simple and reliable
    """
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")

    score_map: dict[str, float] = {}
    document_map: dict[str, Document] = {}

    for rank, document in enumerate(semantic_results, start=1):
        key = get_document_key(document)
        document_map[key] = document
        score_map[key] = score_map.get(key, 0.0) + (semantic_weight / (rrf_k + rank))

    for rank, document in enumerate(keyword_results, start=1):
        key = get_document_key(document)
        document_map[key] = document
        score_map[key] = score_map.get(key, 0.0) + (keyword_weight / (rrf_k + rank))

    ranked_items = sorted(
        score_map.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    final_documents: list[Document] = []
    for key, score in ranked_items[:top_k]:
        document = document_map[key]
        document.metadata = {
            **document.metadata,
            "hybrid_score": round(score, 6),
        }
        final_documents.append(document)

    return final_documents

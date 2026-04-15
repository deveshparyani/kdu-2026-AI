import json
from pathlib import Path

from langchain_core.documents import Document


DEFAULT_CHUNKS_PATH = "storage/chunks"


def get_chunks_directory(chunks_directory: str = DEFAULT_CHUNKS_PATH) -> str:
    """Create the chunks directory if needed and return its path."""
    path = Path(chunks_directory)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _make_chunk_file_path(
    collection_name: str,
    chunks_directory: str = DEFAULT_CHUNKS_PATH,
) -> Path:
    base_dir = Path(get_chunks_directory(chunks_directory))
    return base_dir / f"{collection_name}.json"


def save_documents_for_bm25(
    documents: list[Document],
    collection_name: str,
    chunks_directory: str = DEFAULT_CHUNKS_PATH,
) -> str:
    """Save chunk text and metadata so BM25 can be rebuilt later."""
    if not documents:
        raise ValueError("documents list is empty.")

    file_path = _make_chunk_file_path(
        collection_name=collection_name,
        chunks_directory=chunks_directory,
    )

    payload: list[dict[str, object]] = []
    for index, document in enumerate(documents, start=1):
        payload.append(
            {
                "page_content": document.page_content,
                "metadata": {
                    **document.metadata,
                    "chunk_number": index,
                },
            }
        )

    file_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return str(file_path)


def load_documents_for_bm25(
    collection_name: str,
    chunks_directory: str = DEFAULT_CHUNKS_PATH,
) -> list[Document]:
    """Load saved chunk data and convert it back into LangChain documents."""
    file_path = _make_chunk_file_path(
        collection_name=collection_name,
        chunks_directory=chunks_directory,
    )

    if not file_path.exists():
        raise ValueError(f"Chunk file not found: {file_path}")

    raw_items = json.loads(file_path.read_text(encoding="utf-8"))
    documents: list[Document] = []

    for item in raw_items:
        documents.append(
            Document(
                page_content=item["page_content"],
                metadata=item.get("metadata", {}),
            )
        )

    return documents

import re
from pathlib import Path
from urllib.parse import urlparse

from app.rag.chunk_store import save_documents_for_bm25
from app.rag.clean_text import clean_documents
from app.rag.load_data import is_url, load_source
from app.rag.text_splitter import split_documents
from app.rag.vector_store import create_chroma_vector_store


def make_collection_name(source: str) -> str:
    """Create a simple collection name from a URL or file path."""
    if is_url(source):
        parsed = urlparse(source)
        raw_name = f"{parsed.netloc}{parsed.path}".strip("/")
    else:
        raw_name = Path(source).stem

    cleaned_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw_name).strip("_")
    return cleaned_name or "rag_collection"


def index_source(
    source: str,
    collection_name: str | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    persist_directory: str = "storage/chroma",
) -> dict[str, object]:
    """Load, clean, split, and store a source in Chroma and BM25 storage."""
    final_collection_name = collection_name or make_collection_name(source)

    loaded_documents = load_source(source)
    cleaned_documents = clean_documents(loaded_documents)
    chunks = split_documents(
        cleaned_documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    vector_store = create_chroma_vector_store(
        documents=chunks,
        collection_name=final_collection_name,
        persist_directory=persist_directory,
    )
    chunks_file_path = save_documents_for_bm25(
        documents=chunks,
        collection_name=final_collection_name,
    )

    return {
        "source": source,
        "collection_name": final_collection_name,
        "loaded_documents": len(loaded_documents),
        "cleaned_documents": len(cleaned_documents),
        "chunks_created": len(chunks),
        "chroma_collection": vector_store._collection.name,
        "persist_directory": persist_directory,
        "chunks_file_path": chunks_file_path,
    }

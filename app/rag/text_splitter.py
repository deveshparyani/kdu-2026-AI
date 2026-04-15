from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_text_splitter(
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> RecursiveCharacterTextSplitter:
    """Create and return a text splitter with configurable values."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def split_documents(
    documents: list[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[Document]:
    """Split cleaned documents into smaller chunks."""
    if not documents:
        return []

    text_splitter = get_text_splitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    return text_splitter.split_documents(documents)

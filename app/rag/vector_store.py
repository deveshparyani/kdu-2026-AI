from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.rag.embeddings import DEFAULT_EMBEDDING_MODEL, get_embedding_model


DEFAULT_CHROMA_PATH = "storage/chroma"


def get_persist_directory(persist_directory: str = DEFAULT_CHROMA_PATH) -> str:
    """Create the Chroma storage folder if needed and return its path."""
    path = Path(persist_directory)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def create_chroma_vector_store(
    documents: list[Document],
    collection_name: str,
    persist_directory: str = DEFAULT_CHROMA_PATH,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> Chroma:
    """Create a local Chroma collection from documents."""
    if not documents:
        raise ValueError("documents list is empty.")

    embedding_model = get_embedding_model(model_name=model_name)
    persist_path = get_persist_directory(persist_directory)

    return Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        collection_name=collection_name,
        persist_directory=persist_path,
    )


def load_chroma_vector_store(
    collection_name: str,
    persist_directory: str = DEFAULT_CHROMA_PATH,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> Chroma:
    """Load an existing local Chroma collection."""
    embedding_model = get_embedding_model(model_name=model_name)
    persist_path = get_persist_directory(persist_directory)

    return Chroma(
        collection_name=collection_name,
        embedding_function=embedding_model,
        persist_directory=persist_path,
    )


def add_documents_to_chroma(
    vector_store: Chroma,
    documents: list[Document],
) -> None:
    """Add more documents to an existing Chroma collection."""
    if not documents:
        return

    vector_store.add_documents(documents)


def get_chroma_retriever(
    vector_store: Chroma,
    k: int = 4,
):
    """Return a retriever from the Chroma vector store."""
    return vector_store.as_retriever(
        search_kwargs={"k": k},
    )

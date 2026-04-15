from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_embedding_model(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> HuggingFaceEmbeddings:
    """Create the embedding model."""
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def embed_texts(
    texts: list[str],
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> list[list[float]]:
    """Convert text strings into embeddings."""
    if not texts:
        return []

    embedding_model = get_embedding_model(model_name=model_name)
    return embedding_model.embed_documents(texts)


def embed_documents(
    documents: list[Document],
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> list[list[float]]:
    """Convert LangChain documents into embeddings."""
    texts = [document.page_content for document in documents]
    return embed_texts(texts, model_name=model_name)

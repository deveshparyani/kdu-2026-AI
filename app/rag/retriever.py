from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.tools import tool

from app.rag.chunk_store import DEFAULT_CHUNKS_PATH, load_documents_for_bm25
from app.rag.hybrid_ranker import rank_hybrid_results
from app.rag.vector_store import DEFAULT_CHROMA_PATH, load_chroma_vector_store


def get_semantic_retriever(
    collection_name: str,
    persist_directory: str = DEFAULT_CHROMA_PATH,
    k: int = 4,
):
    """Load a Chroma collection and return its semantic retriever."""
    vector_store = load_chroma_vector_store(
        collection_name=collection_name,
        persist_directory=persist_directory,
    )
    return vector_store.as_retriever(search_kwargs={"k": k})


def get_bm25_retriever(
    collection_name: str,
    chunks_directory: str = DEFAULT_CHUNKS_PATH,
    k: int = 4,
) -> BM25Retriever:
    """Build a BM25 retriever from locally saved chunks."""
    documents = load_documents_for_bm25(
        collection_name=collection_name,
        chunks_directory=chunks_directory,
    )
    retriever = BM25Retriever.from_documents(documents)
    retriever.k = k
    return retriever


def semantic_search(
    query: str,
    collection_name: str,
    persist_directory: str = DEFAULT_CHROMA_PATH,
    k: int = 4,
) -> list[Document]:
    """Run semantic search using the Chroma collection."""
    retriever = get_semantic_retriever(
        collection_name=collection_name,
        persist_directory=persist_directory,
        k=k,
    )
    return retriever.invoke(query)


def keyword_search(
    query: str,
    collection_name: str,
    chunks_directory: str = DEFAULT_CHUNKS_PATH,
    k: int = 4,
) -> list[Document]:
    """Run keyword search using BM25."""
    retriever = get_bm25_retriever(
        collection_name=collection_name,
        chunks_directory=chunks_directory,
        k=k,
    )
    return retriever.invoke(query)


def hybrid_retrieve(
    query: str,
    collection_name: str,
    persist_directory: str = DEFAULT_CHROMA_PATH,
    chunks_directory: str = DEFAULT_CHUNKS_PATH,
    semantic_k: int = 4,
    keyword_k: int = 4,
    final_k: int = 6,
) -> dict[str, list[Document]]:
    """Return results from both semantic and keyword retrieval."""
    semantic_results = semantic_search(
        query=query,
        collection_name=collection_name,
        persist_directory=persist_directory,
        k=semantic_k,
    )
    keyword_results = keyword_search(
        query=query,
        collection_name=collection_name,
        chunks_directory=chunks_directory,
        k=keyword_k,
    )
    final_results = rank_hybrid_results(
        semantic_results=semantic_results,
        keyword_results=keyword_results,
        top_k=final_k,
    )

    return {
        "semantic_results": semantic_results,
        "keyword_results": keyword_results,
        "final_results": final_results,
    }


def _format_documents(documents: list[Document]) -> list[dict[str, object]]:
    formatted_documents: list[dict[str, object]] = []
    for document in documents:
        formatted_documents.append(
            {
                "text": document.page_content,
                "metadata": document.metadata,
            }
        )
    return formatted_documents


def retrieve_context(
    query: str,
    collection_name: str,
    persist_directory: str = DEFAULT_CHROMA_PATH,
    chunks_directory: str = DEFAULT_CHUNKS_PATH,
    semantic_k: int = 4,
    keyword_k: int = 4,
    final_k: int = 6,
) -> dict[str, list[dict[str, object]]]:
    """
    Tool-friendly retrieval function.

    This returns plain dictionaries so it can be passed around more easily later
    by a chat node or an API layer.
    """
    results = hybrid_retrieve(
        query=query,
        collection_name=collection_name,
        persist_directory=persist_directory,
        chunks_directory=chunks_directory,
        semantic_k=semantic_k,
        keyword_k=keyword_k,
        final_k=final_k,
    )

    return {
        "semantic_results": _format_documents(results["semantic_results"]),
        "keyword_results": _format_documents(results["keyword_results"]),
        "final_results": _format_documents(results["final_results"]),
    }


@tool
def retrieval_tool(
    query: str,
    collection_name: str,
    persist_directory: str = DEFAULT_CHROMA_PATH,
    chunks_directory: str = DEFAULT_CHUNKS_PATH,
    semantic_k: int = 4,
    keyword_k: int = 4,
    final_k: int = 6,
) -> dict[str, list[dict[str, object]]]:
    """Retrieve context using both Chroma semantic search and BM25 keyword search."""
    return retrieve_context(
        query=query,
        collection_name=collection_name,
        persist_directory=persist_directory,
        chunks_directory=chunks_directory,
        semantic_k=semantic_k,
        keyword_k=keyword_k,
        final_k=final_k,
    )

import os

from dotenv import load_dotenv
from openai import OpenAI

from app.rag.retriever import retrieve_context
from app.rag.vector_store import DEFAULT_CHROMA_PATH
from app.rag.chunk_store import DEFAULT_CHUNKS_PATH


load_dotenv()


def _resolve_default_groq_model() -> str:
    groq_model = os.getenv("GROQ_MODEL")
    if groq_model:
        return groq_model

    llm_model = os.getenv("LLM_MODEL", "").strip()
    if llm_model and not llm_model.lower().startswith("grok"):
        return llm_model

    return "llama-3.1-8b-instant"


DEFAULT_GROQ_MODEL = _resolve_default_groq_model()
DEFAULT_GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")


def get_groq_client() -> OpenAI:
    """Create the Groq client using environment variables."""
    api_key = (
        os.getenv("GROQ_API_KEY")
        or os.getenv("GROK_API_KEY")
        or os.getenv("XAI_API_KEY")
    )

    if not api_key:
        raise ValueError(
            "Add GROQ_API_KEY to your .env file. "
            "GROK_API_KEY and XAI_API_KEY are also accepted as fallbacks."
        )

    return OpenAI(
        api_key=api_key,
        base_url=DEFAULT_GROQ_BASE_URL,
    )


def build_context(final_results: list[dict[str, object]]) -> str:
    """Convert retrieved chunks into one context string for the LLM."""
    context_parts: list[str] = []

    for index, item in enumerate(final_results, start=1):
        text = str(item.get("text", "")).strip()
        metadata = item.get("metadata", {})
        source = ""

        if isinstance(metadata, dict):
            source = str(metadata.get("source", "unknown"))

        context_parts.append(
            f"Chunk {index}\nSource: {source}\nText: {text}"
        )

    return "\n\n".join(context_parts)


def build_messages(query: str, context: str) -> list[dict[str, str]]:
    """Build the messages sent to Groq."""
    system_message = (
        "You are a helpful RAG assistant. "
        "Answer only from the provided context. "
        "If the answer is not clearly in the context, say you could not find it. "
        "Keep the answer clear and simple. "
        "At the end, mention which chunk numbers were most useful."
    )

    user_message = (
        f"Question:\n{query}\n\n"
        f"Context:\n{context}"
    )

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]


def generate_answer_from_context(
    query: str,
    final_results: list[dict[str, object]],
    model_name: str | None = None,
) -> str:
    """Generate an answer from already retrieved context."""
    if not final_results:
        return "I could not find relevant context to answer the question."

    client = get_groq_client()
    context = build_context(final_results)
    messages = build_messages(query=query, context=context)
    resolved_model_name = model_name or DEFAULT_GROQ_MODEL

    response = client.chat.completions.create(
        model=resolved_model_name,
        messages=messages,
        temperature=0.2,
    )

    return response.choices[0].message.content or "No answer was returned."


def answer_question(
    query: str,
    collection_name: str,
    persist_directory: str = DEFAULT_CHROMA_PATH,
    chunks_directory: str = DEFAULT_CHUNKS_PATH,
    semantic_k: int = 4,
    keyword_k: int = 4,
    final_k: int = 6,
    model_name: str | None = None,
) -> dict[str, object]:
    """
    Full RAG answer step.

    1. retrieve context
    2. take final merged results
    3. send them to Groq
    4. return answer and sources
    """
    retrieval_result = retrieve_context(
        query=query,
        collection_name=collection_name,
        persist_directory=persist_directory,
        chunks_directory=chunks_directory,
        semantic_k=semantic_k,
        keyword_k=keyword_k,
        final_k=final_k,
    )

    final_results = retrieval_result["final_results"]
    answer = generate_answer_from_context(
        query=query,
        final_results=final_results,
        model_name=model_name,
    )

    return {
        "query": query,
        "answer": answer,
        "sources": final_results,
        "semantic_results": retrieval_result["semantic_results"],
        "keyword_results": retrieval_result["keyword_results"],
    }

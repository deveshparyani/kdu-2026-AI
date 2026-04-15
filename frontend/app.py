import httpx
import streamlit as st

from frontend.api_client import (
    DEFAULT_API_BASE_URL,
    ask_question_api,
    check_health,
    ingest_pdf_source,
    ingest_url_source,
)
from frontend.state import init_state


st.set_page_config(
    page_title="KDU AI RAG",
    page_icon="📚",
    layout="wide",
)


def render_sources(sources: list[dict[str, object]]) -> None:
    if not sources:
        st.info("No sources returned.")
        return

    for index, item in enumerate(sources, start=1):
        metadata = item.get("metadata", {})
        source = metadata.get("source", "unknown") if isinstance(metadata, dict) else "unknown"
        score = metadata.get("hybrid_score", "n/a") if isinstance(metadata, dict) else "n/a"
        text = str(item.get("text", "")).strip()

        with st.expander(f"Source {index} | score={score}"):
            st.caption(f"Source: {source}")
            st.write(text)


def render_chat_history() -> None:
    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            sources = item.get("sources")
            if sources:
                render_sources(sources)


def main() -> None:
    init_state()

    st.title("KDU AI RAG")
    st.caption("Upload a PDF or enter a blog URL, index it, and chat with the content.")

    with st.sidebar:
        st.subheader("Backend")
        api_base_url = st.text_input("API Base URL", value=DEFAULT_API_BASE_URL)

        health_placeholder = st.empty()
        if st.button("Check API Health", use_container_width=True):
            try:
                health = check_health(api_base_url=api_base_url)
                health_placeholder.success(f"API is healthy: {health['status']}")
            except Exception as exc:
                health_placeholder.error(f"Health check failed: {exc}")

        st.divider()
        st.subheader("Retrieval Settings")
        chunk_size = st.number_input("Chunk Size", min_value=100, max_value=4000, value=800, step=100)
        chunk_overlap = st.number_input("Chunk Overlap", min_value=0, max_value=1000, value=100, step=10)
        semantic_k = st.number_input("Semantic Top K", min_value=1, max_value=20, value=4, step=1)
        keyword_k = st.number_input("Keyword Top K", min_value=1, max_value=20, value=4, step=1)
        final_k = st.number_input("Final Top K", min_value=1, max_value=20, value=6, step=1)
        model_name = st.text_input("Groq Model", value="llama-3.1-8b-instant")

    left_col, right_col = st.columns([1, 1.2], gap="large")

    with left_col:
        st.subheader("1. Index Content")
        input_mode = st.radio("Choose Input Type", ["Blog URL", "PDF Upload"], horizontal=True)
        collection_name = st.text_input(
            "Collection Name (Optional)",
            value=st.session_state.collection_name,
            placeholder="Leave empty to auto-generate",
        )

        if input_mode == "Blog URL":
            source_url = st.text_input(
                "Blog URL",
                placeholder="https://example.com/article",
            )
            if st.button("Index URL", type="primary", use_container_width=True):
                if not source_url.strip():
                    st.error("Please enter a URL first.")
                else:
                    try:
                        with st.spinner("Indexing URL..."):
                            result = ingest_url_source(
                                source=source_url.strip(),
                                collection_name=collection_name.strip() or None,
                                chunk_size=int(chunk_size),
                                chunk_overlap=int(chunk_overlap),
                                api_base_url=api_base_url,
                            )
                        st.session_state.collection_name = result["collection_name"]
                        st.session_state.last_ingest_result = result
                        st.success("URL indexed successfully.")
                    except httpx.HTTPStatusError as exc:
                        detail = exc.response.text
                        st.error(f"API error: {detail}")
                    except Exception as exc:
                        st.error(f"Indexing failed: {exc}")
        else:
            uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"])
            if st.button("Index PDF", type="primary", use_container_width=True):
                if uploaded_pdf is None:
                    st.error("Please upload a PDF first.")
                else:
                    try:
                        with st.spinner("Uploading and indexing PDF..."):
                            result = ingest_pdf_source(
                                file_name=uploaded_pdf.name,
                                file_bytes=uploaded_pdf.getvalue(),
                                collection_name=collection_name.strip() or None,
                                chunk_size=int(chunk_size),
                                chunk_overlap=int(chunk_overlap),
                                api_base_url=api_base_url,
                            )
                        st.session_state.collection_name = result["collection_name"]
                        st.session_state.last_ingest_result = result
                        st.success("PDF indexed successfully.")
                    except httpx.HTTPStatusError as exc:
                        detail = exc.response.text
                        st.error(f"API error: {detail}")
                    except Exception as exc:
                        st.error(f"Indexing failed: {exc}")

        if st.session_state.last_ingest_result:
            st.divider()
            st.subheader("Latest Indexing Result")
            result = st.session_state.last_ingest_result
            st.json(result)

    with right_col:
        st.subheader("2. Chat With Your Content")
        active_collection = st.session_state.collection_name

        if active_collection:
            st.caption(f"Active collection: `{active_collection}`")
        else:
            st.info("Index a URL or PDF first to start chatting.")

        render_chat_history()

        prompt = st.chat_input("Ask a question about your indexed content")
        if prompt:
            if not active_collection:
                st.error("Please index content before asking a question.")
                return

            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            try:
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        result = ask_question_api(
                            query=prompt,
                            collection_name=active_collection,
                            semantic_k=int(semantic_k),
                            keyword_k=int(keyword_k),
                            final_k=int(final_k),
                            model_name=model_name.strip() or None,
                            api_base_url=api_base_url,
                        )
                    st.markdown(result["answer"])
                    render_sources(result["sources"])

                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result["sources"],
                    }
                )
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text
                st.error(f"API error: {detail}")
            except Exception as exc:
                st.error(f"Question failed: {exc}")


if __name__ == "__main__":
    main()

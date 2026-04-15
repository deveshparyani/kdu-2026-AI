# KDU AI RAG Chatbot

Starter scaffold for a multi-user RAG chatbot with:

- `FastAPI` backend
- `Streamlit` frontend
- `FAISS` for semantic retrieval
- `BM25` for keyword retrieval
- `Sentence Transformers` embeddings
- `LangGraph` for orchestration

## Project Structure

```text
kdu-ai/
├── backend/
│   └── app/
│       ├── api/
│       │   └── routes/
│       ├── core/
│       ├── graph/
│       ├── models/
│       └── services/
├── frontend/
│   ├── app.py
│   └── src/
│       ├── api/
│       ├── components/
│       └── state/
├── shared/
│   └── prompts/
├── storage/
│   ├── cache/
│   ├── documents/
│   └── indexes/
└── tests/
    ├── backend/
    └── frontend/
```

## Why this layout

- `api/routes`: HTTP endpoints for upload, chat, and health.
- `services`: pure application logic for loading, chunking, embedding, retrieval, and reranking.
- `graph`: LangGraph workflow assembly.
- `models`: request and response schemas.
- `frontend`: Streamlit UI and API client.
- `storage`: local development storage for uploaded files and per-session indexes.

## Multi-user strategy for MVP

Store each user's uploaded document data in a separate session namespace:

- `storage/documents/{session_id}/...`
- `storage/indexes/{session_id}/...`

Each chat request includes the `session_id`, and retrieval only loads that session's data.

## Suggested next steps

1. Implement upload ingestion in `backend/app/api/routes/ingest.py`
2. Implement session-scoped FAISS and BM25 stores
3. Build hybrid retrieval in `backend/app/services/retrieval.py`
4. Wire the LangGraph flow in `backend/app/graph/workflow.py`
5. Connect Streamlit to FastAPI

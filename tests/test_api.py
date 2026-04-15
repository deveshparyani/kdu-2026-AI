from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_endpoint(monkeypatch) -> None:
    def fake_index_source(**kwargs):
        return {
            "source": kwargs["source"],
            "collection_name": "demo_collection",
            "loaded_documents": 1,
            "cleaned_documents": 1,
            "chunks_created": 3,
            "chroma_collection": "demo_collection",
            "persist_directory": kwargs["persist_directory"],
            "chunks_file_path": "storage/chunks/demo_collection.json",
        }

    monkeypatch.setattr("api.main.index_source", fake_index_source)

    response = client.post(
        "/api/ingest",
        json={"source": "https://example.com/blog"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["collection_name"] == "demo_collection"
    assert data["chunks_created"] == 3


def test_ingest_pdf_endpoint(monkeypatch) -> None:
    def fake_index_source(**kwargs):
        return {
            "source": kwargs["source"],
            "collection_name": "pdf_collection",
            "loaded_documents": 1,
            "cleaned_documents": 1,
            "chunks_created": 2,
            "chroma_collection": "pdf_collection",
            "persist_directory": kwargs["persist_directory"],
            "chunks_file_path": "storage/chunks/pdf_collection.json",
        }

    monkeypatch.setattr("api.main.index_source", fake_index_source)

    response = client.post(
        "/api/ingest/pdf",
        data={"collection_name": "pdf_collection"},
        files={"file": ("demo.pdf", b"%PDF-1.4 test", "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["collection_name"] == "pdf_collection"
    assert data["chunks_created"] == 2


def test_retrieve_endpoint(monkeypatch) -> None:
    def fake_retrieve_context(**kwargs):
        return {
            "semantic_results": [{"text": "semantic chunk", "metadata": {"source": "demo"}}],
            "keyword_results": [{"text": "keyword chunk", "metadata": {"source": "demo"}}],
            "final_results": [{"text": "final chunk", "metadata": {"source": "demo"}}],
        }

    monkeypatch.setattr("api.main.retrieve_context", fake_retrieve_context)

    response = client.post(
        "/api/retrieve",
        json={"query": "What is this about?", "collection_name": "demo_collection"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["semantic_results"]) == 1
    assert len(data["keyword_results"]) == 1
    assert len(data["final_results"]) == 1


def test_ask_endpoint(monkeypatch) -> None:
    def fake_answer_question(**kwargs):
        return {
            "query": kwargs["query"],
            "answer": "This is a test answer.",
            "sources": [{"text": "final chunk", "metadata": {"source": "demo"}}],
            "semantic_results": [],
            "keyword_results": [],
        }

    monkeypatch.setattr("api.main.answer_question", fake_answer_question)

    response = client.post(
        "/api/ask",
        json={"query": "What is this about?", "collection_name": "demo_collection"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a test answer."
    assert len(data["sources"]) == 1

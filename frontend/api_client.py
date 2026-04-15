import os
from typing import Any

import httpx


DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def _build_url(path: str, api_base_url: str = DEFAULT_API_BASE_URL) -> str:
    return f"{api_base_url.rstrip('/')}{path}"


def check_health(api_base_url: str = DEFAULT_API_BASE_URL) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(_build_url("/health", api_base_url=api_base_url))
        response.raise_for_status()
        return response.json()


def ingest_url_source(
    *,
    source: str,
    collection_name: str | None,
    chunk_size: int,
    chunk_overlap: int,
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> dict[str, Any]:
    payload = {
        "source": source,
        "collection_name": collection_name or None,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            _build_url("/api/ingest", api_base_url=api_base_url),
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def ingest_pdf_source(
    *,
    file_name: str,
    file_bytes: bytes,
    collection_name: str | None,
    chunk_size: int,
    chunk_overlap: int,
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> dict[str, Any]:
    data = {
        "collection_name": collection_name or "",
        "chunk_size": str(chunk_size),
        "chunk_overlap": str(chunk_overlap),
    }
    files = {
        "file": (file_name, file_bytes, "application/pdf"),
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            _build_url("/api/ingest/pdf", api_base_url=api_base_url),
            data=data,
            files=files,
        )
        response.raise_for_status()
        return response.json()


def ask_question_api(
    *,
    query: str,
    collection_name: str,
    semantic_k: int,
    keyword_k: int,
    final_k: int,
    model_name: str | None,
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> dict[str, Any]:
    payload = {
        "query": query,
        "collection_name": collection_name,
        "semantic_k": semantic_k,
        "keyword_k": keyword_k,
        "final_k": final_k,
        "model_name": model_name or None,
    }
    with httpx.Client(timeout=180.0) as client:
        response = client.post(
            _build_url("/api/ask", api_base_url=api_base_url),
            json=payload,
        )
        response.raise_for_status()
        return response.json()

import os
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from api.schemas import AskRequest, IngestRequest, IngestResponse, RetrieveRequest
from app.rag.generate_answer import answer_question
from app.rag.pipeline import index_source
from app.rag.retriever import retrieve_context


app = FastAPI(title="KDU AI RAG API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest) -> dict[str, object]:
    try:
        return index_source(
            source=request.source,
            collection_name=request.collection_name,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            persist_directory=request.persist_directory,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/ingest/pdf", response_model=IngestResponse)
async def ingest_pdf(
    file: UploadFile = File(...),
    collection_name: str | None = Form(default=None),
    chunk_size: int = Form(default=800),
    chunk_overlap: int = Form(default=100),
    persist_directory: str = Form(default="storage/chroma"),
) -> dict[str, object]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    temp_file_path = ""
    try:
        file_bytes = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name

        return index_source(
            source=temp_file_path,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            persist_directory=persist_directory,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.post("/api/retrieve")
def retrieve(request: RetrieveRequest) -> dict[str, object]:
    try:
        return retrieve_context(
            query=request.query,
            collection_name=request.collection_name,
            persist_directory=request.persist_directory,
            chunks_directory=request.chunks_directory,
            semantic_k=request.semantic_k,
            keyword_k=request.keyword_k,
            final_k=request.final_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/ask")
def ask(request: AskRequest) -> dict[str, object]:
    try:
        return answer_question(
            query=request.query,
            collection_name=request.collection_name,
            persist_directory=request.persist_directory,
            chunks_directory=request.chunks_directory,
            semantic_k=request.semantic_k,
            keyword_k=request.keyword_k,
            final_k=request.final_k,
            model_name=request.model_name or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

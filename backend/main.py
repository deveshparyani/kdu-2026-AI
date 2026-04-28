"""FastAPI backend for accessibility platform."""

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

from src.accessibility_platform.chat.rag_chat import RAGChatService
from src.accessibility_platform.config import Config
from src.accessibility_platform.database.chat_db import ChatDatabase
from src.accessibility_platform.pipeline import ProcessingPipeline
from src.accessibility_platform.search.bm25_index import BM25Index
from src.accessibility_platform.search.hybrid_search import HybridSearchService
from src.accessibility_platform.vector_db.chroma_client import VectorDBClient

# Initialize FastAPI
app = FastAPI(title="Accessibility Platform API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
pipeline = ProcessingPipeline()
vector_db = VectorDBClient()
bm25_index = BM25Index()
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
search_service = HybridSearchService(vector_db, bm25_index, openai_client)
chat_db = ChatDatabase(Config.SQLITE_DB_PATH)
rag_service = RAGChatService(chat_db, search_service, openai_client)

# Upload directory
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# Request/Response models
class ChatRequest(BaseModel):
    conversation_id: str
    query: str


class ChatResponse(BaseModel):
    answer: str


class SearchRequest(BaseModel):
    query: str
    file_id: str = None
    top_k: int = 5


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Accessibility Platform API"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a file."""
    try:
        # Generate file ID
        file_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"Processing file: {file_path}")
        
        # Process file
        result = pipeline.process_file(str(file_path), file_id)
        
        print(f"Processing complete. Transcript length: {len(result['transcript'])}")
        print(f"Summary: {result['summary'][:100] if result['summary'] else 'None'}")
        
        # Index chunks for BM25
        if hasattr(pipeline, '_last_state') and pipeline._last_state.chunks:
            bm25_index.index_chunks(pipeline._last_state.chunks)
        
        return {
            "file_id": result["file_id"],
            "file_name": result["file_name"],
            "transcript": result["transcript"],
            "summary": result["summary"],
            "key_points": result["key_points"],
            "tags": result["tags"],
            "cost_summary": result["cost_summary"],
            "processing_time_seconds": result["processing_time_seconds"]
        }
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
def search(request: SearchRequest):
    """Search for relevant content."""
    try:
        results = search_service.search(
            query=request.query,
            top_k=request.top_k,
            file_filter=request.file_id
        )
        return {"results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/create")
def create_conversation():
    """Create a new conversation."""
    try:
        conversation_id = str(uuid.uuid4())
        chat_db.create_conversation(conversation_id)
        return {"conversation_id": conversation_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/message", response_model=ChatResponse)
def chat_message(request: ChatRequest):
    """Send a chat message and get response."""
    try:
        answer = rag_service.answer_question(
            conversation_id=request.conversation_id,
            query=request.query
        )
        return ChatResponse(answer=answer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/set-file")
def set_current_file(conversation_id: str, file_id: str):
    """Set the current file for a conversation."""
    try:
        chat_db.set_current_file(conversation_id, file_id)
        return {"status": "ok"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/history/{conversation_id}")
def get_chat_history(conversation_id: str, limit: int = 50):
    """Get chat history for a conversation."""
    try:
        history = chat_db.get_conversation_history(conversation_id, limit=limit)
        return {"history": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

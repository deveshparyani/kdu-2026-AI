from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.chat_service import ChatService, ChatServiceError
from api.service.streaming_chat_service import StreamingChatService


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)


class UsageSummary(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None = None


class ChatResponse(BaseModel):
    reply: str
    usage: UsageSummary


app = FastAPI(
    title="KDU OpenAI Chat API",
    description="FastAPI service for the separate Streamlit chatbot frontend.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_service = ChatService()
streaming_chat_service = StreamingChatService()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = chat_service.chat(
            messages=[message.model_dump() for message in request.messages]
        )
    except ChatServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(
            status_code=500,
            detail="Unable to process chat request.",
        ) from exc

    return ChatResponse(
        reply=result["reply"],
        usage=UsageSummary(**result["usage"]),
    )


@app.post("/chat/stream")
def stream_chat(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        streaming_chat_service.stream(
            messages=[message.model_dump() for message in request.messages]
        ),
        media_type="application/x-ndjson",
    )

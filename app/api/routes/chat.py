import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.assistant import run_assistant, stream_assistant_response


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return run_assistant(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# This function converts one stream event into SSE text format.
def format_sse_event(event_name: str, data: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"


# This function streams chat events so the frontend can show progress and chunks.
@router.post("/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    def event_generator():
        try:
            for event in stream_assistant_response(request):
                yield format_sse_event(event["event"], event["data"])
        except ValueError as exc:
            yield format_sse_event("error", {"message": str(exc)})
        except Exception as exc:
            yield format_sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

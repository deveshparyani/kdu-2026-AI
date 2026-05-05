"""Why this file exists: it creates the FastAPI app and real chat routes."""

import asyncio

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .auth import get_authenticated_user
from .chatkit_server import (
    create_chatkit_client_secret,
    generate_travel_assistant_text,
)
from .config import Settings, get_settings
from .db import (
    append_hidden_action_event,
    append_thread_message,
    build_action_scope_key,
    create_thread_for_user,
    get_action_response_by_scope_key,
    get_thread,
    list_thread_messages,
    list_threads_for_user,
    save_action_response,
    save_session,
    update_thread_mode,
)
from .models import (
    ActionRequest,
    ActionResponse,
    ChatRequest,
    ChatResponse,
    ChatResponseEvent,
    DebugCreateThreadResponse,
    DemoUser,
    SessionRequest,
    SessionResponse,
    ThreadHandoffResponse,
    ThreadListItem,
    ThreadListResponse,
    ThreadModeResponse,
    WidgetEvent,
)
from .security import is_valid_thread_id
from .tools import (
    get_demo_widget_by_id,
    looks_like_travel_request,
    search_demo_travel_offers,
    split_text_for_stream,
)
from .widgets import BOOK_NOW_ACTION_TYPE


def get_owned_thread_or_error(*, thread_id: str, user_id: str):
    """
    Return a thread only if the authenticated user owns it.

    Security choice:
    This shared helper keeps the IDOR protection in one place so session
    routes, chat routes, widget actions, and handoff routes all enforce the
    same ownership rule.
    """

    if not is_valid_thread_id(thread_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid thread_id format.",
        )

    thread = get_thread(thread_id)
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found.",
        )

    if thread.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have access to this thread. "
                "This check prevents cross-user thread access."
            ),
        )

    return thread


def ensure_thread_has_welcome_message(thread_id: str) -> None:
    """Seed a new thread with one assistant welcome message."""

    if list_thread_messages(thread_id):
        return

    append_thread_message(
        thread_id=thread_id,
        role="assistant",
        content=(
            "Hi! I am your travel booking assistant. Ask me about destinations, "
            "weekend trips, budgets, flights, or hotels."
        ),
    )


def build_assistant_turn(
    *,
    thread,
    user_message: str,
    settings: Settings,
):
    """
    Save the user message, generate one assistant response, and store it.

    This helper is shared by both the normal message endpoint and the streaming
    endpoint so the chat logic stays in one place.
    """

    append_thread_message(
        thread_id=thread.thread_id,
        role="user",
        content=user_message,
    )

    if thread.mode == "human":
        assistant_text = (
            "A human agent has taken over this conversation. "
            "AI responses are paused."
        )
        widgets = []
    else:
        widgets = (
            search_demo_travel_offers(user_message)
            if looks_like_travel_request(user_message)
            else []
        )
        assistant_text = generate_travel_assistant_text(
            user_message=user_message,
            recent_messages=list_thread_messages(thread.thread_id),
            widgets=widgets,
            settings=settings,
        )

    return append_thread_message(
        thread_id=thread.thread_id,
        role="assistant",
        content=assistant_text,
        widgets=widgets,
    )


def create_app() -> FastAPI:
    """Build the FastAPI application."""

    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_origin,
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Tiny health endpoint used for demos and quick checks."""

        return {"status": "ok"}

    @app.post("/api/chat/session", response_model=SessionResponse)
    async def create_chat_session(
        request: SessionRequest,
        user: DemoUser = Depends(get_authenticated_user),
        app_settings: Settings = Depends(get_settings),
    ) -> SessionResponse:
        """
        Create or continue a chat session for the authenticated user.

        Security choice:
        If a thread id is provided, the backend checks ownership before using it.
        This is what prevents IDOR / cross-user thread access.
        """

        if request.thread_id is None:
            thread = create_thread_for_user(user.user_id)
            ensure_thread_has_welcome_message(thread.thread_id)
        else:
            thread = get_owned_thread_or_error(
                thread_id=request.thread_id,
                user_id=user.user_id,
            )

        client_secret, provider = create_chatkit_client_secret(
            user_id=user.user_id,
            thread_id=thread.thread_id,
        )

        save_session(
            client_secret=client_secret,
            thread_id=thread.thread_id,
            user_id=user.user_id,
            model=app_settings.openai_model,
            provider=provider,
        )

        return SessionResponse(
            client_secret=client_secret,
            thread_id=thread.thread_id,
            user_id=user.user_id,
            mode=thread.mode,
            messages=list_thread_messages(thread.thread_id),
        )

    @app.post("/api/chat/message", response_model=ChatResponse)
    async def send_chat_message(
        request: ChatRequest,
        user: DemoUser = Depends(get_authenticated_user),
        app_settings: Settings = Depends(get_settings),
    ) -> ChatResponse:
        """
        Return one assistant reply that the frontend can render in the chat.

        If the thread is in `human` mode, the backend does not call the AI
        helper. It returns a pause message instead.
        """

        thread = get_owned_thread_or_error(
            thread_id=request.thread_id,
            user_id=user.user_id,
        )
        assistant_message = build_assistant_turn(
            thread=thread,
            user_message=request.message.strip(),
            settings=app_settings,
        )

        return ChatResponse(
            thread_id=thread.thread_id,
            mode=thread.mode,
            assistant_message=assistant_message,
        )

    @app.post("/api/chat/stream")
    async def stream_chat_message(
        request: ChatRequest,
        user: DemoUser = Depends(get_authenticated_user),
        app_settings: Settings = Depends(get_settings),
    ) -> StreamingResponse:
        """
        Stream assistant output as simple SSE events.

        This mimics real-time behavior in a beginner-friendly way. If you later
        switch to official ChatKit events or provider-native streaming, this is
        the place where that transport can be replaced.
        """

        thread = get_owned_thread_or_error(
            thread_id=request.thread_id,
            user_id=user.user_id,
        )
        assistant_message = build_assistant_turn(
            thread=thread,
            user_message=request.message.strip(),
            settings=app_settings,
        )

        async def event_generator():
            for chunk in split_text_for_stream(assistant_message.content):
                event = ChatResponseEvent(type="assistant_delta", text=chunk)
                yield f"data: {event.model_dump_json()}\n\n"
                await asyncio.sleep(0.04)

            for widget in assistant_message.widgets:
                widget_event = WidgetEvent(widget=widget)
                yield f"data: {widget_event.model_dump_json()}\n\n"
                await asyncio.sleep(0.03)

            done_event = ChatResponseEvent(type="done")
            yield f"data: {done_event.model_dump_json()}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    @app.get("/api/threads", response_model=ThreadListResponse)
    async def get_threads(
        user: DemoUser = Depends(get_authenticated_user),
    ) -> ThreadListResponse:
        """Return only threads owned by the authenticated user."""

        threads = list_threads_for_user(user.user_id)
        return ThreadListResponse(
            threads=[
                ThreadListItem(
                    thread_id=thread.thread_id,
                    user_id=thread.user_id,
                    created_at=thread.created_at,
                    mode=thread.mode,
                )
                for thread in threads
            ]
        )

    @app.post("/api/debug/create-thread", response_model=DebugCreateThreadResponse)
    async def debug_create_thread(
        user: DemoUser = Depends(get_authenticated_user),
    ) -> DebugCreateThreadResponse:
        """
        Demo-only helper route for testing ownership behavior quickly.

        Security choice:
        We label this route as debug-only because production systems should not
        expose extra thread-creation shortcuts without a clear product need.
        """

        thread = create_thread_for_user(user.user_id)
        ensure_thread_has_welcome_message(thread.thread_id)
        return DebugCreateThreadResponse(
            thread_id=thread.thread_id,
            user_id=thread.user_id,
            mode=thread.mode,
        )

    @app.post("/api/chat/action", response_model=ActionResponse)
    async def handle_chat_action(
        request: ActionRequest,
        user: DemoUser = Depends(get_authenticated_user),
    ) -> ActionResponse:
        """
        Receive a hidden widget action from the frontend.

        Security choice:
        This is not a visible user chat message. It is a hidden event generated
        by a widget button, so the backend must re-check thread ownership,
        action type, widget id, and payload before doing anything.
        """

        thread = get_owned_thread_or_error(
            thread_id=request.thread_id,
            user_id=user.user_id,
        )

        if request.action_type != BOOK_NOW_ACTION_TYPE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported action type.",
            )

        widget = get_demo_widget_by_id(request.widget_id)
        if widget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget not found.",
            )

        if request.payload.offer_id != request.widget_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload offer_id does not match widget_id.",
            )

        expected_action = widget.actions[0]
        if expected_action.type != request.action_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Widget action does not match the server definition.",
            )

        if expected_action.payload.offer_id != request.payload.offer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action payload does not match the server definition.",
            )

        scope_key = build_action_scope_key(
            user_id=user.user_id,
            thread_id=request.thread_id,
            widget_id=request.widget_id,
            action_type=request.action_type,
            idempotency_key=request.idempotency_key,
        )

        existing_response = get_action_response_by_scope_key(scope_key)
        if existing_response is not None:
            return existing_response

        append_hidden_action_event(
            thread_id=thread.thread_id,
            action_type=request.action_type,
            widget_id=request.widget_id,
            payload=request.payload,
        )

        assistant_message = append_thread_message(
            thread_id=thread.thread_id,
            role="assistant",
            content=f"Great, I started the booking flow for {widget.title}.",
        )

        return save_action_response(
            scope_key=scope_key,
            user_id=user.user_id,
            thread_id=request.thread_id,
            widget_id=request.widget_id,
            action_type=request.action_type,
            idempotency_key=request.idempotency_key,
            message=f"Booking started for {request.payload.offer_id}",
            assistant_message=assistant_message,
        )

    @app.get("/api/threads/{thread_id}/mode", response_model=ThreadModeResponse)
    async def get_thread_mode(
        thread_id: str,
        user: DemoUser = Depends(get_authenticated_user),
    ) -> ThreadModeResponse:
        """Return the current mode for one owned thread."""

        thread = get_owned_thread_or_error(
            thread_id=thread_id,
            user_id=user.user_id,
        )
        return ThreadModeResponse(mode=thread.mode)

    @app.post(
        "/api/threads/{thread_id}/handoff/start",
        response_model=ThreadHandoffResponse,
    )
    async def start_human_handoff(
        thread_id: str,
        user: DemoUser = Depends(get_authenticated_user),
    ) -> ThreadHandoffResponse:
        """
        Pause AI responses for one owned thread.

        This is a beginner-friendly hook. A production system would usually
        also notify a human support dashboard or queue.
        """

        _ = get_owned_thread_or_error(
            thread_id=thread_id,
            user_id=user.user_id,
        )
        thread = update_thread_mode(thread_id=thread_id, mode="human")
        return ThreadHandoffResponse(
            mode=thread.mode,
            message="Human handoff started. AI responses are paused.",
        )

    @app.post(
        "/api/threads/{thread_id}/handoff/end",
        response_model=ThreadHandoffResponse,
    )
    async def end_human_handoff(
        thread_id: str,
        user: DemoUser = Depends(get_authenticated_user),
    ) -> ThreadHandoffResponse:
        """Resume AI responses for one owned thread."""

        _ = get_owned_thread_or_error(
            thread_id=thread_id,
            user_id=user.user_id,
        )
        thread = update_thread_mode(thread_id=thread_id, mode="ai")
        return ThreadHandoffResponse(
            mode=thread.mode,
            message="AI responses resumed.",
        )

    return app


app = create_app()

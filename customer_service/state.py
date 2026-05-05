from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationTurn(BaseModel):
    speaker: Literal["user", "assistant"]
    text: str
    interrupted: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class TriageOutput(BaseModel):
    intent: Literal["billing", "other"]
    confidence: float = Field(ge=0.0, le=1.0)
    routing_summary: str
    customer_sentiment: str
    entities: dict[str, str] = Field(default_factory=dict)


class BillingOutput(BaseModel):
    spoken_response: str
    resolution_summary: str
    requires_follow_up: bool = False
    account_action_required: bool = False

 
class HandoffPayload(BaseModel):
    session_id: str
    turn_id: int
    intent: str
    confidence: float
    latest_user_utterance: str
    conversation_summary: str
    entities: dict[str, str] = Field(default_factory=dict)
    trace_id: str
    estimated_tokens: int = 0


class CompactedConversation(BaseModel):
    recent_messages: list[dict[str, str]]
    conversation_summary: str
    estimated_tokens: int
    recent_turn_count: int
    compacted: bool


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    turn_count: int = 0
    rolling_summary: str = ""
    recent_turns: list[ConversationTurn] = Field(default_factory=list)
    last_handoff: Optional[HandoffPayload] = None

    def next_turn_id(self) -> int:
        self.turn_count += 1
        return self.turn_count

    def add_user_turn(self, text: str) -> None:
        self.recent_turns.append(ConversationTurn(speaker="user", text=text))
        self._prune_history()

    def add_assistant_turn(self, text: str, interrupted: bool = False) -> None:
        self.recent_turns.append(
            ConversationTurn(speaker="assistant", text=text, interrupted=interrupted)
        )
        self._prune_history()

    def mark_last_assistant_interrupted(self, heard_prefix: str) -> None:
        for turn in reversed(self.recent_turns):
            if turn.speaker == "assistant":
                turn.text = heard_prefix or turn.text[:80]
                turn.interrupted = True
                break

    def recent_messages(self, limit: int = 6, max_chars: int = 240) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for turn in self.recent_turns[-limit:]:
            messages.append({"role": turn.speaker, "content": turn.text[:max_chars].strip()})
        return messages

    def update_summary(self, max_summary_chars: int = 500, max_turn_chars: int = 180) -> None:
        recent = self.recent_turns[-6:]
        snippets = [f"{turn.speaker}: {turn.text[:max_turn_chars].strip()}" for turn in recent]
        summary = " | ".join(snippets)
        self.rolling_summary = summary[-max_summary_chars:]

    def context_summary(self, max_summary_chars: int = 500) -> str:
        self.update_summary(max_summary_chars=max_summary_chars)
        return self.rolling_summary or "No prior conversation context."

    def compacted_view(
        self,
        max_recent_turns: int,
        max_message_chars: int,
        max_summary_chars: int,
    ) -> CompactedConversation:
        summary = self.context_summary(max_summary_chars=max_summary_chars)
        recent = self.recent_messages(limit=max_recent_turns, max_chars=max_message_chars)
        estimated_chars = len(summary) + sum(len(message["content"]) for message in recent)
        return CompactedConversation(
            recent_messages=recent,
            conversation_summary=summary,
            estimated_tokens=max(1, estimated_chars // 4),
            recent_turn_count=len(recent),
            compacted=len(self.recent_turns) > max_recent_turns or len(summary) >= max_summary_chars,
        )

    def _prune_history(self, keep_last: int = 8) -> None:
        if len(self.recent_turns) <= keep_last:
            return
        removed = self.recent_turns[:-keep_last]
        self.recent_turns = self.recent_turns[-keep_last:]
        compact = " ".join(f"{turn.speaker}: {turn.text}" for turn in removed)
        merged = f"{self.rolling_summary} {compact}".strip()
        self.rolling_summary = merged[-900:]


class VoiceFlowState(BaseModel):
    pending_user_text: str = ""
    recent_messages: list[dict[str, str]] = Field(default_factory=list)
    conversation_summary: str = ""
    session_id: str = ""
    turn_id: int = 0
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    triage_output: Optional[TriageOutput] = None
    handoff_payload: Optional[HandoffPayload] = None
    billing_output: Optional[BillingOutput] = None
    final_spoken_text: str = ""


def truncate_text_by_ratio(text: str, ratio: float) -> str:
    if not text:
        return ""
    safe_ratio = max(0.0, min(1.0, ratio))
    if safe_ratio <= 0:
        return ""
    cutoff = max(1, int(len(text) * safe_ratio))
    return text[:cutoff].rstrip()

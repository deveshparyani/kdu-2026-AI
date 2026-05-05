from __future__ import annotations

from crewai.flow.flow import Flow, listen, start

from .agents import VoiceAgents
from .logging_utils import StructuredLogger
from .state import BillingOutput, HandoffPayload, TriageOutput, VoiceFlowState


class VoiceHandoffFlow(Flow[VoiceFlowState]):
    def __init__(self, agents: VoiceAgents, logger: StructuredLogger) -> None:
        super().__init__()
        self._agents = agents
        self._logger = logger

    @start()
    def triage_turn(self) -> str:
        prompt = self._build_triage_prompt()
        result = self._agents.triage.kickoff(prompt, response_format=TriageOutput)
        triage = result.pydantic
        if triage is None:
            raise RuntimeError("Triage agent did not return structured output.")

        self.state.triage_output = triage
        self.state.handoff_payload = HandoffPayload(
            session_id=self.state.session_id,
            turn_id=self.state.turn_id,
            intent=triage.intent,
            confidence=triage.confidence,
            latest_user_utterance=self.state.pending_user_text,
            conversation_summary=self.state.conversation_summary,
            entities=triage.entities,
            trace_id=self.state.trace_id,
            estimated_tokens=max(
                1,
                (
                    len(self.state.pending_user_text)
                    + len(self.state.conversation_summary)
                    + sum(len(str(message)) for message in self.state.recent_messages)
                )
                // 4,
            ),
        )
        self._logger.emit(
            "handoff_created",
            trace_id=self.state.trace_id,
            handoff=self.state.handoff_payload.model_dump(),
        )
        return triage.intent

    @listen(triage_turn)
    def billing_turn(self, intent: str) -> str:
        if intent != "billing":
            self.state.final_spoken_text = (
                "I can help with that, but this phase one demo only routes billing questions. "
                "Please ask a billing-related question."
            )
            return self.state.final_spoken_text

        prompt = self._build_billing_prompt()
        result = self._agents.billing.kickoff(prompt, response_format=BillingOutput)
        billing = result.pydantic
        if billing is None:
            raise RuntimeError("Billing agent did not return structured output.")

        self.state.billing_output = billing
        self.state.final_spoken_text = billing.spoken_response
        return self.state.final_spoken_text

    def _build_triage_prompt(self) -> str:
        return f"""
You are the Triage Agent in a real-time voice customer service system.

Return structured output only.

Classify the user's intent as either:
- billing
- other

Extract simple entities when obvious, such as:
- billing_issue_type
- month
- invoice_reference

Conversation summary:
{self.state.conversation_summary}

Recent messages:
{self.state.recent_messages}

Latest user utterance:
{self.state.pending_user_text}
""".strip()

    def _build_billing_prompt(self) -> str:
        handoff = self.state.handoff_payload.model_dump() if self.state.handoff_payload else {}
        return f"""
You are the Billing Agent in a real-time voice customer service system.

Return structured output only.

Rules:
- Speak naturally for voice output.
- Keep the response short.
- Never invent account-specific facts.
- If key information is missing, ask one short clarifying question.
- Use the handoff state as the source of truth.

Handoff payload:
{handoff}

Recent messages:
{self.state.recent_messages}
""".strip()

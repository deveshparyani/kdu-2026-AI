from __future__ import annotations

from crewai import Agent

from .config import Settings


class VoiceAgents:
    def __init__(self, settings: Settings) -> None:
        self.triage = Agent(
            role="Customer Service Triage Agent",
            goal="Classify the user's intent and prepare a precise handoff for billing issues.",
            backstory=(
                "You are the first contact for a voice-based customer service system. "
                "You keep outputs short, structured, and safe for downstream handoff."
            ),
            llm=settings.agent_model,
            verbose=settings.verbose,
            allow_delegation=False,
        )

        self.billing = Agent(
            role="Billing Support Agent",
            goal="Resolve billing questions with short, spoken-friendly answers.",
            backstory=(
                "You are a calm billing specialist speaking to a customer over voice. "
                "You do not invent account details. If information is missing, you ask a short clarifying question."
            ),
            llm=settings.agent_model,
            verbose=settings.verbose,
            allow_delegation=False,
        )

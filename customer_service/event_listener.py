from __future__ import annotations

from crewai.events import (
    AgentExecutionCompletedEvent,
    AgentExecutionErrorEvent,
    AgentExecutionStartedEvent,
    BaseEventListener,
    CrewKickoffCompletedEvent,
    CrewKickoffFailedEvent,
    CrewKickoffStartedEvent,
    ToolUsageErrorEvent,
    ToolUsageFinishedEvent,
    ToolUsageStartedEvent,
)

from .logging_utils import StructuredLogger


class CrewMonitoringListener(BaseEventListener):
    def __init__(self, logger: StructuredLogger) -> None:
        self._logger = logger
        super().__init__()

    def setup_listeners(self, crewai_event_bus) -> None:  # type: ignore[override]
        @crewai_event_bus.on(AgentExecutionStartedEvent)
        def on_agent_started(source, event) -> None:
            self._logger.emit(
                "agent_started",
                role=getattr(getattr(event, "agent", None), "role", "unknown"),
                source=source.__class__.__name__,
            )

        @crewai_event_bus.on(AgentExecutionCompletedEvent)
        def on_agent_completed(source, event) -> None:
            self._logger.emit(
                "agent_completed",
                role=getattr(getattr(event, "agent", None), "role", "unknown"),
                source=source.__class__.__name__,
            )

        @crewai_event_bus.on(AgentExecutionErrorEvent)
        def on_agent_failed(source, event) -> None:
            self._logger.emit(
                "agent_failed",
                role=getattr(getattr(event, "agent", None), "role", "unknown"),
                source=source.__class__.__name__,
                error=str(getattr(event, "error", "unknown error")),
            )

        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def on_crew_started(source, event) -> None:
            self._logger.emit(
                "crew_started",
                source=source.__class__.__name__,
                crew_name=getattr(event, "crew_name", "unknown"),
            )

        @crewai_event_bus.on(CrewKickoffCompletedEvent)
        def on_crew_completed(source, event) -> None:
            self._logger.emit(
                "crew_completed",
                source=source.__class__.__name__,
                crew_name=getattr(event, "crew_name", "unknown"),
            )

        @crewai_event_bus.on(CrewKickoffFailedEvent)
        def on_crew_failed(source, event) -> None:
            self._logger.emit(
                "crew_failed",
                source=source.__class__.__name__,
                crew_name=getattr(event, "crew_name", "unknown"),
                error=str(getattr(event, "error", "unknown error")),
            )

        @crewai_event_bus.on(ToolUsageStartedEvent)
        def on_tool_started(source, event) -> None:
            self._logger.emit(
                "tool_started",
                source=source.__class__.__name__,
                tool_name=getattr(event, "tool_name", "unknown"),
            )

        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def on_tool_finished(source, event) -> None:
            self._logger.emit(
                "tool_finished",
                source=source.__class__.__name__,
                tool_name=getattr(event, "tool_name", "unknown"),
            )

        @crewai_event_bus.on(ToolUsageErrorEvent)
        def on_tool_error(source, event) -> None:
            self._logger.emit(
                "tool_error",
                source=source.__class__.__name__,
                tool_name=getattr(event, "tool_name", "unknown"),
                error=str(getattr(event, "error", "unknown error")),
            )

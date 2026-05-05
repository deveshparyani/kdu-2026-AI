from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Optional


class ReplayStore:
    def __init__(self, log_dir: Path) -> None:
        self._events_path = log_dir / "events.jsonl"

    def load_events(
        self,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if not self._events_path.exists():
            return []
        events: list[dict[str, Any]] = []
        with self._events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if session_id and record.get("session_id") != session_id:
                    continue
                if trace_id and record.get("trace_id") != trace_id:
                    continue
                events.append(record)
        return events

    def replay_text(
        self,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> str:
        events = self.load_events(session_id=session_id, trace_id=trace_id)
        if not events:
            return "No replay events found."
        return "\n".join(json.dumps(event, ensure_ascii=False, indent=2) for event in events)

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize(inner) for key, inner in value.items() if "api_key" not in key.lower()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Exception):
        return {"type": value.__class__.__name__, "message": str(value)}
    return value


class StructuredLogger:
    def __init__(self, log_dir: Path, verbose: bool = True) -> None:
        self._lock = threading.Lock()
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._events_path = self.log_dir / "events.jsonl"

        self._logger = logging.getLogger("customer_service")
        self._logger.setLevel(logging.INFO)
        self._logger.handlers.clear()
        self._logger.propagate = False

        formatter = logging.Formatter("%(message)s")
        if verbose:
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            self._logger.addHandler(console)

    def emit(self, event: str, **payload: Any) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **_sanitize(payload),
        }
        line = json.dumps(record, ensure_ascii=False)
        with self._lock:
            with self._events_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        self._logger.info(line)

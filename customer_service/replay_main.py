from __future__ import annotations

import os
import sys
from pathlib import Path

from .replay import ReplayStore


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(
            "Usage:\n"
            "  customer-service replay session <session_id>\n"
            "  customer-service replay trace <trace_id>"
    )

    scope = sys.argv[1].strip().lower()
    identifier = sys.argv[2].strip()
    store = ReplayStore(Path(os.getenv("APP_LOG_DIR", "logs")))

    if scope == "session":
        print(store.replay_text(session_id=identifier))
        return
    if scope == "trace":
        print(store.replay_text(trace_id=identifier))
        return
    raise SystemExit(f"Unknown replay scope: {scope}")

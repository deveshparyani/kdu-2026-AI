from __future__ import annotations

import sys

from .replay_main import main as replay_main
from .query import main as query_main
from .voice import main as voice_main


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage:\n"
            '  customer-service voice\n'
            '  customer-service query "Why was I charged twice this month?"\n'
            '  customer-service replay session <session_id>\n'
            '  customer-service replay trace <trace_id>'
        )

    command = sys.argv[1].strip().lower()
    sys.argv = [sys.argv[0], *sys.argv[2:]]

    if command == "voice":
        voice_main()
        return

    if command == "query":
        query_main()
        return

    if command == "replay":
        replay_main()
        return

    raise SystemExit(f"Unknown command: {command}")

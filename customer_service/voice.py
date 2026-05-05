from __future__ import annotations

from .agents import VoiceAgents
from .config import Settings
from .event_listener import CrewMonitoringListener
from .logging_utils import StructuredLogger
from .services.openai_audio import OpenAIAudioClient
from .audio.runtime import build_runtime


def main() -> None:
    settings = Settings.load()
    logger = StructuredLogger(settings.log_dir, verbose=settings.verbose)
    _listener = CrewMonitoringListener(logger)
    agents = VoiceAgents(settings)
    audio_client = OpenAIAudioClient(settings)
    runtime = build_runtime(settings, agents, audio_client, logger)
    runtime.run()


if __name__ == "__main__":
    main()

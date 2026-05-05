from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for environments without optional deps installed yet
    def load_dotenv() -> bool:
        return False


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None else default


def _env_optional(name: str) -> Optional[str]:
    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str
    agent_model: str
    transcribe_model: str
    tts_model: str
    tts_voice: str
    input_sample_rate: int
    output_sample_rate: int
    frame_ms: int
    preroll_ms: int
    min_speech_ms: int
    end_silence_ms: int
    interrupt_speech_ms: int
    max_turn_seconds: int
    vad_start_threshold: float
    vad_continue_threshold: float
    barge_in_threshold: float
    echo_gate_multiplier: float
    input_device: Optional[str]
    output_device: Optional[str]
    log_dir: Path
    verbose: bool
    retrieval_worker_timeout_seconds: float
    retrieval_max_results: int
    memory_max_recent_turns: int
    memory_max_message_chars: int
    memory_max_summary_chars: int
    retrieval_prompt_records: int
    retrieval_prompt_snippet_chars: int
    retrieval_skip_consensus_on_single_success: bool
    db_max_concurrency: int
    db_max_queue_size: int
    vector_max_concurrency: int
    vector_max_queue_size: int
    consensus_max_concurrency: int
    consensus_max_queue_size: int

    @property
    def frame_size(self) -> int:
        return int(self.input_sample_rate * (self.frame_ms / 1000))

    @property
    def preroll_frames(self) -> int:
        return max(1, self.preroll_ms // self.frame_ms)

    @property
    def start_speech_frames(self) -> int:
        return max(1, self.min_speech_ms // self.frame_ms)

    @property
    def end_silence_frames(self) -> int:
        return max(1, self.end_silence_ms // self.frame_ms)

    @property
    def interrupt_frames(self) -> int:
        return max(1, self.interrupt_speech_ms // self.frame_ms)

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required. Copy .env.example to .env and set it.")

        return cls(
            openai_api_key=api_key,
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            agent_model=os.getenv("AGENT_MODEL", "gpt-4o-mini"),
            transcribe_model=os.getenv("TRANSCRIBE_MODEL", "whisper-1"),
            tts_model=os.getenv("TTS_MODEL", "gpt-4o-mini-tts"),
            tts_voice=os.getenv("TTS_VOICE", "coral"),
            input_sample_rate=_env_int("VOICE_INPUT_SAMPLE_RATE", 16000),
            output_sample_rate=_env_int("VOICE_OUTPUT_SAMPLE_RATE", 24000),
            frame_ms=_env_int("VOICE_FRAME_MS", 20),
            preroll_ms=_env_int("VOICE_PREROLL_MS", 400),
            min_speech_ms=_env_int("VOICE_MIN_SPEECH_MS", 250),
            end_silence_ms=_env_int("VOICE_END_SILENCE_MS", 700),
            interrupt_speech_ms=_env_int("VOICE_INTERRUPT_SPEECH_MS", 320),
            max_turn_seconds=_env_int("VOICE_MAX_TURN_SECONDS", 15),
            vad_start_threshold=_env_float("VOICE_VAD_START_THRESHOLD", 0.018),
            vad_continue_threshold=_env_float("VOICE_VAD_CONTINUE_THRESHOLD", 0.012),
            barge_in_threshold=_env_float("VOICE_BARGE_IN_THRESHOLD", 0.035),
            echo_gate_multiplier=_env_float("VOICE_ECHO_GATE_MULTIPLIER", 1.8),
            input_device=_env_optional("VOICE_INPUT_DEVICE"),
            output_device=_env_optional("VOICE_OUTPUT_DEVICE"),
            log_dir=Path(os.getenv("APP_LOG_DIR", "logs")),
            verbose=_env_bool("APP_VERBOSE", True),
            retrieval_worker_timeout_seconds=_env_float("RETRIEVAL_WORKER_TIMEOUT_SECONDS", 12.0),
            retrieval_max_results=_env_int("RETRIEVAL_MAX_RESULTS", 3),
            memory_max_recent_turns=_env_int("MEMORY_MAX_RECENT_TURNS", 4),
            memory_max_message_chars=_env_int("MEMORY_MAX_MESSAGE_CHARS", 240),
            memory_max_summary_chars=_env_int("MEMORY_MAX_SUMMARY_CHARS", 500),
            retrieval_prompt_records=_env_int("RETRIEVAL_PROMPT_RECORDS", 2),
            retrieval_prompt_snippet_chars=_env_int("RETRIEVAL_PROMPT_SNIPPET_CHARS", 180),
            retrieval_skip_consensus_on_single_success=_env_bool("RETRIEVAL_SKIP_CONSENSUS_ON_SINGLE_SUCCESS", True),
            db_max_concurrency=_env_int("DB_MAX_CONCURRENCY", 10),
            db_max_queue_size=_env_int("DB_MAX_QUEUE_SIZE", 50),
            vector_max_concurrency=_env_int("VECTOR_MAX_CONCURRENCY", 20),
            vector_max_queue_size=_env_int("VECTOR_MAX_QUEUE_SIZE", 80),
            consensus_max_concurrency=_env_int("CONSENSUS_MAX_CONCURRENCY", 8),
            consensus_max_queue_size=_env_int("CONSENSUS_MAX_QUEUE_SIZE", 30),
        )

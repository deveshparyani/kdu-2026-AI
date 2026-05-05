from __future__ import annotations

import queue
import threading
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from ..config import Settings
from ..voice_flow import VoiceHandoffFlow
from ..logging_utils import StructuredLogger
from ..services.openai_audio import OpenAIAudioClient
from ..state import SessionState, truncate_text_by_ratio


def pcm_rms(pcm_bytes: bytes) -> float:
    if not pcm_bytes:
        return 0.0
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples / 32768.0))))


def float_frame_to_pcm16_bytes(frame: np.ndarray) -> bytes:
    mono = frame[:, 0] if frame.ndim > 1 else frame
    clipped = np.clip(mono, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    return pcm.tobytes()


class PCMFrameRingBuffer:
    def __init__(self, max_frames: int) -> None:
        self._frames: deque[bytes] = deque(maxlen=max_frames)

    def append(self, frame: bytes) -> None:
        self._frames.append(frame)

    def snapshot(self) -> list[bytes]:
        return list(self._frames)


@dataclass
class CompletedTurn:
    pcm_bytes: bytes
    interrupted_playback: bool


@dataclass
class PlaybackSnapshot:
    generation: int
    text: str
    produced_bytes: int = 0
    played_bytes: int = 0
    interrupted: bool = False

    @property
    def heard_ratio(self) -> float:
        if self.produced_bytes <= 0:
            return 0.0
        return min(1.0, self.played_bytes / self.produced_bytes)


@dataclass
class PlaybackChunk:
    generation: int
    data: bytes = b""
    is_end: bool = False


class SpeakerPlayer:
    def __init__(
        self,
        settings: Settings,
        logger: StructuredLogger,
        on_interrupted: Callable[[PlaybackSnapshot], None],
    ) -> None:
        self._settings = settings
        self._logger = logger
        self._on_interrupted = on_interrupted
        self._queue: queue.Queue[PlaybackChunk] = queue.Queue()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self._current_generation = 0
        self._speaking = False
        self._producer_cancel: Optional[threading.Event] = None
        self._snapshot: Optional[PlaybackSnapshot] = None
        self.last_output_rms = 0.0

        self._stream = sd.RawOutputStream(
            samplerate=settings.output_sample_rate,
            channels=1,
            dtype="int16",
            device=settings.output_device,
        )

    def start(self) -> None:
        self._stream.start()
        self._playback_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self.interrupt(reason="shutdown")
        self._queue.put(PlaybackChunk(generation=-1, is_end=True))
        self._playback_thread.join(timeout=2)
        self._stream.stop()
        self._stream.close()

    def is_speaking(self) -> bool:
        with self._lock:
            return self._speaking

    def speak(self, text: str, audio_stream: Iterable[bytes]) -> int:
        self.interrupt(reason="new_playback")
        with self._lock:
            self._current_generation += 1
            generation = self._current_generation
            self._speaking = True
            self._producer_cancel = threading.Event()
            self._snapshot = PlaybackSnapshot(generation=generation, text=text)

        producer = threading.Thread(
            target=self._produce_audio,
            args=(generation, audio_stream, self._producer_cancel),
            daemon=True,
        )
        producer.start()
        self._logger.emit("tts_started", generation=generation, text=text)
        return generation

    def interrupt(self, reason: str) -> None:
        with self._lock:
            snapshot = self._snapshot
            cancel_event = self._producer_cancel
            was_speaking = self._speaking
            self._speaking = False
            self._current_generation += 1
            self._snapshot = None
            self.last_output_rms = 0.0

        if cancel_event is not None:
            cancel_event.set()

        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        if snapshot is not None and was_speaking:
            snapshot.interrupted = True
            self._logger.emit(
                "playback_interrupted",
                reason=reason,
                generation=snapshot.generation,
                heard_ratio=snapshot.heard_ratio,
            )
            self._on_interrupted(snapshot)

    def _produce_audio(
        self,
        generation: int,
        audio_stream: Iterable[bytes],
        cancel_event: threading.Event,
    ) -> None:
        try:
            for chunk in audio_stream:
                if cancel_event.is_set():
                    break
                with self._lock:
                    snapshot = self._snapshot
                    current_generation = self._current_generation
                if snapshot is None or generation != snapshot.generation or generation != current_generation:
                    break
                snapshot.produced_bytes += len(chunk)
                self._queue.put(PlaybackChunk(generation=generation, data=chunk, is_end=False))
        finally:
            self._queue.put(PlaybackChunk(generation=generation, is_end=True))

    def _playback_worker(self) -> None:
        while not self._stop_event.is_set():
            chunk = self._queue.get()
            if chunk.generation == -1:
                return

            with self._lock:
                snapshot = self._snapshot
                current_generation = self._current_generation

            if snapshot is None or chunk.generation != current_generation:
                continue

            if chunk.is_end:
                with self._lock:
                    if self._snapshot and self._snapshot.generation == chunk.generation:
                        self._speaking = False
                        self._snapshot = None
                        self.last_output_rms = 0.0
                continue

            self._stream.write(chunk.data)
            self.last_output_rms = pcm_rms(chunk.data)
            with self._lock:
                if self._snapshot and self._snapshot.generation == chunk.generation:
                    self._snapshot.played_bytes += len(chunk.data)


class VoiceTurnDetector:
    def __init__(
        self,
        settings: Settings,
        speaker: SpeakerPlayer,
        logger: StructuredLogger,
        completed_turns: queue.Queue[CompletedTurn],
    ) -> None:
        self._settings = settings
        self._speaker = speaker
        self._logger = logger
        self._completed_turns = completed_turns
        self._ring = PCMFrameRingBuffer(settings.preroll_frames)
        self._recording = False
        self._started_during_playback = False
        self._current_chunks: list[bytes] = []
        self._speech_run = 0
        self._silence_run = 0
        self._max_frames = max(1, (settings.max_turn_seconds * 1000) // settings.frame_ms)

    def process_frame(self, frame: bytes) -> None:
        rms = pcm_rms(frame)
        self._ring.append(frame)

        speaking = self._speaker.is_speaking()
        start_threshold = self._settings.vad_start_threshold
        frames_required = self._settings.start_speech_frames

        if speaking:
            start_threshold = max(
                self._settings.barge_in_threshold,
                self._speaker.last_output_rms * self._settings.echo_gate_multiplier,
            )
            frames_required = self._settings.interrupt_frames

        if not self._recording:
            if rms >= start_threshold:
                self._speech_run += 1
            else:
                self._speech_run = 0

            if self._speech_run >= frames_required:
                interrupted_playback = self._speaker.is_speaking()
                if interrupted_playback:
                    self._speaker.interrupt(reason="barge_in")
                self._recording = True
                self._started_during_playback = interrupted_playback
                self._current_chunks = self._ring.snapshot()
                self._silence_run = 0
                self._speech_run = 0
                self._logger.emit(
                    "speech_started",
                    interrupted_playback=interrupted_playback,
                    threshold=start_threshold,
                )
            return

        self._current_chunks.append(frame)
        if rms < self._settings.vad_continue_threshold:
            self._silence_run += 1
        else:
            self._silence_run = 0

        if self._silence_run >= self._settings.end_silence_frames or len(self._current_chunks) >= self._max_frames:
            audio_bytes = b"".join(self._current_chunks)
            if audio_bytes:
                self._completed_turns.put(
                    CompletedTurn(
                        pcm_bytes=audio_bytes,
                        interrupted_playback=self._started_during_playback,
                    )
                )
                self._logger.emit(
                    "user_turn_finalized",
                    bytes=len(audio_bytes),
                    interrupted_playback=self._started_during_playback,
                )
            self._recording = False
            self._started_during_playback = False
            self._current_chunks = []
            self._speech_run = 0
            self._silence_run = 0


class VoiceConversationRuntime:
    def __init__(self, settings, agents, audio_client, logger) -> None:
        self._settings = settings
        self._agents = agents
        self._audio_client = audio_client
        self._logger = logger
        self._completed_turns: queue.Queue[CompletedTurn] = queue.Queue()
        self._session = SessionState()
        self._speaker = SpeakerPlayer(
            settings=settings,
            logger=logger,
            on_interrupted=self._handle_playback_interrupted,
        )
        self._detector = VoiceTurnDetector(
            settings=settings,
            speaker=self._speaker,
            logger=logger,
            completed_turns=self._completed_turns,
        )

        self._input_stream = sd.InputStream(
            samplerate=settings.input_sample_rate,
            blocksize=settings.frame_size,
            channels=1,
            dtype="float32",
            device=settings.input_device,
            callback=self._audio_callback,
        )

    def run(self) -> None:
        print("AI voice disclosure: you are hearing an AI-generated voice.")
        print("Voice runtime started. Speak a billing question. Press Ctrl+C to stop.")
        self._speaker.start()
        self._input_stream.start()
        try:
            while True:
                turn = self._completed_turns.get()
                self._handle_turn(turn)
        finally:
            self._input_stream.stop()
            self._input_stream.close()
            self._speaker.stop()

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            self._logger.emit("audio_frame_status", status=str(status))
        pcm = float_frame_to_pcm16_bytes(indata.copy())
        self._detector.process_frame(pcm)

    def _handle_turn(self, turn: CompletedTurn) -> None:
        prompt = self._build_transcription_prompt()
        transcript = self._audio_client.transcribe_pcm(
            turn.pcm_bytes,
            sample_rate=self._settings.input_sample_rate,
            prompt=prompt,
        )
        self._logger.emit(
            "transcription_completed",
            session_id=self._session.session_id,
            text=transcript,
            payload={
                "transcript": transcript,
                "audio_bytes": len(turn.pcm_bytes),
                "interrupted_playback": turn.interrupted_playback,
            },
        )
        if not transcript:
            return

        turn_id = self._session.next_turn_id()
        self._session.add_user_turn(transcript)
        compacted = self._session.compacted_view(
            max_recent_turns=self._settings.memory_max_recent_turns,
            max_message_chars=self._settings.memory_max_message_chars,
            max_summary_chars=self._settings.memory_max_summary_chars,
        )
        self._logger.emit(
            "session_compacted",
            session_id=self._session.session_id,
            turn_id=turn_id,
            estimated_tokens=compacted.estimated_tokens,
            compacted=compacted.compacted,
            recent_turn_count=compacted.recent_turn_count,
        )

        flow = VoiceHandoffFlow(self._agents, self._logger)
        flow.state.pending_user_text = transcript
        flow.state.recent_messages = compacted.recent_messages
        flow.state.conversation_summary = compacted.conversation_summary
        flow.state.session_id = self._session.session_id
        flow.state.turn_id = turn_id
        flow.kickoff()

        if flow.state.handoff_payload is not None:
            self._session.last_handoff = flow.state.handoff_payload
            self._logger.emit(
                "handoff_payload_created",
                session_id=self._session.session_id,
                trace_id=flow.state.handoff_payload.trace_id,
                turn_id=turn_id,
                payload=flow.state.handoff_payload.model_dump(mode="json"),
            )

        response_text = flow.state.final_spoken_text
        self._session.add_assistant_turn(response_text)
        self._session.update_summary(max_summary_chars=self._settings.memory_max_summary_chars)

        self._speaker.speak(
            text=response_text,
            audio_stream=self._audio_client.stream_tts_pcm(
                response_text,
                instructions="Speak clearly, warmly, and at a steady customer support pace.",
            ),
        )

    def _handle_playback_interrupted(self, snapshot: PlaybackSnapshot) -> None:
        heard_text = truncate_text_by_ratio(snapshot.text, snapshot.heard_ratio)
        self._session.mark_last_assistant_interrupted(heard_text)

    def _build_transcription_prompt(self) -> str:
        summary = self._session.context_summary(max_summary_chars=self._settings.memory_max_summary_chars)
        return (
            "Customer support conversation. Use punctuation. "
            f"Recent context: {summary[-200:]}"
        )


def build_runtime(
    settings: Settings,
    agents,
    audio_client: OpenAIAudioClient,
    logger: StructuredLogger,
) -> VoiceConversationRuntime:
    return VoiceConversationRuntime(
        settings=settings,
        agents=agents,
        audio_client=audio_client,
        logger=logger,
    )

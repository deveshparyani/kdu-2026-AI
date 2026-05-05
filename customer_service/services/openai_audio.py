from __future__ import annotations

import io
import wave
from collections.abc import Iterator
from typing import Optional

import httpx

from ..config import Settings


class OpenAIAudioClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    def transcribe_pcm(
        self,
        pcm_bytes: bytes,
        sample_rate: int,
        prompt: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        wav_bytes = pcm_to_wav_bytes(pcm_bytes, sample_rate=sample_rate)
        files = {
            "file": ("turn.wav", wav_bytes, "audio/wav"),
        }
        data: dict[str, str] = {"model": self._settings.transcribe_model}
        if prompt:
            data["prompt"] = prompt
        if language:
            data["language"] = language

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self._settings.openai_base_url}/audio/transcriptions",
                headers=self._headers,
                data=data,
                files=files,
            )
            response.raise_for_status()
            payload = response.json()
            return str(payload.get("text", "")).strip()

    def stream_tts_pcm(self, text: str, instructions: Optional[str] = None) -> Iterator[bytes]:
        payload = {
            "model": self._settings.tts_model,
            "voice": self._settings.tts_voice,
            "input": text,
            "response_format": "pcm",
        }
        if instructions:
            payload["instructions"] = instructions

        with httpx.Client(timeout=httpx.Timeout(connect=20.0, read=60.0, write=20.0, pool=60.0)) as client:
            with client.stream(
                "POST",
                f"{self._settings.openai_base_url}/audio/speech",
                headers={**self._headers, "Content-Type": "application/json"},
                json=payload,
            ) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    if chunk:
                        yield chunk


def pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int, channels: int = 1) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()

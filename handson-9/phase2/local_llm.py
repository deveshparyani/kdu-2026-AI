"""Local Llama 3 8B client using Ollama's HTTP API."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx

SYSTEM_PROMPT = (
    "You are a concise educational safety-demo assistant. Answer the user's "
    "current question only. You may use the provided customer profile when it "
    "is relevant to the user's account question. Do not rely on previous chat "
    "history."
)


@dataclass
class LocalLLMResult:
    """Response text and timing from the local Ollama model."""

    text: str
    latency_ms: float


class OllamaClient:
    """Tiny client for Ollama's non-streaming generate endpoint."""

    def __init__(self, *, base_url: str, model: str, timeout_seconds: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def validate_ready(self) -> None:
        """Check that Ollama is reachable and the configured model exists."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise RuntimeError(
                "Ollama is not reachable at "
                f"{self.base_url}. Start Ollama with `ollama serve` or open the "
                "Ollama desktop app."
            ) from error

        models = response.json().get("models", [])
        model_names = {str(model.get("name", "")) for model in models}
        if self.model not in model_names:
            available = ", ".join(sorted(model_names)) or "none"
            raise RuntimeError(
                f"Ollama model {self.model!r} is not installed. Run "
                f"`ollama pull {self.model}`. Available models: {available}."
            )

    def generate(
        self, user_prompt: str, customer_profile: dict[str, str]
    ) -> LocalLLMResult:
        """Generate one response without sending full chat history."""
        started_at = time.perf_counter()
        profile_json = json.dumps(customer_profile, indent=2)
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            "Customer profile from mock backend:\n"
            f"{profile_json}\n\n"
            "User question:\n"
            f"{user_prompt}"
        )

        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 300,
                    },
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise RuntimeError(
                "Ollama request failed. Make sure Ollama is running and the "
                f"{self.model!r} model is pulled."
            ) from error

        latency_ms = (time.perf_counter() - started_at) * 1000
        data = response.json()
        return LocalLLMResult(text=str(data.get("response", "")).strip(), latency_ms=latency_ms)

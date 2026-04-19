"""Small LLM client layer with a mock mode and Groq runtime support."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from app.utils.helpers import estimate_tokens


class LLMClient:
    """Mock-friendly client used by the orchestrator and handlers."""

    def __init__(self) -> None:
        self.use_mock = os.getenv("FIXIT_USE_MOCK_LLM", "true").lower() == "true"
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    def classify_query(
        self,
        query: str,
        model_name: str,
        model_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Classify the query with simple rules for local development."""

        if not self.use_mock:
            return self._classify_query_with_groq(
                query=query,
                model_name=model_name,
                model_config=model_config,
            )

        return self._mock_classify_query(query=query, model_name=model_name)

    def _mock_classify_query(self, query: str, model_name: str) -> dict[str, Any]:
        """Classify the query with simple rules for local development."""

        lowered = query.lower()

        if any(word in lowered for word in ["refund", "complaint", "didn't show", "did not show", "angry", "bad service"]):
            classification = {
                "category": "complaint",
                "complexity": "high" if any(word in lowered for word in ["refund", "urgent", "manager"]) else "medium",
                "response_type": "complex" if any(word in lowered for word in ["refund", "urgent", "manager"]) else "standard",
            }
        elif any(word in lowered for word in ["book", "booking", "appointment", "reschedule", "schedule", "cancel"]):
            classification = {
                "category": "booking",
                "complexity": "medium" if any(word in lowered for word in ["reschedule", "cancel"]) else "low",
                "response_type": "standard" if any(word in lowered for word in ["reschedule", "cancel"]) else "simple",
            }
        else:
            classification = {
                "category": "FAQ",
                "complexity": "low" if len(lowered) < 80 else "medium",
                "response_type": "simple" if "?" in query or len(lowered) < 60 else "standard",
            }

        return {
            "classification": classification,
            "usage": {
                "input_tokens": estimate_tokens(query),
                "output_tokens": estimate_tokens(str(classification)),
            },
            "model_name": model_name,
            "provider_mode": "mock",
        }

    def generate_response(
        self,
        query: str,
        rendered_prompt: dict[str, str],
        model_name: str,
        category: str,
        human_handoff: bool = False,
        model_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a beginner-friendly mock response."""

        if not self.use_mock:
            return self._generate_response_with_groq(
                query=query,
                rendered_prompt=rendered_prompt,
                model_name=model_name,
                category=category,
                human_handoff=human_handoff,
                model_config=model_config,
            )

        return self._mock_generate_response(
            query=query,
            rendered_prompt=rendered_prompt,
            model_name=model_name,
            category=category,
            human_handoff=human_handoff,
        )

    def _mock_generate_response(
        self,
        query: str,
        rendered_prompt: dict[str, str],
        model_name: str,
        category: str,
        human_handoff: bool = False,
    ) -> dict[str, Any]:
        """Return a beginner-friendly mock response."""

        prefix_map = {
            "FAQ": "Here is a quick answer",
            "booking": "Here is help with your booking",
            "complaint": "I am sorry you had this experience",
        }
        prefix = prefix_map.get(category, "Here is your answer")

        response = f"{prefix}: {query.strip()}"
        if category == "complaint" and human_handoff:
            response += " We are also flagging this for a human support review."

        combined_prompt = (
            f"{rendered_prompt['system_message']}\n{rendered_prompt['user_message']}"
        )

        return {
            "text": response,
            "usage": {
                "input_tokens": estimate_tokens(query) + estimate_tokens(combined_prompt),
                "output_tokens": estimate_tokens(response),
            },
            "model_name": model_name,
            "provider_mode": "mock",
        }

    def _classify_query_with_groq(
        self,
        query: str,
        model_name: str,
        model_config: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Classify a support query with a Groq-hosted chat model."""

        response = self._chat_completion(
            model_config=model_config,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify customer support queries for FixIt. "
                        "Return a JSON object with exactly these keys: "
                        "category, complexity, response_type. "
                        "Allowed category values: FAQ, booking, complaint. "
                        "Allowed complexity values: low, medium, high. "
                        "Allowed response_type values: simple, standard, complex. "
                        "Use complaint for refunds, no-shows, missed appointments, or bad service. "
                        "Use booking for scheduling, rescheduling, canceling, or appointment changes. "
                        "Use FAQ for general information questions. "
                        "Examples: "
                        "\"What are your hours?\" -> "
                        "{\"category\":\"FAQ\",\"complexity\":\"low\",\"response_type\":\"simple\"}. "
                        "\"My plumber didn't show up, need refund\" -> "
                        "{\"category\":\"complaint\",\"complexity\":\"high\",\"response_type\":\"complex\"}. "
                        "\"Can I reschedule my cleaning appointment?\" -> "
                        "{\"category\":\"booking\",\"complexity\":\"medium\",\"response_type\":\"standard\"}."
                    ),
                },
                {"role": "user", "content": query.strip()},
            ],
            response_format={"type": "json_object"},
        )
        raw_text = self._extract_text(response)
        classification = self._parse_classification(raw_text)
        usage = self._extract_usage(
            response=response,
            fallback_input=query,
            fallback_output=raw_text,
        )

        return {
            "classification": classification,
            "usage": usage,
            "model_name": model_name,
            "provider_mode": "groq",
            "provider_model_name": model_config["model_name"],
        }

    def _generate_response_with_groq(
        self,
        query: str,
        rendered_prompt: dict[str, str],
        model_name: str,
        category: str,
        human_handoff: bool,
        model_config: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Generate a customer-facing answer with a Groq-hosted chat model."""

        handoff_instruction = ""
        if human_handoff:
            handoff_instruction = (
                " This case needs human review. Mention that a human support specialist "
                "will follow up."
            )

        response = self._chat_completion(
            model_config=model_config,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the FixIt support assistant. Follow the supplied instructions, "
                        "be concise and helpful. Never claim access to company systems, bookings, "
                        "policies, schedules, or internal case tools unless that information is "
                        "explicitly provided in the prompt. Never invent store hours, prices, "
                        "refund approvals, refund timelines, confirmation emails, compensation, or "
                        "appointment details. If the needed business fact is missing, say you do not "
                        "have that information here and offer the next best step, such as asking for "
                        "booking details or directing the customer to a human support channel. "
                        "Safe examples: "
                        "If asked about hours and no hours are provided, say you do not have the "
                        "current business hours available in this workflow. "
                        "If asked for a refund after a no-show, apologize, explain that a human "
                        "support specialist will review it, and ask for the booking reference and "
                        "appointment details without promising a refund timeline."
                        f"{handoff_instruction}"
                    ),
                },
                {"role": "system", "content": rendered_prompt["system_message"]},
                {"role": "user", "content": rendered_prompt["user_message"]},
            ],
        )
        text = self._extract_text(response)
        if human_handoff and "human" not in text.lower():
            text += " A human support specialist will also review this case."

        usage = self._extract_usage(
            response=response,
            fallback_input=(
                f"{rendered_prompt['system_message']}\n{rendered_prompt['user_message']}\n{query}"
            ),
            fallback_output=text,
        )

        return {
            "text": text,
            "usage": usage,
            "model_name": model_name,
            "provider_mode": "groq",
            "provider_model_name": model_config["model_name"],
        }

    def _chat_completion(
        self,
        model_config: dict[str, Any] | None,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Call Groq's OpenAI-compatible chat completions API."""

        if model_config is None:
            raise ValueError("A model configuration is required when mock mode is disabled.")
        if model_config.get("provider") != "groq":
            raise ValueError(
                f"Unsupported provider '{model_config.get('provider')}'. Expected 'groq'."
            )
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when FIXIT_USE_MOCK_LLM=false.")

        payload: dict[str, Any] = {
            "model": model_config["model_name"],
            "messages": messages,
            "temperature": model_config.get("temperature", 0.2),
            "max_tokens": model_config.get("max_tokens", 300),
        }
        if response_format is not None:
            payload["response_format"] = response_format

        request_data = json.dumps(payload).encode("utf-8")
        api_request = request.Request(
            url=f"{self.groq_base_url}/chat/completions",
            data=request_data,
            headers={
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "fixit-support-llmops/1.0",
            },
            method="POST",
        )

        try:
            with request.urlopen(api_request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Groq API request failed with HTTP {exc.code}: {body}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Could not reach Groq API: {exc.reason}") from exc

    def _extract_text(self, response: dict[str, Any]) -> str:
        """Read assistant text from a chat completion response."""

        content = response["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return "".join(text_parts).strip()
        raise ValueError("Unsupported response content format from Groq API.")

    def _extract_usage(
        self,
        response: dict[str, Any],
        fallback_input: str,
        fallback_output: str,
    ) -> dict[str, int]:
        """Normalize usage fields across mock and live responses."""

        usage = response.get("usage", {})
        return {
            "input_tokens": int(usage.get("prompt_tokens", estimate_tokens(fallback_input))),
            "output_tokens": int(
                usage.get("completion_tokens", estimate_tokens(fallback_output))
            ),
        }

    def _parse_classification(self, raw_text: str) -> dict[str, str]:
        """Parse and validate model JSON output for routing."""

        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        parsed = json.loads(cleaned)
        if "classification" in parsed and isinstance(parsed["classification"], dict):
            parsed = parsed["classification"]

        category_map = {
            "faq": "FAQ",
            "booking": "booking",
            "complaint": "complaint",
        }
        complexity_map = {"low": "low", "medium": "medium", "high": "high"}
        response_type_map = {
            "simple": "simple",
            "standard": "standard",
            "complex": "complex",
        }

        category = category_map.get(str(parsed["category"]).strip().lower())
        complexity = complexity_map.get(str(parsed["complexity"]).strip().lower())
        response_type = response_type_map.get(
            str(parsed["response_type"]).strip().lower()
        )

        if not category or not complexity or not response_type:
            raise ValueError(f"Invalid classification payload returned by model: {raw_text}")

        return {
            "category": category,
            "complexity": complexity,
            "response_type": response_type,
        }

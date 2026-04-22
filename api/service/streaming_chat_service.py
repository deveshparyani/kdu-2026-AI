from __future__ import annotations

import json
import os
from typing import Any, Iterator

from dotenv import load_dotenv
from openai import OpenAI

from services.chat_service import ChatServiceError
from tools.calculator_tool import calculator
from tools.tools import tools
from tools.weather_tool import get_weather
from utils.calculate_usage import calculate_usage


load_dotenv()


class StreamingChatService:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-nano")
        self.client: OpenAI | None = None

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        try:
            yield from self._stream(messages)
        except ChatServiceError as exc:
            yield self._event("error", {"detail": str(exc)})
        except Exception:
            yield self._event(
                "error",
                {"detail": "Unable to process chat request."},
            )

    def _stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        if not messages:
            raise ChatServiceError("At least one message is required.")

        input_items: list[Any] = list(messages)
        usage_totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        }
        cost_available = True
        reply_sent = False

        while True:
            response = self._get_client().responses.create(
                model=self.model,
                input=input_items,
                tools=tools,
                stream=True,
            )

            tool_calls = []
            completed_response = None

            for event in response:
                if event.type == "response.output_text.delta":
                    delta = event.delta or ""
                    if delta:
                        reply_sent = True
                        yield self._event("delta", {"delta": delta})

                elif event.type == "response.output_item.done":
                    item = event.item
                    if getattr(item, "type", None) == "function_call":
                        tool_calls.append(item)

                elif event.type == "response.completed":
                    completed_response = event.response

            usage = calculate_usage(completed_response)
            usage_totals["input_tokens"] += usage["input_tokens"]
            usage_totals["output_tokens"] += usage["output_tokens"]
            usage_totals["total_tokens"] += usage["total_tokens"]

            if usage["estimated_cost_usd"] is not None and cost_available:
                usage_totals["estimated_cost_usd"] += usage["estimated_cost_usd"]
            else:
                cost_available = False
                usage_totals["estimated_cost_usd"] = None

            if tool_calls:
                input_items.extend(tool_calls)
                for tool_call in tool_calls:
                    result = self._run_tool(tool_call)
                    input_items.append(
                        {
                            "type": "function_call_output",
                            "call_id": tool_call.call_id,
                            "output": json.dumps(result),
                        }
                    )
                continue

            if not reply_sent:
                reply = getattr(completed_response, "output_text", "").strip()
                if not reply:
                    reply = "I couldn't generate a response just now."
                yield self._event("delta", {"delta": reply})

            yield self._event("usage", {"usage": usage_totals})
            yield self._event("done", {})
            return

    def _run_tool(self, tool_call: Any) -> Any:
        try:
            arguments = json.loads(tool_call.arguments or "{}")
        except json.JSONDecodeError as exc:
            raise ChatServiceError(
                f"Invalid tool arguments for `{tool_call.name}`."
            ) from exc

        if tool_call.name == "get_weather":
            return get_weather(**arguments)

        if tool_call.name == "calculator":
            return calculator(**arguments)

        raise ChatServiceError(f"Unsupported tool requested: `{tool_call.name}`.")

    def _get_client(self) -> OpenAI:
        if self.client is not None:
            return self.client

        if not os.getenv("OPENAI_API_KEY"):
            raise ChatServiceError("OPENAI_API_KEY is not configured.")

        self.client = OpenAI()
        return self.client

    def _event(self, event_type: str, payload: dict[str, Any]) -> str:
        return json.dumps({"type": event_type, **payload}) + "\n"

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from tools.calculator_tool import calculator
from tools.tools import tools
from tools.weather_tool import get_weather
from utils.calculate_usage import calculate_usage


load_dotenv()


class ChatServiceError(Exception):
    """Raised when the chatbot request cannot be completed."""


class ChatService:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-nano")
        self.client: OpenAI | None = None

    def chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
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

        while True:
            response = self._get_client().responses.create(
                model=self.model,
                input=input_items,
                tools=tools,
            )
            usage = calculate_usage(response)
            usage_totals["input_tokens"] += usage["input_tokens"]
            usage_totals["output_tokens"] += usage["output_tokens"]
            usage_totals["total_tokens"] += usage["total_tokens"]

            if usage["estimated_cost_usd"] is not None and cost_available:
                usage_totals["estimated_cost_usd"] += usage["estimated_cost_usd"]
            else:
                cost_available = False
                usage_totals["estimated_cost_usd"] = None

            function_calls = [
                item
                for item in getattr(response, "output", [])
                if getattr(item, "type", None) == "function_call"
            ]

            if not function_calls:
                reply = getattr(response, "output_text", "").strip()
                if not reply:
                    reply = "I couldn't generate a response just now."

                return {
                    "reply": reply,
                    "usage": usage_totals,
                }

            input_items.extend(function_calls)

            for tool_call in function_calls:
                result = self._run_tool(tool_call)
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_call.call_id,
                        "output": json.dumps(result),
                    }
                )

    def _run_tool(self, tool_call: Any) -> Any:
        try:
            arguments = json.loads(tool_call.arguments or "{}")
        except json.JSONDecodeError as exc:
            raise ChatServiceError(f"Invalid tool arguments for `{tool_call.name}`.") from exc

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

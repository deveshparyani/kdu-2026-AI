"""Custom NeMo Guardrails actions for the safety demo."""

from __future__ import annotations

import re
from typing import Optional

from langsmith import traceable
from nemoguardrails.actions import action

SSN_PATTERN = re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b")

PROMPT_INJECTION_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\bjailbreak\b",
    r"\boverride\s+(the\s+)?instructions\b",
    r"\bdisregard\s+(the\s+)?instructions\b",
    r"\bforget\s+(the\s+)?(system|developer|previous)\s+instructions\b",
    r"\bdo\s+not\s+follow\s+(the\s+)?(system|developer)\s+instructions\b",
]

DEBUG_MODE_PATTERNS = [
    r"\byou\s+are\s+now\s+a\s+debugging\s+system\b",
    r"\benter\s+(debug|developer|admin)\s+mode\b",
    r"\bact\s+as\s+(a\s+)?(debugger|developer|admin)\b",
    r"\bprint\s+(the\s+)?(prompt|system\s+prompt|hidden\s+instructions)\b",
]

PROTECTED_DATA_PATTERNS = [
    r"\breveal\s+internal\s+(information|data)\b",
    r"\bprint\s+(all\s+)?stored\s+(profile\s+data|user\s+information)\b",
    r"\bshow\s+confidential\s+data\b",
    r"\boutput\s+the\s+complete\s+customer\s+profile\b",
    r"\breveal\s+(the\s+)?(full\s+)?ssn\b",
    r"\bshow\s+(me\s+)?(the\s+)?full\s+ssn\b",
    r"\bprint\s+(the\s+)?(full\s+)?customer\s+profile\b",
]

INTERNAL_PROFILE_OUTPUT_PATTERNS = [
    r"\binternal\s+customer\s+profile\s+data\b",
    r'"ssn"\s*:\s*"\d{3}-\d{2}-\d{4}"',
    r"\bcomplete\s+customer\s+profile\b",
]


def _latest_user_message(context: Optional[dict]) -> str:
    """Read the latest user message from NeMo's action context."""
    if not context:
        return ""

    return str(
        context.get("user_message")
        or context.get("last_user_message")
        or context.get("input")
        or ""
    )


def _matches_any_pattern(text: str, patterns: list[str]) -> bool:
    """Return True when any configured regex matches the text."""
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


@action(is_system_action=True)
async def detect_prompt_injection(context: Optional[dict] = None) -> bool:
    """Detect simple instruction override and jailbreak phrases."""
    user_message = _latest_user_message(context)
    return _matches_any_pattern(user_message, PROMPT_INJECTION_PATTERNS)


@action(is_system_action=True)
async def detect_debug_mode_attempt(context: Optional[dict] = None) -> bool:
    """Detect attempts to switch the assistant into privileged debug roles."""
    user_message = _latest_user_message(context)
    return _matches_any_pattern(user_message, DEBUG_MODE_PATTERNS)


@action(is_system_action=True)
async def detect_protected_data_request(context: Optional[dict] = None) -> bool:
    """Detect requests for internal profile data, not ordinary account help."""
    user_message = _latest_user_message(context)
    return _matches_any_pattern(user_message, PROTECTED_DATA_PATTERNS)


@action(is_system_action=True)
async def detect_internal_profile_dump(context: Optional[dict] = None) -> bool:
    """Detect accidental dumps of internal profile-shaped output."""
    bot_message = ""
    if context:
        bot_message = str(context.get("bot_message", ""))

    return _matches_any_pattern(bot_message, INTERNAL_PROFILE_OUTPUT_PATTERNS)


@action(is_system_action=True)
@traceable(name="mask_ssns", run_type="tool")
async def mask_ssns(text: str | None = None, context: Optional[dict] = None) -> str:
    """Mask SSNs while preserving the last four digits.

    Example: 123-45-6789 becomes ***-**-6789.
    """
    if text is None and context:
        text = str(context.get("bot_message", ""))

    text = text or ""
    return SSN_PATTERN.sub(lambda match: f"***-**-{match.group(3)}", text)

"""Small wrapper around the AWS Bedrock ApplyGuardrail API."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

import boto3
from botocore.exceptions import BotoCoreError, ClientError

GuardrailSource = Literal["INPUT", "OUTPUT"]


@dataclass
class GuardrailFinding:
    """A compact content-filter finding for terminal display."""

    policy: str
    type: str
    confidence: str
    filter_strength: str
    action: str


@dataclass
class GuardrailResult:
    """Normalized result from AWS Bedrock Guardrails."""

    source: GuardrailSource
    action: str
    text: str
    latency_ms: float
    findings: list[GuardrailFinding]
    raw_response: dict[str, Any]

    @property
    def intervened(self) -> bool:
        """Return True when Bedrock blocked, masked, or otherwise intervened."""
        return self.action == "GUARDRAIL_INTERVENED"


class BedrockGuardrail:
    """Apply one configured AWS Bedrock Guardrail to input or output text."""

    def __init__(
        self,
        *,
        region_name: str,
        guardrail_id: str,
        guardrail_version: str,
        output_scope: str = "FULL",
        profile_name: str | None = None,
    ) -> None:
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        self.output_scope = output_scope
        self.session = boto3.Session(profile_name=profile_name, region_name=region_name)
        self.client = self.session.client("bedrock-runtime")

    def validate_credentials(self) -> str:
        """Verify AWS credentials before the chatbot starts."""
        try:
            identity = self.session.client("sts").get_caller_identity()
        except (BotoCoreError, ClientError) as error:
            raise RuntimeError(
                "AWS credentials are invalid or expired. Run `aws sts "
                "get-caller-identity` to confirm, then refresh your AWS CLI "
                "credentials or set AWS_PROFILE in phase2/.env."
            ) from error

        return str(identity.get("Arn", "unknown AWS identity"))

    def apply(self, text: str, source: GuardrailSource) -> GuardrailResult:
        """Call ApplyGuardrail and normalize the response for the chatbot."""
        started_at = time.perf_counter()

        request: dict[str, Any] = {
            "guardrailIdentifier": self.guardrail_id,
            "guardrailVersion": self.guardrail_version,
            "source": source,
            "content": [{"text": {"text": text}}],
        }

        # FULL is useful for the classroom demo because it exposes more trace
        # detail when the guardrail evaluates content without blocking it.
        if self.output_scope:
            request["outputScope"] = self.output_scope

        try:
            response = self.client.apply_guardrail(**request)
        except (BotoCoreError, ClientError) as error:
            raise RuntimeError(f"AWS Bedrock ApplyGuardrail failed: {error}") from error

        latency_ms = (time.perf_counter() - started_at) * 1000

        return GuardrailResult(
            source=source,
            action=response.get("action", "UNKNOWN"),
            text=_extract_output_text(response),
            latency_ms=latency_ms,
            findings=_extract_findings(response),
            raw_response=response,
        )


def _extract_output_text(response: dict[str, Any]) -> str:
    """Read Bedrock's guarded output text from either documented key spelling."""
    outputs = response.get("outputs") or response.get("output") or []

    text_parts: list[str] = []
    for item in outputs:
        text = item.get("text") if isinstance(item, dict) else None
        if text:
            text_parts.append(str(text))

    return "\n".join(text_parts)


def _extract_findings(response: dict[str, Any]) -> list[GuardrailFinding]:
    """Pull content filter findings from the nested assessment response."""
    findings: list[GuardrailFinding] = []

    for assessment in response.get("assessments", []):
        content_policy = assessment.get("contentPolicy", {})
        for item in content_policy.get("filters", []):
            findings.append(
                GuardrailFinding(
                    policy="contentPolicy",
                    type=str(item.get("type", "UNKNOWN")),
                    confidence=str(item.get("confidence", "UNKNOWN")),
                    filter_strength=str(
                        item.get("filterStrength")
                        or item.get("inputStrength")
                        or item.get("outputStrength")
                        or "UNKNOWN"
                    ),
                    action=str(item.get("action", "UNKNOWN")),
                )
            )

        sensitive_policy = assessment.get("sensitiveInformationPolicy", {})
        for item in sensitive_policy.get("piiEntities", []):
            findings.append(
                GuardrailFinding(
                    policy="sensitiveInformationPolicy",
                    type=str(item.get("type", "UNKNOWN")),
                    confidence="N/A",
                    filter_strength="N/A",
                    action=str(item.get("action", "UNKNOWN")),
                )
            )

        for item in sensitive_policy.get("regexes", []):
            findings.append(
                GuardrailFinding(
                    policy="sensitiveInformationPolicy",
                    type=str(item.get("name", "REGEX")),
                    confidence="N/A",
                    filter_strength="N/A",
                    action=str(item.get("action", "UNKNOWN")),
                )
            )

    return findings

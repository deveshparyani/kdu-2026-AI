"""A very small YAML subset parser for this project.

This is intentionally tiny and only supports the YAML features used in the
FixIt demo files:

- nested dictionaries based on indentation
- quoted and unquoted scalar values
- booleans, integers, and floats
- inline lists like [a, b, c]
- folded multiline strings using `>`

It is not a full YAML implementation, but it keeps this beginner project
portable when PyYAML is not installed.
"""

from __future__ import annotations

from typing import Any


def _read_text(stream_or_text: Any) -> str:
    if hasattr(stream_or_text, "read"):
        return stream_or_text.read()
    return str(stream_or_text)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""

    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]

    quoted = _strip_quotes(value)
    if quoted != value:
        return quoted

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _next_non_empty_line(lines: list[str], start_index: int) -> tuple[int | None, str | None]:
    for index in range(start_index, len(lines)):
        candidate = lines[index]
        if candidate.strip():
            return index, candidate
    return None, None


def _parse_mapping(lines: list[str], start_index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    index = start_index

    while index < len(lines):
        raw_line = lines[index]
        if not raw_line.strip():
            index += 1
            continue

        current_indent = len(raw_line) - len(raw_line.lstrip(" "))
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"Unexpected indentation near line: {raw_line}")

        line = raw_line.strip()
        if ":" not in line:
            raise ValueError(f"Invalid YAML line: {raw_line}")

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value == ">":
            index += 1
            folded_parts: list[str] = []
            while index < len(lines):
                continuation = lines[index]
                if not continuation.strip():
                    index += 1
                    continue
                continuation_indent = len(continuation) - len(continuation.lstrip(" "))
                if continuation_indent <= current_indent:
                    break
                folded_parts.append(continuation.strip())
                index += 1
            result[key] = " ".join(folded_parts).strip()
            continue

        if value == "":
            next_index, next_line = _next_non_empty_line(lines, index + 1)
            if next_index is None:
                result[key] = {}
                index += 1
                continue

            next_indent = len(next_line) - len(next_line.lstrip(" "))
            if next_indent <= current_indent:
                result[key] = {}
                index += 1
                continue

            child, index = _parse_mapping(lines, index + 1, next_indent)
            result[key] = child
            continue

        result[key] = _parse_scalar(value)
        index += 1

    return result, index


def safe_load(stream_or_text: Any) -> dict[str, Any]:
    text = _read_text(stream_or_text)
    lines = text.splitlines()
    data, _ = _parse_mapping(lines, 0, 0)
    return data


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        inner = ", ".join(_format_scalar(item) for item in value)
        return f"[{inner}]"
    if isinstance(value, str):
        if value == "" or any(char in value for char in [":", "#", "{", "}", "[", "]"]):
            return f'"{value}"'
        return value
    return str(value)


def _dump_mapping(data: dict[str, Any], indent: int) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.extend(_dump_mapping(value, indent + 2))
        else:
            lines.append(f"{prefix}{key}: {_format_scalar(value)}")
    return lines


def safe_dump(data: dict[str, Any], *_args: Any, **_kwargs: Any) -> str:
    return "\n".join(_dump_mapping(data, 0)) + "\n"

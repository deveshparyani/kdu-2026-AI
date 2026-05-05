from __future__ import annotations

import re


class SecurityValidationError(ValueError):
    """Raised when a query or tool input attempts unauthorized access."""


class QuerySecurityGuard:
    SECRET_PATTERNS = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"(^|[\s'\"`])\.env($|[\s'\"`])",
            r"openai_api_key",
            r"os\.environ",
            r"authorization\s*:\s*bearer",
            r"dotenv",
            r"file://",
            r"/etc/passwd",
            r"~\/",
            r"\bsecrets?\b",
        ]
    ]

    SQL_WRITE_PATTERNS = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"\bdrop\s+table\b",
            r"\bdelete\s+from\b",
            r"\binsert\s+into\b",
            r"\bupdate\s+\w+\s+set\b",
            r"\balter\s+table\b",
        ]
    ]

    @classmethod
    def validate_user_query(cls, query: str) -> str:
        normalized = " ".join(query.split()).strip()
        if not normalized:
            raise SecurityValidationError("Query cannot be empty.")
        cls._raise_for_secrets(normalized)
        return normalized

    @classmethod
    def validate_worker_query(cls, query: str) -> str:
        normalized = cls.validate_user_query(query)
        for pattern in cls.SQL_WRITE_PATTERNS:
            if pattern.search(normalized):
                raise SecurityValidationError("Write-oriented database commands are not allowed.")
        return normalized

    @classmethod
    def _raise_for_secrets(cls, value: str) -> None:
        for pattern in cls.SECRET_PATTERNS:
            if pattern.search(value):
                raise SecurityValidationError(
                    "Unauthorized access attempt blocked: secret or local file access is not allowed."
                )


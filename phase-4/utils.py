from __future__ import annotations

import re
from typing import Optional


ORDER_ID_PATTERN = re.compile(r"\b(?:ORD\d+|TXN-\d+)\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)")
ACCOUNT_NUMBER_PATTERN = re.compile(r"Account Number:\s*([0-9]{6,})", re.IGNORECASE)
CVV_PATTERN = re.compile(r"CVV:\s*([0-9]{3,4})", re.IGNORECASE)


def extract_order_ids(document_text: str) -> list[str]:
    return ORDER_ID_PATTERN.findall(document_text)


def extract_amounts(document_text: str) -> list[float]:
    return [float(match) for match in AMOUNT_PATTERN.findall(document_text)]


def extract_account_number(document_text: str) -> Optional[str]:
    match = ACCOUNT_NUMBER_PATTERN.search(document_text)
    return match.group(1) if match else None


def extract_cvv(document_text: str) -> Optional[str]:
    match = CVV_PATTERN.search(document_text)
    return match.group(1) if match else None

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal, Optional

from agents import Agent, RunContextWrapper, Runner, function_tool
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from utils import (
    extract_account_number,
    extract_amounts,
    extract_cvv,
    extract_order_ids,
)


load_dotenv()


@dataclass
class AppContext:
    user_id: str
    case_facts: dict = field(default_factory=dict)


class TransactionExtractionResult(BaseModel):
    ok: bool
    status: Literal["completed", "requires_user_input"]
    message: str
    extracted_transactions: list[dict] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    state: Optional[str] = None


@function_tool
def extract_and_store_case_facts(
    ctx: RunContextWrapper[AppContext],
    document_text: str,
) -> TransactionExtractionResult:
    """Extract structured transaction and banking data from a document."""
    order_ids = extract_order_ids(document_text)
    amounts = extract_amounts(document_text)
    account_number = extract_account_number(document_text)
    cvv = extract_cvv(document_text)

    transactions: list[dict] = []
    for index, order_id in enumerate(order_ids):
        amount = amounts[index] if index < len(amounts) else None
        transactions.append(
            {
                "order_id": order_id,
                "amount": amount,
            }
        )

    missing_fields: list[str] = []
    if not account_number:
        missing_fields.append("account_number")
    if not cvv:
        missing_fields.append("cvv")

    ctx.context.case_facts["transactions"] = transactions
    ctx.context.case_facts["banking"] = {
        "account_number": account_number,
        "cvv": cvv,
    }
    ctx.context.case_facts["user_id"] = ctx.context.user_id

    if missing_fields:
        ctx.context.case_facts["state"] = "requires_user_input"
        ctx.context.case_facts["missing_fields"] = missing_fields
        return TransactionExtractionResult(
            ok=False,
            status="requires_user_input",
            message="Some required fields are missing. Additional user input is required.",
            extracted_transactions=transactions,
            missing_fields=missing_fields,
            state="requires_user_input",
        )

    ctx.context.case_facts["state"] = "completed"
    ctx.context.case_facts["missing_fields"] = []
    return TransactionExtractionResult(
        ok=True,
        status="completed",
        message="Critical transactional data extracted successfully.",
        extracted_transactions=transactions,
        missing_fields=[],
        state="completed",
    )


memory_agent = Agent[AppContext](
    name="Memory Compaction Agent",
    instructions="""
    You are responsible for:
    - Extracting important transactional data
    - Preserving critical business information
    - Ignoring irrelevant conversational messages
    - Maintaining structured case facts memory

    Rules:
    - Extract order IDs
    - Extract amounts
    - Extract banking information
    - Detect missing required fields
    - Never remove structured transactional data
    - Ignore irrelevant messages like: okay, cool, nice, thanks

    Use extract_and_store_case_facts.
    """,
    model="gpt-4o-mini",
    tools=[extract_and_store_case_facts],
)


conversation_history: list[dict] = []


if __name__ == "__main__":
    app_context = AppContext(user_id="user_123")

    long_document = """
    Customer transaction report.
    Order ID: ORD1001
    Amount: $5000
    Order ID: TXN-889
    Amount: $1200
    Account Number: 9988776655
    Customer requested payment processing.
    Additional notes: shipment delayed.
    """

    conversation_history.append(
        {
            "role": "user",
            "content": long_document,
        }
    )

    result = Runner.run_sync(
        starting_agent=memory_agent,
        input=long_document,
        context=app_context,
    )

    irrelevant_messages = ["okay", "cool", "nice", "thanks"]
    for message in irrelevant_messages:
        conversation_history.append(
            {
                "role": "user",
                "content": message,
            }
        )

    print("\nFINAL AGENT OUTPUT:\n")
    print(result.final_output)
    print("\nSTRUCTURED CASE FACTS:\n")
    print(json.dumps(app_context.case_facts, indent=4))
    print("\nSESSION MEMORY:\n")
    print(json.dumps(conversation_history, indent=4))

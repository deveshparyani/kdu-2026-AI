from dataclasses import dataclass, field
from typing import Optional, Literal

from agents import Agent, Runner, RunContextWrapper, function_tool
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv()


# Application Context
@dataclass
class AppContext:
    user_id: str
    case_facts: dict = field(default_factory=dict)



class BankingDetailsUpdateResult(BaseModel):
    ok: bool
    status: Literal["requires_user_input", "ready_to_update"]
    message: str
    missing_fields: list[str] = Field(default_factory=list)
    user_id: Optional[str] = None


class BankingDetailsPayload(BaseModel):
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None




@function_tool
def update_banking_details(
    ctx: RunContextWrapper[AppContext],
    routing_number: str,
    account_number: Optional[str] = None,
    account_type: Optional[str] = None,
) -> BankingDetailsUpdateResult:
    """
    Validate banking details and update the case state for the current user.
    """

    payload = BankingDetailsPayload(
        routing_number=routing_number,
        account_number=account_number,
        account_type=account_type,
    )

    missing_fields = [
        field_name
        for field_name, value in payload.model_dump().items()
        if value is None or value == ""
    ]

    ctx.context.case_facts["banking_details"] = payload.model_dump()

    if missing_fields:
        ctx.context.case_facts["state"] = "requires_user_input"
        ctx.context.case_facts["missing_fields"] = missing_fields

        return BankingDetailsUpdateResult(
            ok=False,
            status="requires_user_input",
            message="Additional banking information is required before the update can be completed.",
            missing_fields=missing_fields,
            user_id=ctx.context.user_id,
        )

    ctx.context.case_facts["state"] = "ready_to_update"
    ctx.context.case_facts["missing_fields"] = []

    return BankingDetailsUpdateResult(
        ok=True,
        status="ready_to_update",
        message="Banking details have been validated and are ready for update.",
        missing_fields=[],
        user_id=ctx.context.user_id,
    )



finance_agent = Agent[AppContext](
    name="Finance Agent",
    instructions="""
    You are the Finance Agent.

    Scope:
    - Handle payroll and banking-detail update workflows.
    - Use update_banking_details for banking-detail update requests.

    Rules:
    - Do not process HR, legal, or unrelated requests.
    - Do not infer missing banking fields.
    - Do not request or rely on unrelated conversation history.
    - If required fields are missing, clearly identify the missing fields.
    - Claim that banking details were updated if the tool returns ok=true.
    """,
    model="gpt-4o-mini",
    tools=[update_banking_details],
)



coordinator_agent = Agent[AppContext](
    name="Coordinator Agent",
    instructions="""
    You are the Coordinator Agent.

    Responsibilities:
    - Classify the user's request.
    - Delegate finance-specific requests to ask_finance_agent.
    - Pass only the fields required for the finance task.
    - Do not expose unrelated conversation history to specialist agents.

    For banking-detail update requests, pass only:
    - task intent
    - routing number, if provided
    - account number, if provided
    - account type, if provided

    If the user provides only a routing number, still delegate to Finance Agent.
    The Finance Agent is responsible for validating required fields and reporting missing information.
    """,
    model="gpt-4o-mini",
    tools=[
        finance_agent.as_tool(
            tool_name="ask_finance_agent",
            tool_description=(
                "Delegate finance-specific requests such as payroll or banking-detail updates. "
                "Only include finance-relevant fields in the request."
            ),
        )
    ],
)


if __name__ == "__main__":
    app_context = AppContext(user_id="user_123")

    result = Runner.run_sync(
        starting_agent=coordinator_agent,
        input="Update my banking details. Routing number is 123456789. My account number is 987654321. Account type is SAVINGS.",
        context=app_context,
    )

    print("Final output:")
    print(result.final_output)

    print("\nCase facts:")
    print(app_context.case_facts)
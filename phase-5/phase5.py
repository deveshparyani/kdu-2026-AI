from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

from agents import Agent, RunContextWrapper, Runner, function_tool
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


@dataclass
class WorkflowContext:
    user_id: str
    original_request: str = ""
    planner_output: dict = field(default_factory=dict)
    execution_log: list[dict] = field(default_factory=list)
    shared_memory: dict = field(default_factory=dict)


class PlanStep(BaseModel):
    step_id: str
    title: str
    action: Literal[
        "lookup_order",
        "lookup_payment",
        "create_refund_case",
        "finalize_response",
    ]
    rationale: str
    depends_on: list[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    goal: str
    steps: list[PlanStep]
    success_criteria: list[str] = Field(default_factory=list)


class StepFact(BaseModel):
    key: str
    value: str


class StepExecutionResult(BaseModel):
    step_id: str
    status: Literal["completed", "blocked"]
    summary: str
    facts: list[StepFact] = Field(default_factory=list)


@function_tool
def fetch_shared_memory(ctx: RunContextWrapper[WorkflowContext]) -> dict:
    """Return workflow memory shared by the planner and executor."""
    return {
        "original_request": ctx.context.original_request,
        "planner_output": ctx.context.planner_output,
        "execution_log": ctx.context.execution_log,
        "shared_memory": ctx.context.shared_memory,
    }


@function_tool
def lookup_order(order_id: str) -> dict:
    """Lookup order information in a mock order system."""
    fake_orders = {
        "ORD-1001": {
            "order_id": "ORD-1001",
            "status": "delivered",
            "item": "Noise-cancelling headphones",
            "customer": "John",
        }
    }
    order = fake_orders.get(order_id)
    if not order:
        return {"ok": False, "message": f"No order found for {order_id}."}
    return {"ok": True, "order": order}


@function_tool
def lookup_payment(order_id: str) -> dict:
    """Lookup payment information for an order."""
    fake_payments = {
        "ORD-1001": {
            "order_id": "ORD-1001",
            "payment_status": "captured",
            "amount": 249.99,
            "currency": "USD",
        }
    }
    payment = fake_payments.get(order_id)
    if not payment:
        return {"ok": False, "message": f"No payment found for {order_id}."}
    return {"ok": True, "payment": payment}


@function_tool
def create_refund_case(order_id: str, reason: str) -> dict:
    """Create a refund case in a mock support system."""
    return {
        "ok": True,
        "refund_case_id": "RFC-9001",
        "order_id": order_id,
        "reason": reason,
        "status": "created",
    }


planner_agent = Agent[WorkflowContext](
    name="Planner Agent",
    model="o3-mini",
    instructions="""
    You are the Planner Agent in a planner-executor workflow.

    Produce a structured JSON plan only.

    Rules:
    - Read the user's request and break it into small executable steps.
    - Use only these actions: lookup_order, lookup_payment, create_refund_case, finalize_response.
    - Each step must have a stable step_id.
    - Respect dependencies between steps.
    - Keep the plan concise and execution-ready.
    """,
    output_type=ExecutionPlan,
)


executor_agent = Agent[WorkflowContext](
    name="Executor Agent",
    model="gpt-4o",
    instructions="""
    You are the Executor Agent.

    Your job:
    - Execute exactly one plan step at a time.
    - Call fetch_shared_memory before acting so you stay consistent with the workflow state.
    - Respect step dependencies from the planner output.
    - Use tool results, not guesses.
    - Return a structured step execution result.

    Action rules:
    - lookup_order: call lookup_order with the order ID from the request.
    - lookup_payment: call lookup_payment with the same order ID.
    - create_refund_case: call create_refund_case only after order and payment checks succeed.
    - finalize_response: summarize the completed work using shared memory and execution log.
    """,
    tools=[
        fetch_shared_memory,
        lookup_order,
        lookup_payment,
        create_refund_case,
    ],
    output_type=StepExecutionResult,
)


def append_execution_result(ctx: WorkflowContext, result: StepExecutionResult) -> None:
    entry = result.model_dump()
    ctx.execution_log.append(entry)
    ctx.shared_memory[result.step_id] = {
        "status": result.status,
        "summary": result.summary,
        "facts": [fact.model_dump() for fact in result.facts],
    }


if __name__ == "__main__":
    workflow_context = WorkflowContext(user_id="user_123")
    workflow_context.original_request = (
        "Check order ORD-1001, verify the payment, create a refund case if everything "
        "looks valid, and then tell me what happened."
    )

    planner_result = Runner.run_sync(
        starting_agent=planner_agent,
        input=workflow_context.original_request,
        context=workflow_context,
    )
    plan = planner_result.final_output
    workflow_context.planner_output = plan.model_dump()

    for step in plan.steps:
        step_input = json.dumps(
            {
                "goal": plan.goal,
                "step": step.model_dump(),
                "success_criteria": plan.success_criteria,
            },
            indent=2,
        )
        execution_result = Runner.run_sync(
            starting_agent=executor_agent,
            input=step_input,
            context=workflow_context,
        ).final_output
        append_execution_result(workflow_context, execution_result)

    print("PLANNER OUTPUT:\n")
    print(json.dumps(plan.model_dump(), indent=2))

    print("\nEXECUTION LOG:\n")
    print(json.dumps(workflow_context.execution_log, indent=2))

    print("\nSHARED MEMORY:\n")
    print(json.dumps(workflow_context.shared_memory, indent=2))

    print("\nPHASE 5 ANSWERS:\n")
    print(
        "1. Memory is passed between Planner and Executor through the shared "
        "WorkflowContext object. The plan, execution log, and derived facts are "
        "stored there and exposed to the executor via fetch_shared_memory."
    )
    print(
        "2. Consistency is maintained by using structured planner output, stable "
        "step IDs, explicit dependencies, and a single shared memory object that "
        "is updated after every step."
    )
    print(
        "3. The biggest architectural advantage over raw API chaining is separation "
        "of concerns: planning stays explicit and inspectable, while execution stays "
        "focused, tool-driven, and easier to recover or replay step by step."
    )

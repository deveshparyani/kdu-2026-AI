from agents import Agent, Runner, function_tool
import asyncio
import logging
from dotenv import load_dotenv
from circuit_breaker import CircuitBreaker

load_dotenv()
logging.basicConfig(level=logging.INFO)

count = 0
breaker = CircuitBreaker(failure_threshold=3)


def _simulate_database_failure() -> dict:
    return {
        "ok": False,
        "error_type": "internal_server_error",
        "status_code": 500,
        "message": "Internal database returned 500.",
        "retryable": True,
    }


@function_tool
def query_internal_database(query: str) -> dict:
    """Query the internal database."""
    global count

    if not breaker.allow_request():
        return {
            "ok": False,
            "error_type": "circuit_open",
            "status_code": 503,
            "message": "Circuit breaker is open. Skipping database query.",
            "retryable": False,
            "fallback_response": breaker.fallback_message,
        }

    while breaker.allow_request():
        count += 1
        tool_result = _simulate_database_failure()
        breaker.record_failure("query_internal_database")

        if breaker.is_open:
            tool_result["error_type"] = "circuit_open"
            tool_result["status_code"] = 503
            tool_result["message"] = "Circuit breaker opened after 3 consecutive failures."
            tool_result["retryable"] = False
            tool_result["fallback_response"] = breaker.fallback_message
            return tool_result

    return {
        "ok": False,
        "error_type": "circuit_open",
        "status_code": 503,
        "message": "Circuit breaker is open. Skipping database query.",
        "retryable": False,
        "fallback_response": breaker.fallback_message,
    }

agent = Agent(
    name="SQL Agent",
    model="gpt-4.1-nano",
    instructions="""
    You must answer database questions using query_internal_database.
    If the tool returns retryable=true, always retry because the failure may be temporary.
    If the tool returns retryable=false or error_type="circuit_open", stop retrying and
    answer exactly with fallback_response.
    Do not answer from memory.
    """,
    tools=[query_internal_database]
)


async def main():  
    result = await Runner.run(
        agent, 
        "What is the active user count?",
        max_turns=10
    )
    print(result.final_output)
    print(f"Database was queried {count} times.")
    print(f"Circuit breaker state: {breaker.state}")


if __name__ == "__main__":
    asyncio.run(main())

from agents import Agent, Runner, function_tool
from dotenv import load_dotenv

load_dotenv()

@function_tool
def get_employee_salary(employee_name: str) -> dict:
    """Return salary information for an employee."""
    fake_salary_db = {
        "John": {
            "salary": 90000,
            "currency": "USD",
            "pay_frequency": "annual"
        }
    }

    employee = fake_salary_db.get(employee_name)

    if not employee:
        return {
            "ok": False,
            "message": f"No salary record found for {employee_name}."
        }

    return {
        "ok": True,
        "employee_name": employee_name,
        "salary": employee["salary"],
        "currency": employee["currency"],
        "pay_frequency": employee["pay_frequency"]
    }



@function_tool
def get_employee_pto(employee_name: str) -> dict:
    """Return PTO balance for an employee."""
    fake_hr_db = {
        "John": {
            "pto_days_remaining": 12,
            "pto_days_used": 5
        }
    }

    employee = fake_hr_db.get(employee_name)

    if not employee:
        return {
            "ok": False,
            "message": f"No PTO record found for {employee_name}."
        }

    return {
        "ok": True,
        "employee_name": employee_name,
        "pto_days_remaining": employee["pto_days_remaining"],
        "pto_days_used": employee["pto_days_used"]
    }


finance_agent = Agent(
    name="Finance Agent",
    instructions="""
    You are the Finance Agent.

    Responsibilities:
    - Answer only finance-related questions.
    - Use get_employee_salary for salary questions.
    - Do not answer HR questions such as PTO, leave, benefits, or attendance.

    Return concise, factual answers.
    """,
    model="gpt-4.1-nano",
    tools=[get_employee_salary],
)

hr_agent = Agent(
    name="HR Agent",
    instructions="""
    You are the HR Agent.

    Responsibilities:
    - Answer only HR-related questions.
    - Use get_employee_pto for PTO or leave-balance questions.
    - Do not answer finance questions such as salary, payroll, or banking details.

    Return concise, factual answers.
    """,
    model="gpt-4.1-nano",
    tools=[get_employee_pto],
)



coordinator_agent = Agent(
    name="Coordinator Agent",
    instructions="""
    You are the Coordinator Agent.

    Your job:
    - Understand the user's request.
    - Delegate salary/payroll questions to the Finance Agent tool.
    - Delegate PTO/leave questions to the HR Agent tool.
    - If the user asks about both domains, call both specialist agents.
    - Combine their answers into one final response.

    Important:
    - You do not have direct access to finance or HR databases.
    - Do not invent salary or PTO data.
    - Always use the correct specialist agent for each domain.
    """,
    model="gpt-4.1-nano",
    tools=[
        finance_agent.as_tool(
            tool_name="ask_finance_agent",
            tool_description="Ask the Finance Agent about salary, payroll, or banking details."
        ),
        hr_agent.as_tool(
            tool_name="ask_hr_agent",
            tool_description="Ask the HR Agent about PTO, leave balance, or HR details."
        ),
    ],
)



if __name__ == "__main__":
    result = Runner.run_sync(
        coordinator_agent,
        "What is John's salary and how much PTO does he have?"
    )

    print(result.final_output)
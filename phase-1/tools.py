import random

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class FlakyToolInput(BaseModel):
    query: str = Field(..., description="The research query to process.")


class FlakyResearchTool(BaseTool):
    name: str = "Flaky Research Tool"
    description: str = (
        "A deliberately unreliable research tool. "
        "It raises TimeoutError about 50% of the time. "
        "Use it to simulate production tool instability."
    )
    args_schema: type[BaseModel] = FlakyToolInput

    def _run(self, query: str) -> str:
        if random.random() < 0.5:
            raise TimeoutError("Simulated timeout from Flaky Research Tool")

        return (
            f"Flaky Research Tool succeeded for query: {query}. "
            "Supplemental finding: production multi-agent systems need "
            "retry logic, fallback tools, monitoring, state tracking, and "
            "clear failure boundaries."
        )
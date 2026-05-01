import json
import re
from typing import List, Literal, Optional

from crewai import Crew, Process
from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel, Field

from agents import create_agents
from tasks import (
    create_fact_check_task,
    create_research_task,
    create_revision_task,
    create_writing_task,
)


class ResearchState(BaseModel):
    topic: str = ""
    research_output: Optional[str] = None
    fact_check_status: Optional[Literal["APPROVED", "NEEDS_REVISION"]] = None
    fact_check_issues: List[str] = Field(default_factory=list)
    final_report: Optional[str] = None

    revision_count: int = 0
    max_revisions: int = 2


class ResearchFlow(Flow[ResearchState]):
    """
    Phase 3 Flow.

    This Flow demonstrates:
    1. structured state using Pydantic,
    2. fact-checker-driven decision making,
    3. guarded retry loop,
    4. every revision is fact-checked again,
    5. writer only runs after approval.
    """

    def __init__(self, agents_config: dict, tasks_config: dict, llm):
        super().__init__()
        self.agents_config = agents_config
        self.tasks_config = tasks_config
        self.llm = llm

    @start()
    def start_flow(self):
        self.state.topic = "CrewAI Flow state management and guarded research revision"
        print("\nStarting Phase 3 Flow")
        print("Topic:", self.state.topic)

        return self.state.topic

    @listen(start_flow)
    def run_research_cycle(self, topic: str):
        """
        This is the main event-driven workflow step.

        The Fact-Checker output determines what happens next:

        APPROVED:
            Writer runs.

        NEEDS_REVISION:
            Researcher revises.
            Then Fact-Checker checks again.

        max_revisions reached:
            Stop with warning.
        """

        print("\nSTEP 1: Running initial research")
        self.state.research_output = self.run_research_task(topic)

        print("\nSTEP 2: Running initial fact-check")
        self.run_fact_check_task(topic)

        while (
            self.state.fact_check_status == "NEEDS_REVISION"
            and self.state.revision_count < self.state.max_revisions
        ):
            self.state.revision_count += 1

            print("\nRevision required")
            print(f"Revision attempt: {self.state.revision_count}/{self.state.max_revisions}")
            print("Issues:", self.state.fact_check_issues)

            self.state.research_output = self.run_revision_task(
                topic=topic,
                research_output=self.state.research_output or "",
                issues=self.state.fact_check_issues,
            )

            print("\nFact-checking revised research")
            self.run_fact_check_task(topic)

        if self.state.fact_check_status == "APPROVED":
            print("\nResearch approved. Running Writer.")
            self.state.final_report = self.run_writer_task(topic)
        else:
            print("\nMax revisions reached. Stopping with warning.")
            self.state.final_report = self.stop_with_warning()

        return self.state.final_report

    def run_research_task(self, topic: str) -> str:
        researcher, _, _ = create_agents(
            agents_config=self.agents_config,
            llm=self.llm,
        )

        research_task = create_research_task(
            config=self.tasks_config["research_task"],
            researcher=researcher,
        )

        crew = Crew(
            agents=[researcher],
            tasks=[research_task],
            process=Process.sequential,
            verbose=True,
            memory=False,
        )

        result = crew.kickoff(
            inputs={
                "topic": topic,
            }
        )

        return str(result)

    def run_fact_check_task(self, topic: str):
        _, fact_checker, _ = create_agents(
            agents_config=self.agents_config,
            llm=self.llm,
        )

        fact_check_task = create_fact_check_task(
            config=self.tasks_config["fact_check_task"],
            fact_checker=fact_checker,
        )

        crew = Crew(
            agents=[fact_checker],
            tasks=[fact_check_task],
            process=Process.sequential,
            verbose=True,
            memory=False,
        )

        raw_result = crew.kickoff(
            inputs={
                "topic": topic,
                "research_output": self.state.research_output or "",
            }
        )

        status, issues, confidence = parse_fact_check_result(str(raw_result))

        self.state.fact_check_status = status
        self.state.fact_check_issues = issues

        print("\nFact-check parsed result")
        print("Status:", status)
        print("Issues:", issues)
        print("Confidence:", confidence)

    def run_revision_task(
        self,
        topic: str,
        research_output: str,
        issues: List[str],
    ) -> str:
        researcher, _, _ = create_agents(
            agents_config=self.agents_config,
            llm=self.llm,
        )

        revision_task = create_revision_task(
            config=self.tasks_config["revision_task"],
            researcher=researcher,
        )

        crew = Crew(
            agents=[researcher],
            tasks=[revision_task],
            process=Process.sequential,
            verbose=True,
            memory=False,
        )

        result = crew.kickoff(
            inputs={
                "topic": topic,
                "research_output": research_output,
                "issues": issues,
            }
        )

        return str(result)

    def run_writer_task(self, topic: str) -> str:
        _, _, writer = create_agents(
            agents_config=self.agents_config,
            llm=self.llm,
        )

        writing_task = create_writing_task(
            config=self.tasks_config["writing_task"],
            writer=writer,
        )

        crew = Crew(
            agents=[writer],
            tasks=[writing_task],
            process=Process.sequential,
            verbose=True,
            memory=False,
        )

        result = crew.kickoff(
            inputs={
                "topic": topic,
                "research_output": self.state.research_output or "",
                "fact_check_status": self.state.fact_check_status or "",
            }
        )

        return str(result)

    def stop_with_warning(self) -> str:
        return (
            "Workflow stopped because maximum revisions were reached.\n\n"
            f"Topic: {self.state.topic}\n\n"
            f"Last fact-check status: {self.state.fact_check_status}\n\n"
            f"Unresolved issues:\n{self.state.fact_check_issues}\n\n"
            f"Last research output:\n{self.state.research_output}"
        )


def parse_fact_check_result(raw: str) -> tuple[str, List[str], str]:
    """
    Fact-checker is instructed to return JSON.

    This helper makes the Flow robust if the LLM wraps JSON in markdown fences
    or produces invalid JSON.

    Valid status values:
    - APPROVED
    - NEEDS_REVISION
    """

    cleaned = strip_markdown_code_fence(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return (
            "NEEDS_REVISION",
            ["Fact-check output was not valid JSON."],
            "low",
        )

    status = str(data.get("status", "NEEDS_REVISION")).upper()

    if status not in {"APPROVED", "NEEDS_REVISION"}:
        status = "NEEDS_REVISION"

    issues = data.get("issues", [])

    if not isinstance(issues, list):
        issues = [str(issues)]

    confidence = str(data.get("confidence", "low")).lower()

    if confidence not in {"low", "medium", "high"}:
        confidence = "low"

    return status, issues, confidence


def strip_markdown_code_fence(text: str) -> str:
    text = text.strip()

    fenced_match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if fenced_match:
        return fenced_match.group(1).strip()

    return text
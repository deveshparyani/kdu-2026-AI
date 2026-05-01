from crewai import Agent
from crewai_tools import SerperDevTool

from tools import FlakyResearchTool


def create_researcher(llm):
    return Agent(
        role="Researcher",
        goal=(
            "Research the given topic using available tools. "
            "Collect useful facts, risks, tradeoffs, and implementation details."
        ),
        backstory=(
            "You are a careful research analyst. You use tools when helpful, "
            "but you also handle tool failures gracefully. If a tool fails, "
            "continue with other available tools and clearly mention uncertainty."
        ),
        tools=[
            SerperDevTool(),
            FlakyResearchTool(),
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def create_fact_checker(llm):
    return Agent(
        role="Fact-Checker",
        goal=(
            "Check the research for weak claims, unsupported statements, "
            "contradictions, and missing evidence."
        ),
        backstory=(
            "You are a strict fact-checking expert. You do not accept vague "
            "or unsupported claims. You identify what is reliable and what "
            "needs improvement."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


def create_writer(llm):
    return Agent(
        role="Writer",
        goal=(
            "Write a clear final report using the research and fact-checking feedback."
        ),
        backstory=(
            "You are a technical writer who converts verified information "
            "into a clean, structured explanation."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


def create_agents(llm):
    researcher = create_researcher(llm)
    fact_checker = create_fact_checker(llm)
    writer = create_writer(llm)

    return researcher, fact_checker, writer
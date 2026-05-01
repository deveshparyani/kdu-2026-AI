from crewai import Crew, Process

from agents import create_agents
from tasks import create_tasks


def create_sequential_crew(llm):
    researcher, fact_checker, writer = create_agents(llm)
    tasks = create_tasks(researcher, fact_checker, writer)

    return Crew(
        agents=[researcher, fact_checker, writer],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )


def create_hierarchical_crew(llm, manager_llm):
    researcher, fact_checker, writer = create_agents(llm)
    tasks = create_tasks(researcher, fact_checker, writer)

    return Crew(
        agents=[researcher, fact_checker, writer],
        tasks=tasks,
        process=Process.hierarchical,
        manager_llm=manager_llm,
        verbose=True,
    )
from crewai import Crew, Process

from agents import create_agents
from tasks import create_tasks


def create_memory_enabled_crew(
    agents_config: dict,
    tasks_config: dict,
    llm,
):
    researcher, fact_checker, writer = create_agents(
        agents_config=agents_config,
        llm=llm,
    )

    tasks = create_tasks(
        tasks_config=tasks_config,
        researcher=researcher,
        fact_checker=fact_checker,
        writer=writer,
    )

    crew = Crew(
        agents=[researcher, fact_checker, writer],
        tasks=tasks,
        process=Process.sequential,
        memory=True,
        verbose=True,
    )

    return crew
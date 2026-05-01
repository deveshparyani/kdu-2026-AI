from crewai import Task


def create_research_task(config: dict, researcher):
    return Task(
        config=config,
        agent=researcher,
    )


def create_fact_check_task(config: dict, fact_checker):
    return Task(
        config=config,
        agent=fact_checker,
    )


def create_revision_task(config: dict, researcher):
    return Task(
        config=config,
        agent=researcher,
    )


def create_writing_task(config: dict, writer):
    return Task(
        config=config,
        agent=writer,
    )
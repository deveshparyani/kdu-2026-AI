from crewai import Task


def create_research_task(config: dict, researcher):
    return Task(
        config=config,
        agent=researcher,
    )


def create_fact_check_task(config: dict, fact_checker, research_task):
    return Task(
        config=config,
        agent=fact_checker,
        context=[research_task],
    )


def create_writing_task(config: dict, writer, research_task, fact_check_task):
    return Task(
        config=config,
        agent=writer,
        context=[research_task, fact_check_task],
    )


def create_tasks(tasks_config: dict, researcher, fact_checker, writer):
    research_task = create_research_task(
        config=tasks_config["research_task"],
        researcher=researcher,
    )

    fact_check_task = create_fact_check_task(
        config=tasks_config["fact_check_task"],
        fact_checker=fact_checker,
        research_task=research_task,
    )

    writing_task = create_writing_task(
        config=tasks_config["writing_task"],
        writer=writer,
        research_task=research_task,
        fact_check_task=fact_check_task,
    )

    return [research_task, fact_check_task, writing_task]
from crewai import Agent


def create_researcher(config: dict, llm):
    return Agent(
        config=config,
        llm=llm,
    )


def create_fact_checker(config: dict, llm):
    return Agent(
        config=config,
        llm=llm,
    )


def create_writer(config: dict, llm):
    return Agent(
        config=config,
        llm=llm,
    )


def create_agents(agents_config: dict, llm):
    researcher = create_researcher(
        config=agents_config["researcher"],
        llm=llm,
    )

    fact_checker = create_fact_checker(
        config=agents_config["fact_checker"],
        llm=llm,
    )

    writer = create_writer(
        config=agents_config["writer"],
        llm=llm,
    )

    return researcher, fact_checker, writer
from crewai import Task


def create_research_task(researcher):
    return Task(
        description=(
            "Research this topic:\n\n"
            "{topic}\n\n"
            "Use the SerperDevTool and the Flaky Research Tool if useful. "
            "The Flaky Research Tool may fail. If it fails, continue with "
            "whatever information you can gather from other tools. "
            "Return useful findings, risks, and important implementation notes."
        ),
        expected_output=(
            "A concise research brief with bullet points covering:\n"
            "1. Key concepts\n"
            "2. Practical implementation notes\n"
            "3. Failure-handling observations\n"
            "4. Risks and tradeoffs\n"
            "5. Any uncertainty caused by tool failures"
        ),
        agent=researcher,
    )


def create_fact_check_task(fact_checker, research_task):
    return Task(
        description=(
            "Review the research brief for the topic:\n\n"
            "{topic}\n\n"
            "Check whether the claims are clear, supported, and internally consistent. "
            "Identify weak claims, missing evidence, contradictions, and uncertainty."
        ),
        expected_output=(
            "A fact-check report with:\n"
            "1. APPROVED or NEEDS_REVISION\n"
            "2. List of weak or unsupported claims\n"
            "3. List of contradictions, if any\n"
            "4. Overall confidence: low, medium, or high"
        ),
        agent=fact_checker,
        context=[research_task],
    )


def create_writing_task(writer, research_task, fact_check_task):
    return Task(
        description=(
            "Write a final report about:\n\n"
            "{topic}\n\n"
            "Use the research brief and fact-checking report. "
            "Do not invent facts. Mention any uncertainty caused by tool failures."
        ),
        expected_output=(
            "A structured final report with these sections:\n"
            "1. Summary\n"
            "2. Research findings\n"
            "3. Fact-checking observations\n"
            "4. Sequential workflow behavior under tool failure\n"
            "5. Hierarchical workflow behavior under tool failure\n"
            "6. Cost explanation\n"
            "7. Conclusion"
        ),
        agent=writer,
        context=[research_task, fact_check_task],
    )


def create_tasks(researcher, fact_checker, writer):
    research_task = create_research_task(researcher)
    fact_check_task = create_fact_check_task(fact_checker, research_task)
    writing_task = create_writing_task(writer, research_task, fact_check_task)

    return [research_task, fact_check_task, writing_task]
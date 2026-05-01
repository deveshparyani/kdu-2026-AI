import os
from pathlib import Path

from dotenv import load_dotenv
from crewai import LLM

from config_loader import load_yaml
from crew_builder import create_memory_enabled_crew


PHASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PHASE_DIR.parent

AGENTS_YAML_PATH = PHASE_DIR / "agents.yaml"
TASKS_YAML_PATH = PHASE_DIR / "tasks.yaml"


def load_environment():
    load_dotenv(PROJECT_ROOT / ".env")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY. Add it to your .env file.")


def create_llm():
    return LLM(
        model="gpt-4.1-nano",
        temperature=0.2,
    )


def run_day(day_label: str, topic: str, agents_config: dict, tasks_config: dict):
    print("\n" + "=" * 80)
    print(f"PHASE 2: {day_label}")
    print("=" * 80)

    crew = create_memory_enabled_crew(
        agents_config=agents_config,
        tasks_config=tasks_config,
        llm=create_llm(),
    )

    result = crew.kickoff(
        inputs={
            "topic": topic,
        }
    )

    print(f"\n{day_label} RESULT:")
    print(result)

    return result


def main():
    load_environment()

    agents_config = load_yaml(AGENTS_YAML_PATH)
    tasks_config = load_yaml(TASKS_YAML_PATH)

    topic = (
        "CrewAI YAML configuration, memory behavior, instruction conflicts, "
        "and multi-agent research workflows"
    )

    day_1_result = run_day(
        day_label="DAY 1 MEMORY RUN",
        topic=topic,
        agents_config=agents_config,
        tasks_config=tasks_config,
    )

    day_2_result = run_day(
        day_label="DAY 2 MEMORY RUN",
        topic=topic,
        agents_config=agents_config,
        tasks_config=tasks_config,
    )


if __name__ == "__main__":
    main()
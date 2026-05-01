import os
from pathlib import Path

from dotenv import load_dotenv
from crewai import LLM

from config_loader import load_yaml
from flow import ResearchFlow


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



def main():
    load_environment()

    agents_config = load_yaml(AGENTS_YAML_PATH)
    tasks_config = load_yaml(TASKS_YAML_PATH)

    flow = ResearchFlow(
        agents_config=agents_config,
        tasks_config=tasks_config,
        llm=create_llm(),
    )

    result = flow.kickoff()

    print("\n" + "=" * 80)
    print("PHASE 3 FINAL RESULT")
    print("=" * 80)
    print(result)

    print("\n" + "=" * 80)
    print("PHASE 3 FINAL STATE")
    print("=" * 80)
    print(flow.state)



if __name__ == "__main__":
    main()
import os
from pathlib import Path

from dotenv import load_dotenv
from crewai import LLM

from crews import create_sequential_crew, create_hierarchical_crew


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def validate_environment():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY. Add it to your .env file.")

    if not os.getenv("SERPER_API_KEY"):
        raise RuntimeError("Missing SERPER_API_KEY. Add it to your .env file.")


def create_llm():
    return LLM(
        model="gpt-4.1-nano",
        temperature=0.2,
    )


def create_manager_llm():
    return LLM(
        model="gpt-4.1-nano",
        temperature=0.1,
    )


def run_sequential(topic: str):
    crew = create_sequential_crew(llm=create_llm())
    return crew.kickoff(inputs={"topic": topic})


def run_hierarchical(topic: str):
    crew = create_hierarchical_crew(
        llm=create_llm(),
        manager_llm=create_manager_llm(),
    )
    return crew.kickoff(inputs={"topic": topic})



def main():
    validate_environment()

    topic = (
        "CrewAI orchestration strategies, tool failure handling, "
        "sequential execution, and hierarchical execution"
    )

    print("\n" + "=" * 80)
    print("PHASE 1: SEQUENTIAL WORKFLOW")
    print("=" * 80)

    try:
        sequential_result = run_sequential(topic)
        print("\nSEQUENTIAL RESULT:")
        print(sequential_result)
    except Exception as error:
        print("\nSEQUENTIAL WORKFLOW FAILED")
        print("Error type:", type(error).__name__)
        print("Error message:", str(error))

    print("\n" + "=" * 80)
    print("PHASE 1: HIERARCHICAL WORKFLOW")
    print("=" * 80)

    try:
        hierarchical_result = run_hierarchical(topic)
        print("\nHIERARCHICAL RESULT:")
        print(hierarchical_result)
    except Exception as error:
        print("\nHIERARCHICAL WORKFLOW FAILED")
        print("Error type:", type(error).__name__)
        print("Error message:", str(error))



if __name__ == "__main__":
    main()
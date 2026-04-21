"""Tests for node functions and QA helpers."""

from src.models import ModelBundle
from src.nodes import (
    make_history_summary_node,
    make_qa_node,
    make_refine_node,
    make_summarize_node,
)
from src.qa import (
    answer_ambiguous_followup,
    answer_question,
    answer_memory_question,
    build_qa_prompt,
    is_detail_question,
)
from src.text_helpers import should_keep_original_summary
from src.utils import build_refinement_prompt, clean_generated_summary


class FakeSummarizer:
    """Simple fake summarizer used in tests."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, text: str, **_: object) -> list[dict[str, str]]:
        self.calls.append(text)
        return [{"summary_text": f"summary::{text[:25]}"}]


class FakeRefiner:
    """Simple fake refinement model used in tests."""

    class Tokenizer:
        def encode(self, text: str, add_special_tokens: bool = False) -> list[str]:
            return text.split()

    def __init__(self) -> None:
        self.tokenizer = self.Tokenizer()

    def __call__(self, prompt: str, **_: object) -> list[dict[str, str]]:
        return [{"generated_text": f"refined::{prompt[:25]}"}]


class FakeTokenizer:
    """Simple fake tokenizer used in tests."""

    def encode(self, text: str, add_special_tokens: bool = False) -> list[str]:
        return text.split()

    def __call__(
        self,
        text: str,
        return_tensors: str = "pt",
        truncation: bool = True,
        max_length: int = 512,
    ) -> dict[str, object]:
        return {"input_ids": FakeTensor(text)}

    def decode(self, tokens: object, skip_special_tokens: bool = True) -> str:
        return str(tokens)


class FakeTensor:
    """Fake tensor wrapper with a no-op device transfer."""

    def __init__(self, text: str) -> None:
        self.text = text

    def to(self, device: object) -> "FakeTensor":
        return self


class FakeQAModel:
    """Simple fake seq2seq QA model used in tests."""

    def __init__(self) -> None:
        self.device = "cpu"

    def generate(self, **kwargs: object) -> list[str]:
        input_ids = kwargs["input_ids"]
        return [f"answer::{input_ids.text[:25]}"]


def test_summarize_node_returns_summary() -> None:
    bundle = ModelBundle(
        summarizer=FakeSummarizer(),
        refiner=FakeRefiner(),
        qa_tokenizer=FakeTokenizer(),
        qa_model=FakeQAModel(),
    )
    node = make_summarize_node(bundle)

    result = node({"input_text": "This is a short source document for testing."})

    assert result["summary"].startswith("summary::")


def test_refine_node_sets_context() -> None:
    bundle = ModelBundle(
        summarizer=FakeSummarizer(),
        refiner=FakeRefiner(),
        qa_tokenizer=FakeTokenizer(),
        qa_model=FakeQAModel(),
    )
    node = make_refine_node(bundle)

    result = node(
        {
            "input_text": "Original source text with extra details.",
            "summary": "summary text",
            "summary_length": "short",
        }
    )

    assert result["refined_summary"]


def test_answer_question_returns_generated_text() -> None:
    bundle = ModelBundle(
        summarizer=FakeSummarizer(),
        refiner=FakeRefiner(),
        qa_tokenizer=FakeTokenizer(),
        qa_model=FakeQAModel(),
    )

    answer = answer_question(
        model_bundle=bundle,
        prompt="Current question:\nWhat is the topic?",
    )

    assert answer.startswith("answer::")


def test_qa_node_appends_memory_turn() -> None:
    bundle = ModelBundle(
        summarizer=FakeSummarizer(),
        refiner=FakeRefiner(),
        qa_tokenizer=FakeTokenizer(),
        qa_model=FakeQAModel(),
    )
    node = make_qa_node(bundle)

    result = node(
        {
            "input_text": "The city program improved transport and health access.",
            "refined_summary": "The program improved transport and health access.",
            "conversation_history": [],
            "history_summary": None,
            "user_query": "What improved?",
            "is_exit": False,
        }
    )

    assert "What improved?" in result["conversation_history"][0]
    assert result["qa_response"] is not None


def test_history_summary_node_compacts_old_turns() -> None:
    bundle = ModelBundle(
        summarizer=FakeSummarizer(),
        refiner=FakeRefiner(),
        qa_tokenizer=FakeTokenizer(),
        qa_model=FakeQAModel(),
    )
    node = make_history_summary_node(
        model_bundle=bundle,
        history_token_limit=5,
        keep_recent_turns=2,
    )

    result = node(
        {
            "conversation_history": [
                "User: Q1\nAssistant: A1",
                "User: Q2\nAssistant: A2",
                "User: Q3\nAssistant: A3",
            ],
            "history_summary": None,
        }
    )

    assert result["history_summary"].startswith("refined::")
    assert len(result["conversation_history"]) == 2


def test_build_qa_prompt_uses_document_and_summary() -> None:
    prompt = build_qa_prompt(
        state={
            "input_text": "The city launched a program for transport and health.",
            "refined_summary": "Important facts.",
            "user_query": "What changed in the program?",
        },
        tokenizer=None,
        max_prompt_tokens=200,
    )

    assert "The city launched a program" in prompt
    assert "Important facts." in prompt
    assert "What changed in the program?" in prompt
    assert "recent conversation" not in prompt.lower()


def test_build_refinement_prompt_uses_requested_length() -> None:
    prompt = build_refinement_prompt("summary text", "long")

    assert "Requested length: long." in prompt
    assert "7 to 10 sentences" in prompt
    assert "Draft summary:" in prompt


def test_clean_generated_summary_removes_repetition() -> None:
    cleaned = clean_generated_summary(
        "The program improved transport. The program improved transport. It also added clinics."
    )

    assert cleaned == "The program improved transport. It also added clinics."


def test_answer_memory_question_returns_last_question() -> None:
    answer = answer_memory_question(
        {
            "conversation_history": [
                "User: What is the topic?\nAssistant: The topic is transport.",
            ]
        },
        "What was my last question?",
    )

    assert answer == "What is the topic?"


def test_is_detail_question_detects_detail_requests() -> None:
    assert is_detail_question("Details of the program")
    assert is_detail_question("What kind of program is it?")
    assert not is_detail_question("What is the program about?")


def test_qa_node_answers_memory_question_without_model_lookup() -> None:
    bundle = ModelBundle(
        summarizer=FakeSummarizer(),
        refiner=FakeRefiner(),
        qa_tokenizer=FakeTokenizer(),
        qa_model=FakeQAModel(),
    )
    node = make_qa_node(bundle)

    result = node(
        {
            "input_text": "Document text.",
            "refined_summary": "Refined summary.",
            "conversation_history": [
                "User: What is the topic?\nAssistant: The topic is transport.",
            ],
            "history_summary": None,
            "user_query": "What was my last question?",
            "is_exit": False,
        }
    )

    assert result["qa_response"] == "What is the topic?"


def test_answer_ambiguous_followup_requests_clarification() -> None:
    answer = answer_ambiguous_followup("why")

    assert answer == "Please ask a more specific question so I can answer it correctly."


def test_refine_node_keeps_original_when_refinement_drops_topic() -> None:
    class OffTopicRefiner(FakeRefiner):
        def __call__(self, prompt: str, **_: object) -> list[dict[str, str]]:
            return [{"generated_text": "Weekly clinic screenings increased."}]

    bundle = ModelBundle(
        summarizer=FakeSummarizer(),
        refiner=OffTopicRefiner(),
        qa_tokenizer=FakeTokenizer(),
        qa_model=FakeQAModel(),
    )
    node = make_refine_node(bundle)

    result = node(
        {
            "input_text": "Source text.",
            "summary": "The city launched a pilot program for transport and digital literacy.",
            "summary_length": "medium",
        }
    )

    assert result["refined_summary"] == "The city launched a pilot program for transport and digital literacy."


def test_should_keep_original_summary_detects_topic_loss() -> None:
    assert should_keep_original_summary(
        "The city launched a pilot program for transport and digital literacy.",
        "Weekly clinic screenings increased.",
        "medium",
    )

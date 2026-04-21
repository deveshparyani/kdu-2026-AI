"""Tests for LangGraph workflow wiring."""

from src.graph import build_assistant_graph, build_qa_graph, run_assistant_workflow
from src.models import ModelBundle


class FakeSummarizer:
    """Fake summarizer for graph tests."""

    def __call__(self, text: str, **_: object) -> list[dict[str, str]]:
        return [{"summary_text": f"summary::{text[:20]}"}]


class FakeRefiner:
    """Fake refiner for graph tests."""

    class Tokenizer:
        def encode(self, text: str, add_special_tokens: bool = False) -> list[str]:
            return text.split()

    def __init__(self) -> None:
        self.tokenizer = self.Tokenizer()

    def __call__(self, prompt: str, **_: object) -> list[dict[str, str]]:
        return [{"generated_text": f"refined::{prompt[:20]}"}]


class FakeTokenizer:
    """Fake tokenizer for graph tests."""

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
    """Fake seq2seq model for graph tests."""

    def __init__(self) -> None:
        self.device = "cpu"

    def generate(self, **_: object) -> list[str]:
        return ["unused"]


def test_build_assistant_graph_runs_end_to_end() -> None:
    bundle = ModelBundle(
        summarizer=FakeSummarizer(),
        refiner=FakeRefiner(),
        qa_tokenizer=FakeTokenizer(),
        qa_model=FakeQAModel(),
    )
    app = build_assistant_graph(bundle)

    result = app.invoke({"input_text": "This is a graph test document."})

    assert result["summary"].startswith("summary::")
    assert result["refined_summary"]


def test_run_assistant_workflow_uses_provided_bundle() -> None:
    bundle = ModelBundle(
        summarizer=FakeSummarizer(),
        refiner=FakeRefiner(),
        qa_tokenizer=FakeTokenizer(),
        qa_model=FakeQAModel(),
    )

    result = run_assistant_workflow(
        input_text="Another test document.",
        summary_length="long",
        model_bundle=bundle,
    )

    assert result["summary"].startswith("summary::")
    assert result["refined_summary"]
    assert result["summary_length"] == "long"


def test_qa_graph_uses_checkpointer_memory() -> None:
    bundle = ModelBundle(
        summarizer=FakeSummarizer(),
        refiner=FakeRefiner(),
        qa_tokenizer=FakeTokenizer(),
        qa_model=FakeQAModel(),
    )
    app = build_qa_graph(bundle, history_token_limit=100)
    config = {"configurable": {"thread_id": "test-thread"}}

    app.invoke(
        {
            "input_text": "doc",
            "summary_length": "medium",
            "summary": "summary",
            "refined_summary": "refined summary",
            "user_query": None,
            "qa_response": None,
            "streamed_answer": None,
            "conversation_history": [],
            "history_summary": None,
            "is_exit": False,
        },
        config=config,
    )
    result = app.invoke({"user_query": "What happened?", "qa_response": None}, config=config)

    assert result["qa_response"] == "unused"
    assert len(result["conversation_history"]) == 1

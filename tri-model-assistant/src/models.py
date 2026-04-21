"""Model loading helpers for the local assistant."""

from dataclasses import dataclass

import torch
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    Pipeline,
    PreTrainedModel,
    PreTrainedTokenizerBase,
    pipeline,
)

DEFAULT_SUMMARIZATION_MODEL = "sshleifer/distilbart-cnn-12-6"
DEFAULT_REFINEMENT_MODEL = "google/flan-t5-base"
DEFAULT_QA_MODEL = "google/flan-t5-base"


@dataclass
class ModelBundle:
    """Bundle of pipelines used by the application."""

    summarizer: Pipeline
    refiner: Pipeline
    qa_tokenizer: PreTrainedTokenizerBase
    qa_model: PreTrainedModel


def get_default_device() -> int:
    """Use GPU when available, otherwise fall back to CPU."""

    return 0 if torch.cuda.is_available() else -1


def load_model_bundle(
    summarization_model: str = DEFAULT_SUMMARIZATION_MODEL,
    refinement_model: str = DEFAULT_REFINEMENT_MODEL,
    qa_model: str = DEFAULT_QA_MODEL,
    device: int | None = None,
) -> ModelBundle:
    """Load all three local Hugging Face pipelines."""

    resolved_device = get_default_device() if device is None else device

    summarizer = pipeline(
        task="summarization",
        model=summarization_model,
        device=resolved_device,
    )
    refiner = pipeline(
        task="text2text-generation",
        model=refinement_model,
        device=resolved_device,
    )
    qa_tokenizer = AutoTokenizer.from_pretrained(qa_model)
    qa_model_instance = AutoModelForSeq2SeqLM.from_pretrained(qa_model)

    if resolved_device >= 0:
        qa_model_instance = qa_model_instance.to(f"cuda:{resolved_device}")

    return ModelBundle(
        summarizer=summarizer,
        refiner=refiner,
        qa_tokenizer=qa_tokenizer,
        qa_model=qa_model_instance,
    )

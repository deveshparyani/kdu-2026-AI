# Tri-Model AI Assistant

This project is a small, assignment-friendly Python application that runs a
local tri-model assistant with LangGraph and Hugging Face Transformers.

The assistant uses three model roles:

1. A summarization model to compress the source text.
2. A refinement model to clean up and improve the summary.
3. A question answering model to answer follow-up questions from the refined
   summary.

## Default Models

- Summarization: `sshleifer/distilbart-cnn-12-6`
- Refinement: `google/flan-t5-base`
- Question answering: `google/flan-t5-base`

## Project Layout

```text
tri-model-ai-assistant/
├── README.md
├── .gitignore
├── app.py
├── pyproject.toml
├── docs/
│   └── design_notes.md
├── src/
│   ├── __init__.py
│   ├── state.py
│   ├── models.py
│   ├── nodes.py
│   ├── graph.py
│   ├── utils.py
│   └── cli.py
├── tests/
│   ├── __init__.py
│   ├── test_state.py
│   ├── test_nodes.py
│   └── test_graph.py
└── sample_data/
    └── sample_input.txt
```

## Setup With uv

```bash
uv sync
```

This creates the local `.venv` and the `uv.lock` file.

## Run The App

```bash
uv run python app.py
```

You can also load text from a file:

```bash
uv run python app.py --input-file sample_data/sample_input.txt
```

If no file is provided, the app asks you to paste text into the terminal. Type
`END` on a new line to finish the input.

## Run Tests

```bash
uv run pytest
```

## Notes

- The first run may take some time because the Hugging Face models are
  downloaded locally.
- The QA loop continues until you type `exit`.
- The question answering model only sees the refined summary, which keeps the
  design simple and easy to explain in an academic submission.

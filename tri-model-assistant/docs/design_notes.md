# Design Notes

## Goal

The goal of this project is to show a simple multi-step AI workflow that uses
three different local model roles in a clean and modular way.

## Workflow

The application uses a `LangGraph` `StateGraph` with two main processing nodes:

1. `summarize`
2. `refine`

The question answering step is kept outside the graph because it runs in a loop
after the summary has already been prepared. This keeps the graph small and
easy to explain in a student assignment while still using the refined summary as
the QA context.

## Large Input Handling

The summarization model has practical input limits, so the project includes a
simple text chunking helper. Large text is split into word-based chunks, each
chunk is summarized, and the partial summaries are merged. If needed, the merged
summary is summarized one more time to keep it compact.

## Why This Structure

- `state.py` stores the shared state contract.
- `models.py` loads the local Hugging Face pipelines.
- `nodes.py` keeps graph logic separate from CLI code.
- `graph.py` builds the LangGraph workflow.
- `cli.py` handles user interaction.
- `utils.py` contains reusable helpers.

This makes the project easier to read, test, and submit as coursework.

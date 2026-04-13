# Stock Trading Agent

## LangSmith Observability

Set these environment variables before running traced sessions:

```bash
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=stock-trading-agent
```

Then run the CLI:

```bash
./.venv/bin/python main.py
```

This logs agent execution to LangSmith and prints local token and estimated cost observations in the terminal.

## Evaluation

Run the basic evaluation suite with LangSmith:

```bash
./.venv/bin/python -m app.analytics.evaluate_agent
```

The evaluation uses examples from `app/data/evaluation_examples.json`.

## Trace Reporting

Fetch recent LangSmith trace summaries for a project:

```bash
./.venv/bin/python -m app.analytics.report_langsmith
```

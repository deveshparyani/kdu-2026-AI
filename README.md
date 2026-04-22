# KDU OpenAI Chatbot

This project now has:

- a `FastAPI` backend in `main.py`
- a `Streamlit` chatbot frontend in `app.py`
- a reusable OpenAI chat service in `services/chat_service.py`

## What the backend does

The backend accepts the full chat history, sends it to the OpenAI Responses API, handles tool calls for:

- weather
- calculator
- built-in web search

and then returns the assistant reply plus token usage.

## Setup

Create a `.env` file with:

```env
OPENAI_API_KEY=your_openai_api_key
WEATHER_API_KEY=your_openweathermap_api_key
OPENAI_MODEL=gpt-5-nano
```

Optional usage-cost settings:

```env
OPENAI_INPUT_COST_PER_MILLION=0.00
OPENAI_OUTPUT_COST_PER_MILLION=0.00
```

## Install dependencies

```bash
pip install -r requirements.txt
```

or with `uv`:

```bash
uv sync
```

## Run the backend

```bash
uvicorn main:app --reload
```

Backend URLs:

- `GET /health`
- `POST /chat`

## Run the frontend

```bash
streamlit run app.py
```

If your backend is running on a different host or port:

```bash
CHAT_BACKEND_URL=http://127.0.0.1:8000 streamlit run app.py
```

## Example request

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is the weather in Mumbai and what is 12 * 17?"}
    ]
  }'
```

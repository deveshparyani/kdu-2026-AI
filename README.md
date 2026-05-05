# Travel Booking AI Agent

This repository is a beginner-friendly monorepo for a travel booking AI assignment.

The current version is an actual chatbot application:

- `backend/` is a local FastAPI server.
- `frontend/` is a React + Vite chat application.
- ChatKit-specific integration points are still marked with `TODO` comments.

This starter does **not** connect directly to OpenAI-hosted Agent Builder. Instead, the frontend talks to a **local FastAPI backend**, and that backend is where you can later add ChatKit SDK logic and OpenAI calls.

## Project layout

```text
chatkit-travel-agent/
  backend/   # Local FastAPI app
  frontend/  # React + Vite chat interface
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- npm
- `uv` for Python package management

## 1. Install `uv`

On macOS or Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

You can also check the install worked with:

```bash
uv --version
```

## 2. Create your environment file

From the project root:

```bash
cp .env.example .env
```

Then open `.env` and set:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-nano
```

`gpt-4.1-nano` is the default model used by this starter because it is small, fast, and easy to experiment with while learning.

## 3. Set up and run the backend

```bash
cd backend
uv venv
source .venv/bin/activate
uv sync
uv run python -m uvicorn app.main:app --reload
```

The FastAPI server will start at `http://localhost:8000`.

## 4. Set up and run the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite app will start at `http://localhost:5173`.

## 5. What this project already does

- shows a real travel chatbot UI
- streams or simulates streaming assistant responses
- renders travel offer widgets inline in the conversation
- validates secure thread ownership on every sensitive backend route
- sends hidden `Book Now` actions through the backend
- supports simple human handoff mode
- keeps the OpenAI model name in one config place
- highlights where future ChatKit SDK code belongs

## 6. What you will add later

- real ChatKit Python SDK wiring in the backend
- real ChatKit frontend bindings if your assignment needs them
- real travel tools such as search, booking, or handoff flows
- better authentication and production-grade security

## Learning note

This repo is designed to be read in small steps. Start with:

1. `backend/app/main.py`
2. `backend/app/chatkit_server.py`
3. `frontend/src/components/ChatApp.tsx`

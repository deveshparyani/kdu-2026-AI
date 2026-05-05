# Frontend

This frontend is a plain React + TypeScript app built with Vite.

It talks to the FastAPI backend only. The browser never receives `OPENAI_API_KEY`.

## Install

```bash
cd frontend
npm install
```

## Run the frontend

```bash
npm run dev
```

Vite runs on:

- `http://localhost:5173`

The FastAPI backend should run on:

- `http://localhost:8000`

## What this frontend does

- renders a real chatbot conversation window
- lets you switch between `user_a` and `user_b`
- creates secure chat threads through `POST /api/chat/session`
- streams or simulates streaming assistant replies from `POST /api/chat/stream`
- renders travel offer widgets inline inside assistant messages
- sends hidden widget actions to `POST /api/chat/action`
- keeps human handoff controls as a secondary panel
- keeps the manual `thread_id` ownership test inside a collapsible security panel

## Start the backend

In another terminal:

```bash
cd ../backend
uv run python -m uvicorn app.main:app --reload
```

## How to demo the chatbot

1. Select `user_a`.
2. Click `New Thread`.
3. Send: `Find me a weekend trip to Goa under 10000`
4. Watch the assistant response stream into the chat window.
5. Click `Book Now` inside the inline travel widget.
6. Start human handoff from the side panel.
7. Send another message and confirm the backend returns the AI paused response.

## How to test thread isolation

1. Create a thread as `user_a`.
2. Copy the current `thread_id`.
3. Switch to `user_b`.
4. Open the `Security Test` panel.
5. Paste `user_a`'s thread id.
6. Click `Continue Thread`.
7. Confirm that the app shows a `403` access denied style error from the backend.

## ChatKit note

The file `src/components/ChatKitMountPoint.tsx` is where the official ChatKit UI should be mounted later.

For now, the project keeps a custom chat UI and leaves `TODO` comments where official ChatKit UI or ChatKit stream events would connect later.

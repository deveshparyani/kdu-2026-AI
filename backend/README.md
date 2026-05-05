# Backend

This backend implements Phase 1: Session Security and Thread Isolation.

It uses:

- FastAPI
- `uv`
- in-memory storage for users, threads, and sessions
- a demo authentication header: `X-Demo-User-Id`

## What this phase teaches

1. The backend decides who the user is.
2. The frontend must not be trusted to send `user_id` in the request body.
3. A thread must only be reusable by its owner.
4. This server-side ownership check prevents IDOR style cross-user access.

## Run with `uv`

```bash
cd backend
uv venv
source .venv/bin/activate
uv sync
uv run python -m uvicorn app.main:app --reload
```

The backend will run at `http://localhost:8000`.

## Run tests

```bash
cd backend
uv run pytest
```

## If you see `ModuleNotFoundError: No module named 'app'`

That usually means one of these happened:

1. You ran the command from the wrong folder.
2. Another old virtual environment is still active.

Use this safest version:

```bash
cd backend
uv run python -m uvicorn app.main:app --reload
```

Why this works better:

- `cd backend` makes the local `app/` package importable
- `python -m uvicorn` uses the project Python instead of an older `uvicorn` command left on your shell path

If you still see paths from another project, deactivate the old environment first:

```bash
deactivate
```

## Endpoints

- `GET /health`
- `POST /api/chat/session`
- `GET /api/threads`
- `POST /api/debug/create-thread`

## Test with `curl`

Create a session for `user_a`:

```bash
curl -X POST http://localhost:8000/api/chat/session \
  -H "Content-Type: application/json" \
  -H "X-Demo-User-Id: user_a" \
  -d '{}'
```

Continue an existing thread for `user_a`:

```bash
curl -X POST http://localhost:8000/api/chat/session \
  -H "Content-Type: application/json" \
  -H "X-Demo-User-Id: user_a" \
  -d '{"thread_id":"thread_replace_me"}'
```

List only `user_a` threads:

```bash
curl http://localhost:8000/api/threads \
  -H "X-Demo-User-Id: user_a"
```

Create a demo thread directly:

```bash
curl -X POST http://localhost:8000/api/debug/create-thread \
  -H "X-Demo-User-Id: user_a"
```

## Simulate `user_a` and `user_b`

The header changes the authenticated demo user:

- `X-Demo-User-Id: user_a`
- `X-Demo-User-Id: user_b`

Example:

```bash
curl http://localhost:8000/api/threads -H "X-Demo-User-Id: user_a"
curl http://localhost:8000/api/threads -H "X-Demo-User-Id: user_b"
```

Each user should only see their own thread list.

## Demonstrate a hardcoded `thread_id` attack

1. Create a thread as `user_a`.
2. Copy the returned `thread_id`.
3. Try to reuse that same `thread_id` as `user_b`.

Example attack:

```bash
curl -X POST http://localhost:8000/api/chat/session \
  -H "Content-Type: application/json" \
  -H "X-Demo-User-Id: user_b" \
  -d '{"thread_id":"thread_replace_me"}'
```

Expected result:

- the server returns `403 Forbidden`
- the backend refuses cross-user thread access

## ChatKit note

All ChatKit-specific client secret creation is isolated inside:

- `app/chatkit_server.py`

The rest of the backend calls only:

- `create_chatkit_client_secret(user_id, thread_id)`

That keeps OpenAI-specific code away from the route and ownership logic, and it ensures `OPENAI_API_KEY` is never exposed to the frontend.

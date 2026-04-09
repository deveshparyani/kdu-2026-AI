# FastAPI Template

Reusable FastAPI template with async SQLAlchemy, env-driven configuration, configurable authentication identifiers, standardized error handling, structured logging, and production-friendly testing defaults.

## What This Template Includes

- FastAPI app factory with centralized middleware, exception handlers, and OpenAPI setup
- Async SQLAlchemy foundation with Alembic migrations
- Configurable auth identifier mode: `email`, `username`, or `either`
- Registration, login, refresh, logout, password reset, email verification, and protected-route example flows
- Structured JSON logging and standardized error responses
- Isolated pytest setup with API, service, repository, and security coverage
- Container and CI assets for repeatable local and pipeline execution

## Quick Start

1. Create a virtual environment and install dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

2. Copy the example environment file.

```bash
cp .env.example .env
```

3. Update the required values at minimum:

- `DATABASE_URL`
- `AUTH_JWT_SECRET`
- `SECRET_KEY`
- `APP_BASE_URL`

4. Run migrations.

```bash
alembic upgrade head
```

5. Start the app.

```bash
uvicorn app.main:app --reload
```

## Project Layout

```text
app/
  api/
    dependencies/
    routes/
  core/
  db/
  models/
  repositories/
  schemas/
  services/
alembic/
docs/
tests/
```

## Current API Surface

- `GET /api/v1/health`
- `GET /api/v1/health/ready`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`
- `POST /api/v1/auth/email-verification/request`
- `POST /api/v1/auth/email-verification/confirm`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/admin`

## Request And Response Examples

Registration with email:

```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```

Registration with username:

```json
{
  "username": "template_user",
  "password": "StrongPass123!"
}
```

Login:

```json
{
  "identifier": "user@example.com",
  "password": "StrongPass123!"
}
```

Token response:

```json
{
  "access_token": "access.jwt.token",
  "refresh_token": "refresh.jwt.token",
  "token_type": "bearer",
  "expires_in": 900,
  "refresh_expires_in": 604800,
  "user": {
    "id": "11111111-1111-1111-1111-111111111111",
    "email": "user@example.com",
    "username": "template_user",
    "role": "user",
    "is_active": true,
    "is_verified": false
  }
}
```

Password reset request:

```json
{
  "identifier": "user@example.com"
}
```

Password reset confirm:

```json
{
  "token": "password.reset.token",
  "new_password": "NewStrongPass123!"
}
```

Email verification request:

```json
{
  "identifier": "user@example.com"
}
```

Readiness response:

```json
{
  "status": "ready",
  "service": "fastapi-template",
  "environment": "production",
  "version": "0.1.0",
  "database": "ok"
}
```

Standard error response:

```json
{
  "detail": {
    "code": "validation_error",
    "message": "Invalid request.",
    "fields": [
      {
        "field": "password",
        "message": "Field required"
      }
    ]
  }
}
```

## Switching Auth Identifier Mode

Set `AUTH_IDENTIFIER_MODE` in `.env`:

- `AUTH_IDENTIFIER_MODE=email`
- `AUTH_IDENTIFIER_MODE=username`
- `AUTH_IDENTIFIER_MODE=either`

Behavior:

- `email`: registration and login require email-compatible identifiers
- `username`: registration and login use username validation rules
- `either`: registration accepts either identifier, and login uses the generic `identifier` field to resolve email or username

When you change auth mode, also review:

- `AUTH_USERNAME_MIN_LENGTH`
- `AUTH_USERNAME_MAX_LENGTH`
- `AUTH_USERNAME_REGEX`
- `AUTH_PASSWORD_REQUIRE_UPPERCASE`
- `AUTH_PASSWORD_REQUIRE_LOWERCASE`
- `AUTH_PASSWORD_REQUIRE_DIGIT`
- `AUTH_PASSWORD_REQUIRE_SPECIAL`
- tests that assume a particular identifier shape

## Configuration Notes

The template is env-driven. Key groups in [.env.example](/Users/devesh/Desktop/Fast-API-Template/.env.example):

- App and OpenAPI metadata
- CORS and trusted hosts
- Database and migration settings
- Authentication and JWT settings
- Logging and observability
- Optional email, worker, storage, and rate limit integrations
- Deployment and startup-safety settings

## Development Commands

Run the app:

```bash
uvicorn app.main:app --reload
```

Create a migration:

```bash
alembic revision --autogenerate -m "describe_change"
```

Apply migrations:

```bash
alembic upgrade head
```

Run checks:

```bash
ruff check .
mypy app tests
pytest
pytest --cov=app --cov-report=term-missing --cov-fail-under=70
```

## Deployment Assets

The template now includes:

- [Dockerfile](/Users/devesh/Desktop/Fast-API-Template/Dockerfile)
- [docker-compose.yml](/Users/devesh/Desktop/Fast-API-Template/docker-compose.yml)
- [ci.yml](/Users/devesh/Desktop/Fast-API-Template/.github/workflows/ci.yml)

Recommended deployment flow:

1. build the image
2. inject environment-specific secrets
3. run `alembic upgrade head`
4. start the ASGI service
5. monitor `GET /api/v1/health` and `GET /api/v1/health/ready`

## How To Extend The Template

Add a route:

- define request and response schemas in `app/schemas`
- implement orchestration in `app/services`
- keep persistence in `app/repositories`
- register the route module in [app/api/router.py](/Users/devesh/Desktop/Fast-API-Template/app/api/router.py)

Add a model and migration:

- add the ORM model in `app/models`
- import it in the model package if needed for Alembic discovery
- create an Alembic revision
- update repository methods and tests in the same change

Add a feature safely:

- start with contracts and service behavior
- keep routes thin
- keep configuration centralized in `app/core/config.py`
- update docs and `.env.example`
- add API, service, and persistence tests

More detailed extension guidance lives in [docs/template_guide.md](/Users/devesh/Desktop/Fast-API-Template/docs/template_guide.md).

## Source-Of-Truth Docs

- [AGENTS.md](/Users/devesh/Desktop/Fast-API-Template/AGENTS.md)
- [code_review.md](/Users/devesh/Desktop/Fast-API-Template/code_review.md)
- [docs/design.md](/Users/devesh/Desktop/Fast-API-Template/docs/design.md)
- [docs/template_guide.md](/Users/devesh/Desktop/Fast-API-Template/docs/template_guide.md)

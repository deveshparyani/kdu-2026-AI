# Template Guide

## Purpose

Use this guide when extending the template itself or when starting a new service from it. The goal is to keep new work reusable, testable, and aligned with the implemented architecture.

## Start Here

Read these files in order before making structural changes:

1. `AGENTS.md`
2. `docs/design.md`
3. `code_review.md`
4. `README.md`

## Current Template Shape

Implemented layers:

- `app/api`: routes and FastAPI dependencies
- `app/core`: config, logging, middleware, exception handling, security
- `app/db`: engine, sessions, metadata, base models
- `app/models`: SQLAlchemy models
- `app/repositories`: persistence logic
- `app/schemas`: request and response contracts
- `app/services`: orchestration and reusable application logic
- `tests`: API, service, repository, security, and DB wiring coverage

Optional layers such as `app/domain` or `app/integrations` should be added only when the feature actually needs them.

Built-in operational assets:

- `Dockerfile` for container builds
- `docker-compose.yml` for local app + PostgreSQL startup
- `.github/workflows/ci.yml` for lint, type-check, tests, and coverage

## How To Switch Auth Identifier Mode

Change `AUTH_IDENTIFIER_MODE` in the environment:

- `email`
- `username`
- `either`

Recommended companion settings:

- `AUTH_USERNAME_MIN_LENGTH`
- `AUTH_USERNAME_MAX_LENGTH`
- `AUTH_USERNAME_REGEX`
- `AUTH_PASSWORD_MIN_LENGTH`
- `AUTH_PASSWORD_REQUIRE_UPPERCASE`
- `AUTH_PASSWORD_REQUIRE_LOWERCASE`
- `AUTH_PASSWORD_REQUIRE_DIGIT`
- `AUTH_PASSWORD_REQUIRE_SPECIAL`

Behavior guidance:

- `email`: use email-based registration and login
- `username`: use username-based registration and login
- `either`: keep the API contract generic and accept `identifier` for login

When changing identifier mode:

1. Verify schemas still validate the intended inputs.
2. Verify repository lookups still match the chosen identifiers.
3. Verify API tests cover the chosen mode.
4. Do not fork separate route sets for different auth modes.

## How To Add A Route

1. Add request and response schemas in `app/schemas`.
2. Add or extend a service in `app/services`.
3. Add or extend repository behavior in `app/repositories` if persistence is needed.
4. Add a route module in `app/api/routes`.
5. Register the router in `app/api/router.py`.
6. Add API tests in `tests/api`.

Rule:

- route handlers should validate transport concerns and call services
- route handlers should not contain business logic or direct SQLAlchemy queries

## How To Add A Service

Put service logic in `app/services` when the code:

- coordinates repositories
- applies application rules
- creates tokens
- validates workflow-level behavior
- translates lower-level failures into stable service errors

Service rules:

- keep services reusable outside route modules
- accept repositories or collaborators explicitly
- avoid importing FastAPI request objects or response objects

## How To Add A Repository

Put persistence behavior in `app/repositories` when the code:

- performs ORM queries
- persists models
- translates DB exceptions into repository-level errors

Repository rules:

- repositories may use SQLAlchemy directly
- repositories should not know about HTTP or FastAPI
- route handlers should not bypass repositories

## How To Add Schemas

Add schemas in `app/schemas` for:

- request bodies
- response payloads
- reusable API-facing value objects
- standardized error contracts

Schema rules:

- do not expose ORM models directly
- add examples when the shape is public or reused often
- keep normalization and validation near the transport boundary when practical

## How To Add Models And Migrations

1. Add or update ORM models in `app/models`.
2. Ensure metadata discovery still includes the model for Alembic.
3. Generate a migration.
4. Review the migration before applying it.
5. Add repository and API or service tests that prove the new schema behavior.

Commands:

```bash
alembic revision --autogenerate -m "add_widget_table"
alembic upgrade head
```

Rules:

- migrations are the schema source of truth
- do not rely on runtime table creation in production
- keep migration names descriptive

## How To Add Tests

Use the lowest-cost test mix that proves behavior:

- `tests/unit` for helpers, validation, and service behavior
- `tests/api` for request validation, auth, authorization, and response contracts
- repository tests for persistence and constraint behavior

Test rules:

- use isolated, deterministic fixtures
- use the separate test database path provided by the test harness
- prefer real repository and dependency wiring over excessive mocking
- keep coverage meaningful and maintain the CI threshold

## How To Update Configuration

When adding a new setting:

1. Add it to `app/core/config.py`.
2. Add it to `.env.example`.
3. Document it in `README.md` or this guide when the behavior is developer-facing.
4. Add tests when the setting changes runtime behavior materially.

## How To Add Cross-Cutting Concerns

Use these homes consistently:

- middleware in `app/core/middleware.py`
- exception mapping in `app/core/exceptions.py`
- logging in `app/core/logging.py`
- security helpers in `app/core/security.py`

Examples:

- request IDs
- CORS
- trusted hosts
- standardized error envelopes
- structured logs
- readiness checks
- startup safety validation

## How To Use The Completed Auth Flows

Available baseline routes:

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

Extension guidance:

- keep new auth endpoints thin and service-driven
- reuse existing token helpers before creating new token logic
- if you add stateful revocation, keep it in a dedicated persistence or cache layer
- if you add outbound email delivery, keep provider code in `app/integrations`

## Future Extension Checklist

Before finishing a change, verify:

- the route, service, repository, and schema boundaries still make sense
- new configuration is env-driven and documented
- request and response examples are updated if public contracts changed
- migrations were added when schema changed
- tests cover the main success path and the important failure paths

## Guidance For AI Agents

AI agents should:

- treat `AGENTS.md` as the working contract
- follow existing naming and layering patterns
- update docs and `.env.example` in the same change when behavior changes
- prefer general-purpose template patterns over project-specific shortcuts

AI agents should not:

- hardcode email-only assumptions into auth flow
- put SQLAlchemy logic in route handlers
- add undocumented settings
- introduce hidden side effects or implicit startup behavior

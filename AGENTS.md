# AGENTS.md

## Purpose

This repository is a reusable FastAPI template. It should stay production-oriented, practical, and easy to adapt across projects without baking in project-specific business rules.

This document is the working contract for developers and AI agents contributing to the template.

## Current Implementation Baseline

The template currently includes:

- FastAPI app factory and router composition
- env-driven settings in `app/core/config.py`
- structured logging, middleware, and global exception handlers
- async SQLAlchemy session management and Alembic setup
- user model, repository, auth service, JWT helpers, and protected route flow
- standardized error responses
- API, service, repository, DB, and security tests

## Architecture Rules

Use the current layer boundaries consistently:

- `app/api`: FastAPI routes, dependencies, and transport-level concerns
- `app/core`: settings, logging, middleware, exceptions, lifecycle, security
- `app/db`: engine, session wiring, metadata, ORM base
- `app/models`: SQLAlchemy models only
- `app/repositories`: persistence logic and DB exception translation
- `app/schemas`: request and response schemas
- `app/services`: orchestration and reusable application behavior
- `tests`: deterministic API, service, repository, and security coverage

Optional layers such as `app/domain` or `app/integrations` may be added later, but only when needed by a real feature.

## Layering Expectations

1. Routes call services.
2. Services coordinate repositories and security helpers.
3. Repositories own ORM queries and persistence behavior.
4. Routes must not access SQLAlchemy directly.
5. ORM models must not contain business workflows.
6. FastAPI-specific concerns must stay near the API layer.

## Coding Rules

- Keep route handlers thin.
- Keep business logic out of routes.
- Keep DB access out of routes and dependencies unless the dependency exists specifically to provide request-scoped resources.
- Use type hints in non-trivial code.
- Keep config centralized in `app/core/config.py`.
- Keep public behavior documented when it changes.
- Prefer explicit interfaces over clever abstractions.

## Authentication And Authorization Rules

- Authentication answers who the user is.
- Authorization answers what the user can do.
- Keep those concerns separate in code and tests.
- Support `AUTH_IDENTIFIER_MODE=email`, `username`, or `either`.
- Use a generic login field such as `identifier` where possible.
- Never log or return raw passwords, password hashes, or secrets.
- Return `401` for unauthenticated access.
- Return `403` for unauthorized access.

## Database Rules

- Use one async SQLAlchemy session per request.
- Keep repositories reusable and independent from FastAPI.
- Treat migrations as the source of truth for schema evolution.
- Add migrations for schema changes.
- Keep test DB behavior isolated from development and production databases.

## Testing Expectations

Every meaningful change should add the smallest useful test mix that proves behavior.

Minimum expectations:

- unit tests for pure helpers and service rules
- repository or persistence tests for DB behavior
- API tests for validation, auth, authorization, and error contracts
- regression coverage for security-sensitive paths

The suite should stay:

- deterministic
- isolated
- meaningful rather than inflated

## Documentation Expectations

When public behavior or developer workflow changes, update the relevant docs in the same change:

- `README.md`
- `docs/template_guide.md`
- `.env.example`
- `code_review.md`
- `docs/design.md` if the blueprint meaningfully changed

Public APIs should keep request and response examples accurate in generated docs when practical.

## Reusability Principles

- Do not add project-specific business workflows to the template core.
- Keep auth identifier behavior configurable rather than forking separate implementations.
- Keep optional integrations optional.
- Prefer patterns another team could copy into a different project with minimal edits.
- Preserve stable extension points for routes, services, repositories, schemas, migrations, and tests.

## Review Workflow

Before considering a change complete:

1. Run `ruff check .`
2. Run `mypy app tests`
3. Run `pytest`
4. Review the change against `code_review.md`
5. Verify docs and `.env.example` still match the implementation

## Extension Guidance

When adding a feature:

1. start with the schema and service shape
2. add repository behavior if persistence is needed
3. add route wiring last
4. add migrations for schema changes
5. add or update tests in the same change

If a change makes the template less reusable, stop and redesign before merging.

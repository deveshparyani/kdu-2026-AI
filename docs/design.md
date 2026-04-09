# Template Design

## Goal

Build a reusable, production-ready FastAPI template that provides clean architectural boundaries, env-driven configuration, and a sensible path for authentication, persistence, testing, and deployment without forcing project-specific assumptions.

## Non-Goals

- No project-specific business domain.
- No hardcoded cloud vendor dependency.
- No auth implementation locked to email-only login.
- No hidden runtime configuration outside environment variables.

## Architecture Summary

The template should be built as a modular service with clear separation between transport, business logic, persistence, and integrations.

Planned layers:

- API layer for routing, request validation, and response serialization.
- Service layer for use-case orchestration and transaction control.
- Domain layer for business rules and reusable policies.
- Persistence layer for repository contracts and database adapters.
- Integration layer for email, cache, storage, background jobs, and observability.
- Core layer for configuration, security utilities, logging, and startup/shutdown wiring.

Design constraints:

1. FastAPI should remain a delivery mechanism, not the center of business logic.
2. Configuration must be environment-driven through a single settings system.
3. The auth subsystem must support `email`, `username`, or `either` identifier mode through configuration.
4. Database access must be structured so it can be tested independently of HTTP routing.
5. External systems must be replaceable without rewriting the service layer.

## Implemented Build Status

Implemented:

1. Project skeleton, configuration system, and environment validation.
2. Logging, health and readiness endpoints, startup checks, and lifecycle wiring.
3. Database engine, session management, base models, and Alembic migration setup.
4. User model, repository contracts, and persistence tests.
5. Authentication core: password hashing, token strategy, identifier parsing, and auth settings.
6. Auth API flows: register, login, refresh, logout, current user, password reset, and email verification.
7. Authorization primitives with authenticated and admin-only route protection.
8. Packaging and CI assets for repeatable local and pipeline execution.

Still optional for downstream projects:

- permission or scope-based authorization beyond RBAC
- provider-backed outbound email delivery
- cache-backed token revocation or rate limiting
- worker integrations, storage providers, and telemetry exporters
- admin bootstrap automation

## Auth Flow

Auth must be configurable rather than forked into separate template variants.

Baseline auth flow:

1. Client submits credentials using a configured identifier field plus password.
2. The auth layer resolves which identifier formats are allowed from `AUTH_IDENTIFIER_MODE`.
3. Input validation normalizes the identifier according to mode:
   - `email`: require email-shaped identifier and compare against normalized email field.
   - `username`: require configured username rules and compare against username field.
   - `either`: accept either input shape and resolve against the appropriate stored field.
4. Service layer fetches user through repository methods that do not expose ORM concerns.
5. Password verification happens in the security layer.
6. Token issuance happens in a dedicated auth/token component.
7. Refresh, logout, email verification, and password reset are implemented as reusable service-driven flows.

Rules:

- The route contract should stay stable even when auth mode changes through environment variables.
- Identifier resolution logic should be centralized, not duplicated across routes.
- The template must document any ambiguity rules for `either` mode.

## Database Flow

The template should prefer explicit, testable database flow:

1. Application startup initializes the database engine and session factory from environment variables.
2. Each request obtains a scoped session through dependency wiring.
3. Services use repositories or a unit-of-work style abstraction for data operations.
4. Commit and rollback behavior is explicit and consistent.
5. ORM entities remain persistence concerns; API schemas and domain rules stay separate.
6. Migrations manage schema evolution; runtime table creation should not replace migrations in production.

Database design expectations:

- Use a relational database baseline.
- Support safe local defaults and production-grade connection tuning through environment variables.
- Enforce data integrity with constraints, indexes, and migrations.
- Keep destructive schema changes deliberate and documented.

## Deployment Strategy

The template should be deployment-friendly from the start.

Implemented strategy:

- Container-first packaging for consistent local, CI, and production execution.
- Twelve-factor style configuration via environment variables.
- Health and readiness endpoints for orchestration platforms.
- Migration execution as an explicit deployment step.
- Reverse proxy or ingress compatibility.
- Structured logs suitable for local and centralized collection.
- Optional telemetry and error reporting integrations.

Target deployment environments:

- Local development
- CI pipelines
- Single-container hosting
- Container orchestration platforms

## Acceptance Criteria

The template is considered complete when the following remain true:

- The architecture is documented and bounded clearly enough for contributors to implement consistently.
- All major runtime behavior is planned as env-driven configuration.
- Auth supports `email`, `username`, and `either` modes without separate codebases.
- Database access, auth logic, and external providers are separable and testable.
- Deployment and operations expectations are implemented and documented.
- Another developer or AI agent can extend the template by following `AGENTS.md` and `docs/template_guide.md`.

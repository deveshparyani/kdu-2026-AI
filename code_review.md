# Code Review Checklist

Use this checklist when reviewing template changes or downstream projects based on this template.

## Architecture

- [ ] Are route, service, repository, schema, and model responsibilities still clearly separated?
- [ ] Does the change avoid putting business logic in route handlers?
- [ ] Does the change avoid putting ORM queries in route handlers?
- [ ] Is the design reusable rather than tailored to one project domain?
- [ ] If a new abstraction was added, does it solve a real extension point?

## Security

- [ ] Are passwords, tokens, secrets, and hashes excluded from logs and responses?
- [ ] Does auth still support the configured identifier mode: `email`, `username`, or `either`?
- [ ] Are `401` and `403` responses used correctly?
- [ ] Are token validation and permission checks explicit and reusable?
- [ ] Are production errors sanitized appropriately?

## Testing

- [ ] Do tests cover both success and failure paths?
- [ ] Does the change use deterministic fixtures?
- [ ] Does persistence behavior use the isolated test database when relevant?
- [ ] If auth or authorization changed, are protected-route and role-guard cases covered?
- [ ] If DB schema changed, was migration behavior updated and reviewed?

## API Quality

- [ ] Are request and response schemas explicit?
- [ ] Are status codes and error shapes consistent with the existing API?
- [ ] Are request and response examples still accurate?
- [ ] Is OpenAPI metadata still accurate for public endpoints?
- [ ] Are validation failures stable and predictable?

## Database Safety

- [ ] Are migrations the source of truth for schema changes?
- [ ] Are repository errors translated into user-friendly service or API behavior?
- [ ] Are uniqueness and constraint assumptions enforced consistently?
- [ ] Is transaction and session behavior appropriate for async request handling?

## Maintainability

- [ ] Does configuration remain centralized and env-driven?
- [ ] Was `.env.example` updated for new settings?
- [ ] Were `README.md` and `docs/template_guide.md` updated when developer workflow changed?
- [ ] Are names and module boundaries clear enough for the next contributor?
- [ ] Would another project be able to reuse this change with minimal edits?

## Final Gate

- [ ] I understand the change end to end.
- [ ] I checked the main risks, not just style.
- [ ] I would be comfortable building the next feature on top of this version.

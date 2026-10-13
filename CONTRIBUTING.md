# Contributing

Preserve the [rebuild contract](docs/rebuild.md) and follow
[AGENTS.md](AGENTS.md) for safety and task-specific reading.

1. State the problem, intended result, affected services, and observable
   acceptance criteria. Inspect live state before operational work.
2. Make a focused change; preserve unrelated work. Keep provisioning, Compose,
   environment declarations, verification, and recovery instructions consistent.
3. Run the relevant [development checks](docs/development.md). Live changes use
   the [operations guide](docs/operations.md) and the affected service runbook.
4. Report changed behavior, checks and limits, deployment revision, and rollback.
   Completed recovery changes must be committed and retrievable through the
   documented clone path. Never commit production secrets or durable data.

## Documentation ownership

Update the owning document in the same behavior change. Do not copy its details
into the other guides; link to them. Explain when documentation is unaffected.

| Change | Owner |
|---|---|
| Purpose / quickstart | [README](README.md) |
| User capability or workflow | [USER_DOC](USER_DOC.md) |
| Component or data boundary | [Architecture](docs/architecture.md) |
| Setup / checks | [Development](docs/development.md) |
| Runtime procedure / service constraint | [Operations](docs/operations.md) or the [owning runbook](docs/reference/service-policies.md) |
| Readiness / verification | [Status](docs/status.md), linking dated evidence |
| Essential agent instruction | [AGENTS](AGENTS.md) |
| Consequential decision | [Decisions](docs/decisions/README.md) |

Evidence names its date, revision, environment, method, and limits. Preserve
historical reports; update status when later evidence supersedes them. A health
response does not prove a user workflow or restore. Docs-only edits need source
and link review, not deployment. Run `python3 scripts/check-docs.py` after edits.

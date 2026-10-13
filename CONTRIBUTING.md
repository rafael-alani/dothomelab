# Contributing

Changes must preserve the [rebuild contract](docs/rebuild.md). This is a
personal infrastructure repository with real durable data; a working container
alone does not establish reproducible deployment or recovery.

## From problem to accepted change

1. Describe the problem, affected services/users, intended result, scope, and
   observable acceptance criteria. Link relevant manual sections and evidence.
2. Read [AGENTS.md](AGENTS.md) and the task-specific documents it names. Inspect
   live state before relying on an inventory. Separate observed drift from the
   change being requested.
3. Make a focused branch when useful (`codex/<topic>` for agent-created
   branches). Preserve unrelated local work. Keep data, secrets, dumps, media,
   and generated production environment files out of Git.
4. Implement the smallest complete change. Include provisioning, Compose,
   environment variable names/defaults, verification, and recovery implications
   when they are affected. Use the [development guide](docs/development.md) to
   choose checks and the [operations guide](docs/operations.md) for live work.
5. Update the documentation that owns the changed behavior in the same change.
   Use the table below; an internal refactor need not create a meaningless
   manual edit. Record why documentation is unaffected when that is not obvious.
6. Review the diff for secrets, unrelated changes, and unsafe commands. Report
   checks performed, failures, skipped checks, deployment revision, rollback,
   and external prerequisites. Completed recovery changes must be committed
   and available through the repository's documented clone path.

## Documentation ownership

| Change | Update |
|---|---|
| Purpose or shortest start | [README](README.md) |
| Capability, permission, setting, or user journey | [User manual](USER_DOC.md) |
| Structure, data flow, or component boundary | [Architecture](docs/architecture.md); an [ADR](docs/decisions/README.md) for a consequential decision |
| Setup, test, or debug command | [Development](docs/development.md) |
| Deploy, update, diagnose, backup, or restore procedure | [Operations](docs/operations.md) or the owning service runbook |
| Service-specific update/data constraint | [Service policies](docs/reference/service-policies.md) and the affected runbook |
| Readiness or verification result | [Status](docs/status.md), linking dated evidence |
| Add, move, or split documentation | [Documentation map](docs/README.md) and affected links |
| Agent needs essential new guidance | [AGENTS.md](AGENTS.md); keep detailed reference out of it |

## Evidence and review

Use a PR, commit description, or review note that states the concrete problem
and resulting behavior, then relevant validation and limits. Do not describe
an unrun check as passing. A docs-only change needs link/navigation and source
review; it does not need a deployment or backup. A health response does not
prove playback, authentication, data integrity, or restoration.

Date new operational evidence and name the code revision and environment. Keep
historical reports as observations of their original date. Add a supersession
note when later evidence changes their interpretation; do not silently rewrite
history. [Status](docs/status.md) is the entry point to current readiness.

No general or Labrador handbook is wired into this pilot. The clone is
self-contained. Extract shared rules only after this repo's documentation has
been reviewed; do not add placeholders or assume sibling files load in an
isolated checkout.

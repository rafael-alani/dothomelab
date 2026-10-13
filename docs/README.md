# Documentation

| Question | Read |
|---|---|
| What can I do, and how? | [User manual](../USER_DOC.md) |
| What works, and what remains open? | [Dated status](status.md) |
| How does the system fit together? | [Architecture](architecture.md) |
| How do I develop and check a change? | [Development](development.md) |
| How do I deploy, update, or recover? | [Operations](operations.md) |
| Which service runbook applies? | [Service policies and runbooks](reference/service-policies.md) |
| What must an agent preserve? | [AGENTS](../AGENTS.md) |
| How do I contribute and maintain docs? | [Contributing](../CONTRIBUTING.md) |
| Why was a significant choice made? | [Decisions](decisions/README.md) |

## Detailed contracts

- [Full rebuild](rebuild.md): recovery inputs, commands, failure behavior.
- [HAOS](haos-vm.md): managed VM104 and its VMA/native recovery.
- [Media contract](media-data-contract.md): canonical paths and allowed writers.
- [Inventory](../provision/inventory.env): guest identities, resources, mounts.
- [Environment example](../.env.example): configuration names and defaults.
- [Evidence index](evidence/README.md): dated checks, migrations, repairs, research.

Service-specific procedures live beside their implementation in `hosts/`,
`clients/`, and `backup/`. Historical reports retain their original dates and
are not instructions to rerun a migration. New reports go in `docs/evidence/`;
link them from status when they change readiness.

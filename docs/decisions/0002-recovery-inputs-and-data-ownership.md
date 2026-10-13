# 0002 — Recovery inputs and data ownership

Recorded: 2026-10-13. Status: **Existing implemented design, recorded retrospectively**.

Guest roots are replaceable, so durable state must survive outside them. Git
owns deployment configuration, `/root/.env` recovery secrets, appdata application
and native state, and `/vault/shared` large user files. Bootstrap reconstructs
LXCs and restores absent HAOS VM104 from its canonical VMA; VM101 and physical
disk provisioning remain external. Exact inputs are in the [rebuild contract](../rebuild.md).

Application-local databases preserve supported versions/extensions, isolation,
and application-specific restore paths. Canonical media has explicit organizers
and narrow writers so readers cannot reorganize it. The [Grimmory M4B failure](../book-metadata-canonicalization-2026-07-26.md)
shows why success with one format cannot authorize writing another.

Consequences: an appdata restore still needs shared files and an off-host PBS
key; same-host PBS is not off-site protection. Code/image rollback cannot undo
a schema or media mutation. Targeted restore samples do not prove a clean-host
rebuild. See [media ownership](../media-data-contract.md),
[migration evidence](../compose-project-migration.md), and [current status](../status.md).

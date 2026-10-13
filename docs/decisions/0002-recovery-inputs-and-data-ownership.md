# 0002 — Recovery inputs and data ownership

Recorded: 2026-10-13. Status: **Existing implemented design, documented
retrospectively**. This record summarizes established repository contracts;
it does not introduce a new migration or claim clean-host acceptance.

## Context and decision

Guest roots are replaceable. Git owns desired deployment state; production
`/root/.env` owns recovery secrets; SSD appdata owns application databases,
configuration, native identities, and the HAOS recovery image; `vault/shared`
owns large user data. Bootstrap recreates managed LXCs without their old roots
and restores absent VM104 from a verified canonical VMA. VM101 and physical
disk provisioning remain external.

Keep databases application-local so supported versions/extensions, isolation,
logical restore, and rollback remain specific to the application. Do not move
PostgreSQL data directories between majors or servers.

Give each canonical media class an explicit organizer and narrowly scoped
metadata writers. Readers receive read-only access; derived libraries are
separate. The Grimmory M4B failure demonstrated why ebook metadata-writing
success cannot authorize audiobook mutation.

## Consequences

An appdata restore requires independently available shared files. PBS on the
same host is not an independent off-site copy, and narrow shared binds beneath
appdata paths do not add their bytes to the appdata snapshot. The encryption
key must be available off-host. A code/image rollback cannot undo a schema or
canonical-file mutation without appropriate retained data.

Verification must cover the requested recovery scope and the affected media
structure. A dry-run, targeted restore sample, or one successful metadata pilot
does not prove a full clean-host recovery or every file format.

## Established sources

- [Rebuild contract and recovery material](../rebuild.md)
- [Original migration and restore evidence](../compose-project-migration.md)
- [Media ownership contract](../media-data-contract.md)
- [Book metadata pilot and rollback evidence](../book-metadata-canonicalization-2026-07-26.md)
- [Current service policies](../reference/service-policies.md)

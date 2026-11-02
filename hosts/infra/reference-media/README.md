# Immutable reference archive

The native PVE SSH endpoint is the sole writer of
`/vault/shared/media/references/objects/<sha256>.<extension>`. Files are verified
before atomic publication, mode 0444 and never overwritten or deleted by the
protocol. The Mac consumes the existing read-only Samba Media share; it uploads
through the separate `reference-ingest` account. No HTTP service, public route,
Docker socket or general shell is introduced.

## State and recovery

`/srv/appdata/docker/reference-media` contains the SQLite WAL catalog, retained
inventory snapshots, completion receipts, public enrollment key and deployment
revision. It is covered by the existing appdata policy. Reference originals are
on `/vault/shared`, outside appdata PBS; no extra media backup was introduced.
The local vault's small notes/thumbnails follow its existing Syncthing/backup
policy. The Mac profile and private ingestion key remain outside both Git and the
vault; losing them requires sign-in and scoped key re-enrollment.

The endpoint fixes both data paths and checks the mounted dataset identities on
every request. The restricted key allows no shell, PTY, forwarding or client path
selection. Requests are size-bounded JSON plus optional exact-size media/inventory
bytes. `put`, `inventory`, `link`, `complete_post`, `pending`, `catalog` and `status`
are the only operations. The catalog keeps separate source, collection,
membership-instance, carousel-position and immutable asset identities. This
preserves multiple memberships and repeated entries while deduplicating media.

Install from a committed PVE checkout after inspecting mounts/ownership:

```bash
bash hosts/infra/reference-media/install.sh "$(git rev-parse HEAD)" /protected/path/ingest.pub
```

The installer changes ownership of only the exact state/archive/object directories,
never recursively. Existing object permissions/ownership remain intact. It keeps
root-owned release code and the preceding forced-key configuration; no shared SSH
policy is modified. Full bootstrap re-enrolls the endpoint when retained appdata
contains `reference-media/ingest.pub`. A missing public key is an explicit external
prerequisite, not an invitation to create unrestricted access.

## Operation and verification

Use the [desktop runbook](../../../clients/reference-media/README.md) for collection,
queues and Obsidian commands. Status/catalog requests use the dedicated client
key and strict SSH host-key validation. A successful scan must carry explicit
completion proof; authentication, pagination, schema or server errors cannot
retire previous memberships. Every prior snapshot and original remains retained.
The service is request-driven; it has no daemon to restart.

```bash
python3 -m unittest discover -s hosts/infra/reference-media -p 'test_*.py'
findmnt -n -o SOURCE -T /vault/shared/media/references
findmnt -n -o SOURCE -T /srv/appdata/docker/reference-media
cat /srv/appdata/docker/reference-media/DEPLOYED_COMMIT
```

Pulse monitors PVE/Infra and their containers, but does not provide application
coverage for this request-driven native endpoint or the Mac LaunchAgent. Report
that gap explicitly; `References/Archive` and the desktop worker status are the
workflow health indicators. The background collector has no separate Homarr UI.

Rollback code by reinstalling a retained committed release or restoring its exact
forced-key configuration. Retain the newer catalog and all immutable objects;
additive tables need no destructive down-migration. Older code may lack new
membership/completion features. Stop the client before changing protocol versions.
Do not remove appdata, media, historical scans, or rollback releases as a code
rollback. See the [delivery evidence](../../../docs/evidence/2026-11-02-reference-media-boards.md).

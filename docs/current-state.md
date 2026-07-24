# Current state

Last reconciled with the live PVE host on 2026-07-24 at approximately 15:45
CEST. Historical migration evidence remains in
`docs/compose-project-migration.md` and `docs/apps-cleanup-2026-07-24.md`.

## Live architecture

| System | Live workload | Durable state |
|---|---|---|
| PVE `afa` | PVE 9.1.2; `rpool` and `vault` healthy | Git, `/root/.env`, appdata, shared data, PBS datastore |
| CT102 `servarr` | one 13-container Compose project | `/srv/appdata/docker` at `/docker`; `/vault/shared` at `/data` |
| CT110 `infra` | 9 active containers plus Cockpit, Samba, Tailscale | both canonical datasets mounted read-write |
| CT112 `apps` | 12 containers in five Compose projects | appdata read-write; shared data read-only |
| CT113 `proxmox-backup-server` | PBS 4.2.3 | `vault/pbs_datastore`, quota 2 TiB |
| VM101 | running, unmanaged | outside repository scope |
| VM104 HAOS | stopped, unmanaged | outside repository scope |

Active container counts and names are kept in the README architecture tree.
All application Compose files, focused prepare/verify scripts, Cockpit/Samba
configuration, PBS client tooling, WUD runner, and restore logic are in Git.

## New recovery implementation

The repository now declares and automates:

- canonical ZFS child datasets and properties;
- the four LXC identities, resources, root sizes, static IP/MAC addresses,
  mounts, TUN devices, GPU devices, startup order, and OS templates;
- Debian/Docker/PBS/native package installation;
- PBS datastore reuse, users/token/ACL, retention, GC, full verification, and
  the PVE backup client configuration;
- appdata copy or latest-snapshot restore;
- internal Docker mTLS generation and WUD configuration;
- native Cockpit account, Samba password database, and Tailscale state restore;
- all Compose preparation/deployment and end-to-end verification.

The entrypoint is `./bootstrap.sh`; full behavior and safety constraints are in
`docs/rebuild.md`. A read-only live dry-run completed successfully. A real
clean-host rebuild has not been performed, so complete bare-metal recovery is
not yet verified.

## Native state capture

`scripts/capture-native-recovery.sh` ran successfully on 2026-07-24. It briefly
stopped only Tailscale and SMB, copied consistent state into appdata, restarted
both, and verified Tailscale online plus the `afa` Samba account. The captured
files are mode 0600 and mapped to guest root:

```text
/srv/appdata/docker/
├── infra-samba/private/passdb.tdb
├── tailscale/tailscaled.state
└── recovery/
    ├── infra-afa.shadow-hash
    ├── pbs-root.shadow-hash
    └── pbs-appdata.key
```

Snapshot `host/afa-appdata/2026-07-24T12:38:45Z` now contains these files and
the final same-day Apps/NPM/Obsidian state. Its upload and server-side
verification succeeded. A targeted client restore recovered all five native
files and matched their live bytes, UID, GID, and mode.

## Data and database policy

- Large application-independent data is under `/vault/shared`.
- Persistent Docker state and application-local databases are under
  `/srv/appdata/docker`.
- Immich retains PostgreSQL 14/VectorChord; Jellystat retains private
  PostgreSQL 18; Mealie uses SQLite. There is no central PostgreSQL service.
- Guest roots contain replaceable packages, images, caches, logs, and runtime
  configuration only.
- `/vault/shared` still lacks an independent backup; PBS resides on the same
  `vault` pool and does not protect against pool loss.

## Backup and updates

The daily PVE timer freezes CT102/110/112, snapshots appdata, resumes the
guests, and uploads encrypted appdata plus `/root/.env`. Retention is 7 last,
14 daily, 8 weekly, and 12 monthly; prune is daily, GC weekly, and full
verification monthly. A successful backup alone starts sequential WUD updates.
Database-specific hooks are not installed; consistency relies on the brief
guest freeze around the ZFS snapshot.

The new 246.784 GiB logical snapshot completed at 14:47 CEST, reused 99.1%,
removed its temporary ZFS snapshot, and successfully handed off to WUD; no
update was reported. Verify-new finished `OK` at 15:44 CEST. Prior evidence
also includes a 10,018-file temporary restore and a 200-file
byte/UID/GID/mode sample. This proves encrypted backup integrity and sampled
restore paths, not the new complete bootstrap.

## Known external or unfinished items

- PVE installation and physical pool/disk creation remain manual. Bootstrap
  imports an existing `vault` and never guesses destructive disk operations.
- The router is verified only as a contract: DNS must remain
  `192.168.0.100`, and TCP 80/443 must forward to `192.168.0.110`.
- VM101 and HAOS VM104 are intentionally ignored.
- Obsidian Syncthing is deployed receive-only, but laptop/phone pairing, GUI
  authentication/private routing, Proton login, first checksum-restored
  archive, and timer enablement remain user steps.
- Retained migration snapshots, volumes, images, dumps, and Immich rollback
  assets still require a separate explicitly authorized cleanup.

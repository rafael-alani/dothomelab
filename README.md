# dothomelab

Git-managed application and recovery definitions for the Proxmox homelab.
Active Docker workloads run on `servarr` (CT102), `infra` (CT110), and `apps`
(CT112); encrypted appdata backups are stored by PBS in CT113.

The recovery set is this repository, the Proxmox host's production
`/root/.env`, SSD application state under `/srv/appdata/docker`, off-host PBS
credentials, and large shared data under `/vault/shared`. Git reproduces the
applications and selected native configuration; it does not yet provision PVE,
the ZFS pools, LXCs, VM101, or HAOS.

## Back up before migration

- Put Compose definitions, scripts, mount requirements, versions, and restore notes in this repository.
- Put persistent Docker state under `/srv/appdata/docker/<service>`.
- Put large application-independent data under `/vault/shared`.
- Create a logical database dump when the application's recovery procedure
  requires one; the recurring PBS job freezes the application LXCs around its
  ZFS snapshot but has no database-specific hooks installed.
- Keep secrets only in the production `/root/.env`; the appdata PBS job includes it as an encrypted recovery archive when present.
- Protect data under `/vault/shared` separately when it is irreplaceable. PBS
  is on the same `vault` pool and is not an independent backup for that data.
- Retain old volumes, images, snapshots, dumps, and migration ZIPs until the
  replacement has a newer successful backup and a verified rollback/restore.

## Bootup / restore

1. Reinstall Proxmox VE and import the `vault` pool.
2. Clone this repository and recover the off-host PBS encryption key and administrator password.
3. Recreate the PBS LXC, bind-mount `vault/pbs_datastore`, and reconnect the `appdata` datastore.
4. Restore `appdata.pxar` to `/srv/appdata/docker` and the encrypted production `.env` archive to `/root/.env`.
5. Recreate CT102, CT110, and CT112. Bind `/srv/appdata/docker` at
   `/docker` in Servarr and at its host path in Infra/Apps; bind
   `/vault/shared` read-write at `/data` in Servarr, read-write at
   `/vault/shared` in Infra, and read-only at `/data` in Apps. Restore the
   Apps GPU device mappings and the Servarr TUN device.
6. Restore Docker TLS server/client material from the separate off-host copy,
   install the remote API endpoints, and reinstall the PVE backup/WUD systemd
   units.
7. Run `scripts/sync-guest-repo.sh` for each application LXC, run the relevant
   `prepare.sh`/native installer, and deploy Servarr, Infra, WUD, Obsidian, and
   all five Apps projects with `scripts/deploy-compose.sh`.
8. Recreate manual credentials/state that are not in Git, including the Samba
   password. Reauthenticate Proton only if the restored session has expired.
9. Run every focused `verify.sh`, then verify mounts, DNS/proxy routes, Docker
   TLS, the PBS upload, and a temporary restore before considering recovery
   complete.

See [`docs/current-state.md`](docs/current-state.md) for the live architecture,
known gaps, and outcome against the initial plan. Backup mechanics are in
[`backup/pbs/README.md`](backup/pbs/README.md); completed migration evidence is
in [`docs/compose-project-migration.md`](docs/compose-project-migration.md) and
[`docs/apps-cleanup-2026-07-24.md`](docs/apps-cleanup-2026-07-24.md); the
unfinished Obsidian steps are in
[`hosts/infra/obsidian-sync/README.md`](hosts/infra/obsidian-sync/README.md).

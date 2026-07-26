# Media pipeline phase 5 evidence — PinePods

## Scope and safety boundary

Phase 5 makes PinePods the podcast subscription, download, playback, and
progress service while keeping Audiobookshelf canonical for audiobooks. No
Audiobookshelf database, appdata, user, library record, old podcast file,
volume, or image is deleted. The parent `/podcasts` LXC bind remains because
PinePods needs it; the PinePods container receives only `/podcasts/pinepods`.

The scheduled appdata job that began at `2026-07-26 02:02:50 CEST` completed
successfully at `02:12:11`; its success-only WUD handoff completed at
`02:14:00`. No on-demand PBS backup was started for this rollout.

## Upstream revalidation

The official PinePods repository was inspected at commit
`4b8785b555aac67ece420478a83b3ee28b718c22` (2026-07-10), after the current
`0.9.0` release (2026-06-26). The official quick-start and image define:

- `madeofpendletonwool/pinepods:latest` on application port `8040`;
- `postgres:18` with `PGDATA=/var/lib/pgdata/pgdata` and a bind at
  `/var/lib/pgdata`, outside PostgreSQL 18's image-owned volume;
- required Valkey, supported here as the explicit
  `valkey/valkey:8-alpine` major;
- `/opt/pinepods/downloads` and `/opt/pinepods/backups` as the portable
  application binds;
- supported PUID/PGID remapping, first-admin bootstrap variables, optional
  OIDC, the built-in `/api/health` database/Valkey readiness endpoint, and a
  built-in GPodder-compatible API.

The multi-architecture `latest` manifest resolved before deployment; its
linux/amd64 child digest was recorded as
`sha256:782a1cb78600959d8a0a5cdfd95f9191637a978686e273d0e97ad281ea1dc78f`
in the operator preflight. Exact image identity is captured again from the
live container after deployment.

## Pre-migration Audiobookshelf inventory

A read-only query of the live Audiobookshelf SQLite database found:

- one Podcasts library rooted at `/podcasts`;
- zero podcast items, zero podcast rows, zero podcast episodes, and zero
  podcast progress rows;
- zero files and zero bytes below `/vault/shared/media/podcasts`;
- two active application users, including one administrator.

No feed URL, credential, API key, password, or private-feed value was printed
or copied into Git. Because there is no subscription, episode, or progress
object to migrate, phase 5 uses no database edits and has no unsupported
progress conversion. The retained library record and appdata are the rollback
source.

## Repository implementation

`hosts/apps/pinepods` declares one isolated Compose project:

- the official application `latest` channel is backup-gated and must pass
  direct `/api/health` after a sequential WUD replacement;
- PostgreSQL 18 and Valkey 8 are private, publish no host ports, and have
  `wud.watch=false`;
- generated database, cache, and administrator values persist only in
  `/root/.env`; `.env.example` contains placeholders;
- database files, server backups, latest/previous logical dumps, acceptance
  evidence, and retained restore-test artifacts are below canonical appdata;
- downloaded episodes are confined to `/podcasts/pinepods`, which resolves to
  `/vault/shared/media/podcasts/pinepods` outside PBS appdata.

The private `pinepods.rafael.media` NPM route terminates TLS, allows WebSockets,
preserves long playback/download connections, and allows only LAN and
Tailscale source ranges. Pi-hole, Homarr, bootstrap order, WUD checks, container
counts, backup hooks, and focused verification are reconciled from Git.

## Validation and live evidence

The final section is updated from the live host after deployment. Acceptance
requires all of the following before Audiobookshelf loses its writable podcast
container bind:

- Compose config and repository checks;
- healthy application/database/Valkey plus exact mounts, UID/GID, DNS, HTTPS,
  Homarr, and WUD policy;
- a public-feed subscription, refresh, one downloaded episode, web
  play/seek/resume progress, GPodder-compatible client sync, OPML export, and
  duplicate-free OPML re-import;
- a current logical dump and isolated PostgreSQL 18 restore whose object counts
  remain equal before and after an application query;
- Audiobookshelf audiobook playback plus prior BookOrbit/Storyteller
  regressions;
- bootstrap dry-run, focused verifiers, and `provision/verify.sh`.

## Recovery and rollback

Restore `/srv/appdata/docker/pinepods` and `/root/.env`, restore the separate
episode subtree from its own shared-media recovery source, then run bootstrap.
Use the custom-format dump for a PostgreSQL major migration; never copy the
live PostgreSQL directory between majors.

Rollback reverts and syncs the Git commit, restores the prior Compose
generation, and leaves PinePods stopped if necessary. Retain all PinePods
appdata/dumps/episodes/restore-test artifacts and all Audiobookshelf
appdata/library records/files/images. Reattaching Audiobookshelf's exact
`/podcasts` bind is sufficient to make its preserved podcast library reachable
again; rollback does not authorize deleting anything.

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
in the operator preflight. The deployed image reports image ID
`sha256:72f9a834d2c4db01109463aa0c0d60c72e5560559a0f1a1d45ee4be3395b2702`
and repository digest
`madeofpendletonwool/pinepods@sha256:ebc258bb0c62cdb69e5fb726b247c885dac19b50d06fed68fa8d37197b88ace4`.

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

During the intentionally overlapping PinePods acceptance window,
Audiobookshelf's still-active filesystem watcher noticed the public NASA test
episode below the shared parent. Immediately before removing its container
bind, the retained state was one Podcasts library, one item, one podcast, one
episode, zero progress rows, and two active users. The exact same counts
remained after container recreation. The row and episode file were not
deleted, and the retained library was not edited to pretend that progress had
migrated.

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

Live acceptance completed at `2026-07-26T00:54:10Z`. The official PinePods
news RSS feed was first tried because it was public and first-party, but its
entries have no audio enclosures. PinePods imported 21 news entries and then
failed the requested download safely with a builder error. That subscription
remains, and the failure is recorded here. The accepted fixture is NASA's
official Houston We Have a Podcast feed, whose enclosure returned HTTP 200
and byte ranges.

The supported application and GPodder APIs proved:

- exactly one matching NASA subscription after OPML export and re-import;
- 200 refreshed episodes in the bounded query and one downloaded episode;
- one MP3 plus one zero-byte ownership marker and `26,727,782` total bytes in
  the PinePods episode subtree;
- web progress persisted at 37 seconds;
- a GPodder-compatible client initial sync returned both subscriptions and its
  episode action persisted at 48 seconds in the main application;
- the sanitized OPML and feed hashes are retained without feed credentials.

The evidence file is:

```text
/srv/appdata/docker/pinepods/acceptance/
  20260726T005410Z/acceptance-summary.json
```

The episode is:

```text
/vault/shared/media/podcasts/pinepods/Houston We Have a Podcast/
  2024-03-06_So You Want to be an Astronaut__2_127.mp3
```

It is below `vault/shared`, not `rpool/appdata/docker`, so it is outside the
appdata PBS job. No physical phone was available. The protocol harness is the
accepted GPodder-compatible client; first use on AntennaPod or another native
client still requires enabling podcast sync for the user, entering
`https://pinepods.rafael.media`, and entering that user's PinePods
credentials.

The current custom-format PostgreSQL dump, role export, hashes, server
metadata, and counts are in
`/srv/appdata/docker/pinepods/backups/latest`. Its counts are:

```text
users=2
podcasts=2
episodes=454
downloads=1
progress=1
gpodder_devices=2
api_keys=2
```

The isolated PostgreSQL 18 restore and network-isolated PinePods application
query passed with those exact counts before and after startup. Its stopped
containers, internal network, database files, health responses, counts, and
hashes are retained under:

```text
/srv/appdata/docker/pinepods/restore-tests/20260726T005423Z
network: pinepods_restore_20260726t005423z
```

Live Compose config validation passed for PinePods and Audiobookshelf using a
mode-0600 temporary dotenv that was removed immediately. PinePods, PostgreSQL
18, Valkey 8, and Audiobookshelf are healthy with zero restarts. PinePods
application processes run as UID/GID `1000:1000`; the only shared-media
container mount is `/podcasts/pinepods` to `/opt/pinepods/downloads`.
PostgreSQL and Valkey publish no host port. The application alone is watched
by WUD; a dry-run found `apps/pinepods` associated with
`docker.backupgated`, 43 watched containers total, and no eligible updates.
The focused verifier confirms both supporting services have
`wud.watch=false`.

Pi-hole resolves `pinepods.rafael.media` to NPM at `192.168.0.110`. Private
HTTPS validates its certificate and `/api/health` reports application,
database, and Valkey ready. NPM has one exact route with WebSockets and
LAN/Tailscale allow rules followed by `deny all`. Nginx and NPM SQLite
integrity pass. Homarr has the PinePods app and three board items; the managed
totals are 21 apps, 63 items, and 147 layouts.

After acceptance, Audiobookshelf was recreated without `/podcasts`; its exact
mounts are writable `/config` and `/metadata` plus read-only `/audiobooks`.
The retained podcast library/item/podcast/episode/progress/user counts were
identical before and after. Its focused verifier, HTTP health, SQLite
integrity, and private HTTPS pass. The representative Alice M4B remains
readable inside the container: a 65,536-byte read succeeded and SHA-256 still
equals
`fe522ad254a3dc6ea68fea734f5376897fccff588458dc56e35628c1aec8a3ed`.
Phase 3's authenticated direct-play, range, resume, and offline-session
evidence remains valid; no authenticated browser session was available for a
new UI seek, and the scoped Shelfarr identity correctly cannot play media.
BookOrbit and Storyteller focused regressions pass.

The live media contract, Infra/NPM/Homarr, PinePods, Audiobookshelf,
BookOrbit, and Storyteller focused verifiers pass. Python compilation, WUD
unit tests, Bash parsing, repository media-contract verification, and
`git diff --check` pass. CT112 now has 37 containers in 19 projects; the live
homelab has 63 containers in 26 projects. The clean-build declaration remains
40 Apps containers and 66 total in 29 projects.

The production bootstrap dry-run preserves all six PinePods recovery values
but stops at the pre-existing missing external
`PAPERLESS_GPT_OPENAI_API_KEY`; no placeholder was written to production.
`provision/verify.sh` passes ZFS, the complete live media contract, free-space
floors, HAOS recovery, and all LXC mounts, then reaches the same known
inventory boundary:

```text
FAIL LXC 112 has 37 active containers; expected 40
```

Those missing containers are the pre-existing Paperless-GPT, Prometheus, and
Loki live-deployment gap, not a PinePods failure. The scheduled appdata backup
completed successfully at `2026-07-26 02:12:11 CEST`; its success-only WUD
handoff completed at `02:14:00`, and no temporary backup snapshot remains.
The PinePods logical-dump hook is installed, but no routine on-demand PBS
backup was started.

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

# Audiobookshelf and Kavita addition — 2026-07-25

## Scope and live preflight

The repository adds one-container `audiobookshelf` and `kavita` projects to
Apps LXC 112, adopts their existing NPM hostnames, and replaces duplicate or
misconfigured Homarr applications with deterministic managed tiles.

Read-only live inspection found:

- PVE 9.1.2, healthy pools, about 521 GiB free on appdata, and 19.9 TiB free
  on `vault/shared`;
- 12 active Apps containers in five projects, deployed repository commit
  `796d0a4`, and no listeners on Apps ports 13378 or 5000;
- no Audiobookshelf/Kavita containers, Compose projects, or appdata trees;
- existing shared directories for audiobooks, podcasts, books, comics, and
  `mangas`, all owned by the Apps mapped user at the top level;
- NPM SQLite integrity `ok` with 36 active proxy hosts, including a stale
  Audiobookshelf route to `192.168.0.109:13378` and a Kavita route to
  `0.0.0.0:5000`;
- Homarr SQLite integrity `ok`, but two app records per service: one pair on
  the `dashboard` board pointing to `homarr.dev`, and another pair on the
  `Admin`/`default` boards using the intended hostnames;
- both hostnames already resolving through Pi-hole to NPM at `192.168.0.110`.

No live dataset, mount, guest, container, image, appdata, proxy row, Homarr
row, or production environment was changed during preflight or repository
validation.

## Declared end state

| Project | Image | Apps port | Durable state | Shared data | Update |
|---|---|---:|---|---|---|
| `audiobookshelf` | `ghcr.io/advplyr/audiobookshelf:latest` | 13378 | config SQLite, migrations, metadata, covers, logs, app backups | audiobooks RO; podcasts RW | backup-gated WUD |
| `kavita` | `ghcr.io/kareadita/kavita:latest` | 5000 | config SQLite, users, progress, covers, cache, app backups | books/comics/mangas RO | backup-gated WUD |

Both containers run as Apps UID/GID `1000:1000`. Audiobookshelf follows
upstream's required separate `/config` and `/metadata` local mounts on SSD
appdata. Its audiobook library remains read-only; a new narrow LXC bind maps
only `/vault/shared/media/podcasts` read-write at `/podcasts` so podcast
downloads do not require write access to the rest of shared media. Kavita maps
the existing books, comics, and `mangas` directories read-only.

The first administrator and libraries are created through each private web UI.
No new recovery secret is required. NPM maps:

- `audiobookshelf.rafael.media` to `192.168.0.112:13378`;
- `kavita.rafael.media` to `192.168.0.112:5000`.

Both routes preserve the existing wildcard certificate, enable WebSockets,
and allow only LAN `192.168.0.0/24` and Tailscale `100.64.0.0/10` before a
final `deny all`. Audiobookshelf receives the upstream-recommended 10 GiB
request limit and streaming-friendly buffering/timeouts. Homarr receives one
managed application and one tile per existing `dashboard`, `Admin`, and
`default` board for each service. The reconciler removes only the four stale
legacy app definitions and their six tiles after taking a focused SQLite
backup, then creates deterministic replacements.

## Update and recovery policy

Audiobookshelf documents `latest` as its stable release channel and ordinary
pull/recreate upgrades. Kavita documents GHCR `latest` as its stable channel
and ordinary pull/redeploy updates. Kavita's special ordered-upgrade warning
applies only to databases older than v0.7.6; this is a new current-version
deployment. Both are therefore eligible for the existing backup-gated WUD
route. The sequential runner stops unless Audiobookshelf's direct UI and
Kavita's `/api/health` recover after replacement.

The Apps freeze plus appdata ZFS snapshot protects both embedded databases
before WUD. Audiobook, podcast, book, comic, and manga files live under
`/vault/shared` and are not in PBS appdata backups. Audiobookshelf's built-in
database/cover backups and Kavita's `config/backups` provide application-level
restore material inside appdata, but neither substitutes for independent
protection of shared media.

If a future release requires ordered migration, disable WUD for that service,
retain the pre-update appdata snapshot and built-in backup, review upstream
release notes, and perform a manual tested upgrade. Rollback restores the
prior guest Git archive and old image, stops only the affected project without
deleting data, and restores the focused NPM/Homarr SQLite backup if needed.
Never delete recovered appdata or media until users, libraries, progress,
metadata/covers, OPDS/mobile access, and representative playback/reading are
verified.

Upstream references:

- [Audiobookshelf Docker installation, storage, stable tags, and upgrades](https://audiobookshelf.org/docs/documentation/install/docker/)
- [Audiobookshelf reverse-proxy and WebSocket guidance](https://github.com/advplyr/audiobookshelf)
- [Audiobookshelf database migration policy](https://audiobookshelf.org/docs/contributing/database-migrations/)
- [Kavita GHCR Compose and stable/nightly channels](https://wiki.kavitareader.com/installation/docker/github/)
- [Kavita Docker update and legacy ordered-upgrade guidance](https://wiki.kavitareader.com/installation/updating/updating-docker/)
- [Kavita Nginx Proxy Manager guidance](https://wiki.kavitareader.com/installation/remote-access/npm-example/)
- [Kavita backup and restore guidance](https://wiki.kavitareader.com/troubleshooting/faq/)

## Validation and pending live evidence

Repository validation passed:

- both Compose files parsed with the Apps guest's installed Docker Compose;
- all changed shell, Python, and Node files passed syntax checks, and the Git
  diff passed whitespace validation;
- both upstream `latest` manifests resolved for `linux/amd64`;
- the NPM and Homarr reconcilers ran twice against temporary copies of the live
  databases, preserved integrity, produced exactly 16 managed private routes
  and 14 managed Homarr apps/42 items, and left exactly one Audiobookshelf and
  one Kavita app;
- a complete `./bootstrap.sh --dry-run` passed against the live PVE state with
  a non-secret synthetic validation environment.

Live deployment remains pending with the earlier declared Apps generation. A
complete apply must use one committed repository revision across every
application LXC, add the narrow podcasts mount, preserve focused NPM/Homarr
backups, and then verify:

1. both projects healthy with exact images, identity, mounts, and WUD labels;
2. database integrity and canonical SSD appdata paths;
3. read-only library mounts plus mapped-user podcast write access;
4. private HTTPS/WebSockets and exactly one Homarr tile on every managed board;
5. first administrators, library scans, progress persistence, and
   representative audiobook/podcast playback plus book/comic reading;
6. a successful post-deployment encrypted appdata backup and sampled restore.

# Stillroom staging connection — 2026-10-18

## Scope and revisions

The user authorized changes to Stillroom and dothomelab, publishing to staging,
and connecting staging to production Immich and shared originals for dummy-album
testing. The user explicitly selected only owner albums beginning `Archive:`.

App runtime source: `4cf7509e4ceeace41ce543306f0e01a14ba545e5` on the private
`rafael-alani/immich-external-library-picture-removal` repository's `staging`
branch. Homelab implementation: `748016b69eebc6283d861bd4bcb300e12fc6c1ac` on
`codex/stillroom-staging`; subsequent commits add evidence only. Both were pushed
and fetched from GitHub. PVE uses a separate checkout at
`/root/dothomelab-stillroom-staging`; unrelated primary worktrees were preserved.

The private UI is **https://stillroom.staging.rafael.media**, CT114 port 8083.
The existing two-minute staging poller is active. A repository-only read deploy
key is retained in canonical staging appdata and registered read-only on GitHub.
It uses pinned GitHub host keys with strict checking; no personal/PVE private
credential or deploy key is mounted into the application container.

## Observed state and changes

Production Immich on CT112 reports **3.0.3**. Its photo bind remains read-only,
with API originals below `/old-photos` and the external library UUID recorded
in the tracked Stillroom configuration. The dedicated API key has exactly
`asset.read`, `user.read`, `album.read`, `library.read`. Values were never logged
or copied to the operator machine.

PVE hotplugged exactly CT114 mp1 photos and mp2 archive, with no guest stop:

| PVE | CT114 | Container |
|---|---|---|
| `/vault/shared/media/photos` | `/shared/media/photos` | `/old-photos` |
| `/vault/shared/archive` | `/shared/archive` | `/archive` |
| `/srv/appdata/docker/staging/stillroom/state` | same | `/data` |

New archive/state directories use host 101000:101000, guest 1000:1000. Existing
photo ownership/permissions were not changed. `pct config`, `findmnt`, `stat`,
`namei` and runtime UID access were inspected. There was ample free space (about
402 GiB appdata, 20 TiB shared at inspection).

Config enables observed-trash mode, `Archive:` scope, five-minute grace, three
successful observations, 30-second polls, and up to 20 bundles per scan. Live
moves are configured but gated by a disposable compatibility sample; at handoff
there were **zero matching albums, zero candidates and zero production moves**.
Archive batches go to `archive/temp` for later manual sorting.

The tracker is stable across release rollback. The deployer checks its SQLite
integrity and permits one-hour graceful shutdown. It never restores a prior
tracker generation independently of the external originals. Interrupted moves
or restores block and retain their journals.

## Verification

- Required app quality gate: **68 tests**, Python 3.11.2, disposable CT114 tree.
  Covers legacy and trash lifecycle, scoped membership, queues, video/Live Photo
  bundles, copy failure, no overwrite, rename/restore, interruptions and CSRF.
- Homelab checks: nine deployment tests (including stable journal rollback and
  private Git key scope), one lifecycle test, eight dashboard tests; shell syntax,
  registry validation and documentation checks passed.
- Docker image built and started healthy; Compose was validated with `--quiet`
  before each deployment. Deployed source labels matched accepted commits.
- Complete read-only API inventory: **26,718 assets**, 25,731 IMAGE and 987 VIDEO.
  Pagination and required fields validated in about 1.4 seconds. There are 27
  owner albums. The 3.0.3 contract uses `albumUsers` for ownership and paginated
  metadata search with `albumIds` for membership; one real album returned its
  expected 202 items. The deployed selector was then verified read-only against
  that owner album without altering worker scope/state.
- Desktop and 390px mobile UI inspected. Isolated demo exercised trash, grace,
  image/XMP previews and settings; no browser errors. No production UI action
  selected or trashed a real asset.
- A disposable fixture wholly below the archive mount passed live copy/unlink
  and restore as the service UID. All bytes verified; archive copies survived
  restore. The fixture was cleaned afterward. No real original was moved.
- Full `hosts/staging/verify.sh` passed: identities, mounts, accepted commits,
  SQLite, timers, Homarr enrollment, private DNS and trusted HTTPS. Existing
  Film-introspect and Form & Field remained healthy.

## Rollback and limits

Private NPM SQLite backup `database.sqlite.pre-stillroom-20261018` passed
integrity checks; the matching Pi-hole config snapshot is
`pihole.toml.pre-stillroom-20261018`. Both remain beside their canonical appdata.
Only the committed route helpers were transported to CT110, preserving its
unrelated `/opt/dothomelab` revision. Nginx validation passed, and the new route
uses LAN/Tailscale allow rules with a final deny. No public DNS/router exposure
was added.

Previous CT114 checkouts and app releases/images are retained. To pause moves,
stop Stillroom and temporarily pause the staging poller (it otherwise restarts
unhealthy apps). Code rollback retains the current stable tracker. It does not
undo moves. Restore individual bundles with the app's stopped-worker command,
then restore/rescan in Immich; archive copies are preserved. Never rewind the
tracker without reconciling later file changes.

The user's real dummy-album trash/move/Immich-restore journey remains untested.
The disposable verification sample is deliberately retained and must precede
other live moves. Archive renames belong between completed batches. No power-loss,
clean-host restore, database-only metadata recovery or production backup restore
was tested. Shared photos and archive are outside routine appdata PBS; moving
within the same ZFS pool is not an independent backup. Rebuilding without the
retained deploy key also requires fresh read-only GitHub key registration.

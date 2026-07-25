# ImmichFrame and Wizarr addition — 2026-07-25

## Declared outcome

Apps LXC 112 gains two single-container Compose projects:

| Project | Container | Apps port | Durable state | Update policy |
|---|---|---:|---|---|
| `immichframe` | `immichframe` | 8080 | optional config under `/srv/appdata/docker/immichframe` | `latest`, backup-gated WUD |
| `wizarr` | `wizarr` | 5690 | database and settings under `/srv/appdata/docker/wizarr` | `latest`, backup-gated WUD |

Both use the rolling image channel documented by their upstream projects.
Neither contains a separate database or infrastructure image that needs a
manual major-version migration policy.

Nginx Proxy Manager maps:

- `immichframe.rafael.media` to `192.168.0.112:8080`;
- `wizarr.rafael.media` to `192.168.0.112:5690`.

Both routes are restricted to `192.168.0.0/24` and Tailscale
`100.64.0.0/10`, followed by `deny all`. This is deliberate for ImmichFrame,
whose upstream documentation advises against public exposure, and avoids
making Wizarr invitation management public without separate authorization.

Homarr receives an app and tile for each service on the `dashboard`, `Admin`,
and `default` boards. The route and tile reconciliation remains idempotent and
retains pre-change SQLite backups.

## Verified live rollout status

On 2026-07-25, Wizarr was prepared from canonical appdata and deployed to
CT112 as the standalone `wizarr` Compose project. The container is healthy,
the direct and private HTTPS endpoints return the expected setup redirect,
its persistent SQLite database is non-empty and integrity-clean, and its
backup-gated WUD labels match the committed declaration.

The two NPM proxy rows and both Homarr applications already existed from the
current Infra generation, so this rollout did not rewrite either database.
NPM SQLite integrity and `nginx -t` passed; the target rows use the declared
Apps ports and LAN/Tailscale restrictions. Homarr SQLite integrity and health
passed with both applications, six target board items, and fourteen layout
placements. Pulse's command-disabled CT112 agent converged with Wizarr and the
complete running Docker inventory.

ImmichFrame was deployed later the same day after its dedicated scoped key was
added to production `/root/.env`. The repository dotenv parser confirmed the
value was present without printing it, and Immich returned HTTP 200 from the
album-read endpoint covered by the documented scope set. The prior verifier
incorrectly used `/api/users/me`, which requires an unrelated user permission;
the committed verifier now checks `/api/albums`.

The standalone `immichframe` project is running with zero restarts, detected
the existing Immich 3.0.3 server, and passed its focused UI, dependency,
credential, canonical-storage, image, Compose-project, and backup-gated WUD
checks. Pi-hole resolves `immichframe.rafael.media` to NPM and private HTTPS
returns 200 with certificate verification. NPM SQLite integrity and `nginx -t`
pass with the exact Apps backend and LAN/Tailscale restrictions. Homarr remains
healthy and integrity-clean with the deterministic ImmichFrame app, three
managed board items, and seven layout placements. Pulse converged with
ImmichFrame and the complete CT112 Docker inventory.

With both projects live, Apps runs 27 containers in fifteen Compose projects
and the homelab runs 51 containers. No placeholder or shared Immich credential
was created, printed, or committed.

## Recovery inputs

ImmichFrame requires a dedicated Immich API key in the PVE host
`/root/.env` as `IMMICHFRAME_API_KEY`. The key must have the read-only scopes
listed in `hosts/apps/immichframe/README.md`. The key is a recovery secret and
must never be committed.

Wizarr's first-run administrator, Jellyfin connection, API credential, and
invite policy are stored in `/srv/appdata/docker/wizarr`. They are covered by
the canonical appdata backup rather than duplicated in Git. After first launch,
connect Wizarr to `http://192.168.0.112:8096`.

## Backup and rollback

The existing daily PVE job snapshots all of
`rpool/appdata/docker`, uploads that appdata and `/root/.env` to PBS, and only
then hands eligible application updates to WUD. The two new paths and the
ImmichFrame secret therefore join the existing recovery set without a new
backup mechanism.

The Wizarr rollout began with no existing Wizarr container or appdata, and the
scheduled appdata service had completed successfully earlier the same day.
This routine empty-state deployment did not start an on-demand backup. NPM and
Homarr were not rewritten; their existing focused SQLite backups remain beside
canonical appdata. Once either service has durable user state, use a
task-specific rollback point before a destructive or schema-changing action.

Rollback does not delete new state:

1. restore the previous Git archive on the affected LXC;
2. redeploy the prior Compose definitions or stop only the two new projects;
3. restore the focused NPM/Homarr SQLite backup if route/tile rollback is
   required;
4. retain `/srv/appdata/docker/immichframe` and
   `/srv/appdata/docker/wizarr` until restore verification is complete.

## Verification contract

The focused verifiers require:

- both containers running under their declared Compose projects;
- the exact upstream `latest` image references and backup-gated WUD labels;
- working Apps HTTP endpoints;
- a working Immich dependency and an API key accepted by Immich;
- a non-empty, integrity-clean Wizarr SQLite database on canonical appdata;
- private NPM routes with the expected backends;
- Homarr apps, tiles, and layouts on all three managed boards;
- the deployed Git commit matching the intended committed revision.

Wizarr's Jellyfin link and a real invite redemption require first-run
application setup and must be recorded as an external prerequisite until
verified.

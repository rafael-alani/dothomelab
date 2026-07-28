# Sortarr addition — 2026-07-28

## Scope and preflight

Sortarr was added as a separate CT102 Compose project, with private Pi-hole
DNS, Nginx Proxy Manager TLS, and a tile on each managed Homarr board. Before
the change, PVE 9.1.2 and both ZFS pools were healthy, CT102 and CT110 were
running with their canonical mounts, TCP 9595 was unused, Sortarr appdata did
not exist, and neither NPM nor Homarr contained a Sortarr entry.

No shared-media path, Arr database, Arr queue, or existing Arr service
configuration was changed. The new service reads library metadata through
Sonarr and Radarr's APIs. Its durable state is below
`/srv/appdata/docker/sortarr`, inside the existing encrypted appdata backup
job.

## Upstream and desired state

The deployment follows the official
[repository](https://github.com/Jaredharper1/Sortarr),
[wiki](https://github.com/Jaredharper1/Sortarr/wiki), and
[Compose example](https://github.com/Jaredharper1/Sortarr/blob/main/docker-compose.yaml).
The official GHCR repository did not publish a `0.9.0` tag, so Git pins the
verified amd64 digest behind upstream's `latest` tag. Upstream marks Sortarr as
maintenance-only; `wud.watch=false` therefore keeps updates manual.

The deployed container:

- reports Sortarr 0.9.0 and has zero restarts;
- binds only `192.168.0.102:9595`;
- joins `servarr-hello_default` to reach `sonarr:8989` and `radarr:7878`;
- mounts only `/docker/sortarr:/data`, with no media/download mount;
- stores both Arr keys, the Basic-auth password, and the session secret in
  owner `1000:1000`, mode-0600 files below `/docker/sortarr/secrets`;
- trusts only the immediate NPM address `192.168.0.110`;
- uses the private `sortarr.rafael.media` route, limited to
  `192.168.0.0/24` and `100.64.0.0/10`.

On the first start, upstream treated the missing startup-state version as a
pre-0.8.3 upgrade and returned `upgrade_resave_required`. Because preflight
proved this was empty appdata, the non-secret 0.9.0 startup-state template was
installed before the focused restart. Clean bootstrap now seeds that template
only when the state is absent; it never overwrites an existing upgrade state.

## Live verification

Focused Sortarr verification passed:

- container `running/healthy`, zero restarts, exact digest, correct Compose
  project, and manual WUD policy;
- canonical appdata owner/mode and file-backed secret policy passed;
- unauthenticated direct and HTTPS API access returned HTTP 401;
- authenticated direct and HTTPS configuration APIs passed with setup
  complete, Basic auth active, and both Arr providers configured;
- `/api/shows` returned 30 Sonarr series and `/api/movies` returned 748 Radarr
  movies.

Infra verification passed with the optional Portainer Agent HTTP probe
disabled:

- Pi-hole resolves `sortarr.rafael.media` to NPM at `192.168.0.110`;
- NPM SQLite integrity and `nginx -t` pass; the exact backend is
  `192.168.0.102:9595` with TLS and final `deny all`;
- Homarr SQLite integrity passes with 25 managed apps, 75 managed items, and
  200 layout rows; Sortarr has one tile on `dashboard`, `Admin`, and
  `HomeAssistant`, with unauthenticated ping disabled because Basic auth would
  make it a false negative;
- the live media data contract passed without write probes, including
  canonical Sortarr appdata and unchanged shared-media access.

The standard Infra verifier's default Portainer Agent probe still fails
because nothing listens on CT110 TCP 9001, despite the existing
`portainer_agent` container being running. That pre-existing, unrelated
condition did not affect Sortarr, NPM, Pi-hole, Homarr, or the remaining Infra
verification.

The final live inventory is 73 running containers in 35 Compose projects:
CT102 has 18 in five projects, CT110 has 11 in five, and CT112 has 44 in
twenty-five; no running container reports unhealthy.

## Rollback and recovery

The rollout retained integrity-clean, mode-0600 pre-change databases:

- `/srv/appdata/docker/infra-nginx-proxy-manager/database.sqlite.pre-sortarr`
- `/srv/appdata/docker/homarr/db.sqlite.pre-sortarr`

Rollback is scoped to stopping/removing only the `sortarr` Compose project and
reverting its managed Pi-hole, NPM, and Homarr definitions. Retain
`/srv/appdata/docker/sortarr` and the two focused SQLite copies until a
separate cleanup task authorizes their removal. Production secrets remain only
in `/root/.env` and canonical Sortarr appdata; none entered Git or command
output.

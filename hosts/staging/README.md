# Staging

CT114 `staging` runs trusted development branches independently of production:
Debian 12, 6 CPUs, 16 GiB RAM, 512 MiB swap, 500 GiB replaceable root disk,
static `192.168.0.114`, unprivileged, on boot. Its only data bind is
`/srv/appdata/docker/staging`; it has no shared media, production appdata,
production `.env`, hardware, remote Docker API, or PVE credentials.

The first app is [film-introspect](https://github.com/rafael-alani/film-introspect/tree/staging)
at **https://film-introspect.staging.rafael.media**, private to LAN/Tailscale.
The API is Docker-internal and web port 8080 binds only the staging LAN IP.
Pi-hole provides the exact local record; NPM uses a dedicated
`*.staging.rafael.media` certificate and a deny-by-default source-address policy.
The route reconciler creates the certificate once with NPM's existing
Cloudflare DNS-01 credentials, then NPM manages renewals. ACME creates temporary
public TXT records; no public application A/AAAA record or router change is
needed. The previous `film-introspect-staging.rafael.media` private route is
retained as a transition alias; the new name is the canonical application origin.

CPU and memory are shared ceilings, not dedicated reservations. The root disk
is a ZFS `refquota` with zero `refreservation`; 500 GiB is not allocated up front
or guaranteed available. At resizing, the host had 407 GiB usable pool space,
18 GiB available RAM, and 8 physical CPU cores. All guests compete for these.
Staging's durable appdata bind is outside its root-disk quota and shares the
same SSD. Keep at least 60–90 GiB SSD headroom, monitor both paths and host RAM
in Pulse, and serialize builds. More storage or reduced existing usage is
required before staging can actually consume 500 GiB. No retained images,
data generations, or snapshots are automatically pruned.

## Push a staging release

Push commits to the app repository's `staging` branch. A guest-local systemd
timer checks `apps.json` every two minutes (up to ten seconds jitter).
It builds the new commit before stopping the old app, validates Compose,
copies the stopped app's data into an independent generation, starts the new
containers, and requires container health, direct UI/API health, and SQLite
integrity before accepting it. Cutover has a brief interruption; this is not
a zero-downtime platform.

App code updates are explicitly authorized by the staging workflow and do not
use WUD or wait for the daily PBS job. Every staging container has
`wud.watch=false`. This is a separate deployment path from production's
backup-gated image updates. Only people trusted to execute code inside this
guest should be able to push these branches. Builds have network access;
the LXC's resource limits contain their CPU/memory use.

On PVE:

```bash
pct exec 114 -- systemctl status dothomelab-staging.timer
pct exec 114 -- journalctl -u dothomelab-staging.service -n 80
pct exec 114 -- /opt/dothomelab/hosts/staging/deploy.py --verify
pct exec 114 -- /opt/dothomelab/hosts/staging/deploy.py --app film-introspect --retry
```

Build failures leave the current app running. A failed health check restores
the previous containers and their untouched data generation. The failed
commit/configuration is held until a new commit/configuration arrives or an
operator passes `--retry`. A persisted deployment journal recovers interrupted
cutovers. A failed attempt never deletes databases, volumes, images, source
bundles, or rollback generations. Those accumulate and need separately
reviewed cleanup; keep an eye on staging root and appdata capacity in Pulse.

To pause updates, disable the timer with
`pct exec 114 -- systemctl disable --now dothomelab-staging.timer`. This does
not interrupt an in-progress service run. A normal Git revert pushed to
`staging` deploys against current data; schema-incompatible downgrades require
an explicit choice of a retained data generation. Do not blindly switch the
current pointer to an older generation after users have added notes.

## Film-introspect settings

The first deployment uses the application's built-in demo mode and single-user
prototype mode. No production Jellyfin/Bazarr key is supplied. It is suitable
for developing the UI, API, and persisted notes; actual playback/subtitle
integration remains unverified until configured and exercised.

`initialize-env.py` generates a dedicated `STAGING_FILM_INTROSPECT_AUTH_SECRET`
in PVE `/root/.env` and renders only explicitly prefixed staging variables.
Optional keys are listed in `.env.example`. To connect a service later, set
the `STAGING_FILM_INTROSPECT_JELLYFIN_*` variables and
`STAGING_FILM_INTROSPECT_DEMO_MODE=false`, then rerun initialization on PVE.
Use a separate test server/key where possible: Jellyfin API keys are broadly
privileged, and branch code can read secrets explicitly supplied to it.
Each release keeps its scoped environment for rollback, mode 0600.

## Add another app

1. Add a credential-free GitHub repository URL, branch, unique port, private
   `app.staging.rafael.media` hostname, HTTP health path (optional JSON success key),
   Compose path, SQLite filenames, and container
   count to `apps.json`. A missing branch fails closed; main is never a fallback.
2. Add a reviewed Compose definition under `hosts/staging/<name>`. Follow the
   sample's `STAGING_SOURCE`, `STAGING_IMAGE_TAG`, `STAGING_COMMIT`,
   `STAGING_DATA`, and `STAGING_ENV` variables; name it `staging-<name>`.
   Only mount the app's data generation. Give every service a health check,
   resource/log limits, `wud.watch=false`, and the commit label. The runner
   checks `/` and the declared health endpoint; the sample requires JSON
   `{"ok":true}` at `/api/health`.
3. Extend the initializer to render that app's scoped runtime environment.
   Stateless apps can declare `sqlite: []`; SQLite apps list their database
   filenames. Other database engines require a new application-consistent
   backup/restore implementation and verification before enrollment.
4. Commit/push homelab configuration, then run `./bootstrap.sh --staging-only`
   from the updated PVE clone. This syncs the reviewed definitions, creates
   missing CT114 only, deploys registered apps, adds private DNS/TLS routes,
   updates the backup freeze list and Pulse, and runs focused verification.
   Existing production Compose projects are not redeployed.

The currently installed implementation uses Git declarations and branch polling.
The [deployment architecture research](../../docs/staging-platform-research-2026-10-04.md)
compares shared Actions workflows, self-hosted runners, and deployment dashboards.
No GitHub credential
is needed for the public test repository. Private repositories need a
separately scoped read-only credential/recovery design before enrollment.

## Recovery inputs and limits

Full `./bootstrap.sh` includes CT114. For an existing homelab use:

```bash
./bootstrap.sh --staging-only --dry-run
./bootstrap.sh --staging-only
./hosts/staging/verify.sh
```

Canonical appdata contains each app's `current.json`, `previous.json`, optional
`pending.json`/`failed.json`, scoped environment, and `releases/<id>/` with
Compose, source Git bundle, environment, commit metadata, and independent
`data/`. The entire tree is inside the existing encrypted appdata backup;
CT114 joins its short freeze window. No on-demand PBS job is needed for a
new empty deployment. Inclusion does not prove a later PBS backup or restore.

Guest root source checkouts, Docker images, and build cache are replaceable.
On recovery the accepted commit is rebuilt from its retained Git bundle before
checking GitHub for a new branch head. Registry access and upstream base
images remain external rebuild prerequisites; previously built images are
retained locally but are not exported into appdata. Film-introspect's staging
Dockerfiles install from the frozen Bun lockfile. Dependency/base-image
availability and a complete clean-host rebuild remain unverified externally.

An interrupted candidate never becomes current until all checks pass. SQLite
generation tests cover corruption, symlinks, build failures, health failures,
and crashes before/after the current-pointer commit. Live acceptance evidence
belongs in `docs/staging-addition-2026-10-04.md`.

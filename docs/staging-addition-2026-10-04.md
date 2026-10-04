# Staging LXC acceptance — 2026-10-04

## Result

Created unprivileged Debian 12 CT114 `staging`, static `192.168.0.114/24`,
MAC `02:7A:8C:00:01:14`, gateway `192.168.0.1`, Pi-hole DNS,
2 vCPU, 4096 MiB RAM, 512 MiB swap, and a 32 GiB `local-zfs` root.
It starts on boot after production. The only data mount is
`/srv/appdata/docker/staging`, host UID/GID `100000:100000` and mode 0700.
There are no production appdata, shared media, GPU, TUN, or remote Docker API
mounts/listeners. Root usage after installation was about 2.1 GiB.

Film-introspect is healthy at
https://film-introspect-staging.rafael.media, using the private NPM route and
the existing trusted `*.rafael.media` certificate. Pi-hole resolves it exactly
to `192.168.0.110`. A request from the proxy container's non-allowed loopback
source returned HTTP 403; LAN HTTPS returned the healthy application. No
router forwarding or public DNS changes were made. A separate internet-origin
request was not tested.

The app starts in demo mode with its native local single-user profile.
Its unique auth secret is stored in PVE `/root/.env` and scoped staging
appdata, never Git. No production Jellyfin/Bazarr keys were supplied.
Real playback, account flows, and external integrations are not acceptance
claims for this deployment.

## Deployment and persistence evidence

- Created the previously absent `staging` branch from main
  `11d22da0b943b173bfb13a71c52f804000cfdb58`.
- Added frozen Bun lockfile installs to both app Dockerfiles. The first live
  build exposed missing workspace dependency links in the API image; the
  health gate rejected it. The staging branch now copies the API/contracts
  workspace links alongside Bun's shared dependency store.
- First accepted app commit:
  `a05aec7fc944565039c8789c7758594760a3f6b1`.
- Created one explicitly temporary demo note through the application API.
- Pushed the README staging-guide link as
  `8c8976c7a08b9f56f6c2c71e7b7f25e3560d8c7c`. The systemd timer independently
  detected, built, and accepted it at 22:07:49 Europe/Amsterdam.
- Both API and web containers were healthy, labeled with the accepted commit;
  `/api/health`, `/api/config`, demo playback, the HTTPS live screen, and the
  browser library screen worked.
- The same note ID/body survived the automatic release in a different data
  generation. The note was then deleted only from the current app through its
  API. Both current and previous SQLite generations passed integrity checks.
- Failed-first-release and previous accepted images/data/source bundles remain
  retained. No volumes, databases, images, or rollback generations were pruned.

The runner polls every two minutes with up to ten seconds of jitter. Build
failures preserve the running release; cutover health failures restore the
previous release and untouched data generation. Seven automated tests passed
for independent data copies, corrupt databases, symlink rejection, failed
builds, failed health checks, and interrupted commits. Health-failure rollback
to an already accepted release is covered by these tests; it was not induced
against the live accepted app. The successful live update proves note
persistence, not a destructive whole-guest or PBS restore.

The application itself passed all 10 Bun tests, TypeScript checks for every
workspace, and production API/web builds. Docker Compose validation passed
before deployment; actual images subsequently built and ran inside CT114.

## Recovery, monitoring, and provisioning findings

`APPLICATION_CTIDS`, `PULSE_DOCKER_CTIDS`, and `ALL_CTIDS` include CT114.
Pulse's supported reconciliation verified PVE visibility for all LXCs and
command-enabled Docker agents for CT102, CT110, CT112, and CT114. Image updates
in Pulse remain disabled. Staging images have `wud.watch=false`; their explicit
branch deployment workflow uses per-release rollback rather than WUD.

CT114 was added to the existing appdata snapshot freeze list. Its source
bundles, accepted/previous state, environments, and independent databases
are under the existing appdata dataset. The most recent scheduled PBS service
had succeeded at 02:23:13 Europe/Amsterdam before staging existed. No on-demand
backup was started; a later successful snapshot and a staging restore test
are not established by this task.

The focused PVE dry run passed before creation. During creation, bootstrap's
inherited `umask 077` caused an omitted Debian template parent directory,
`/etc`, to be created with mode 0700. Root DNS worked, but apt's `_apt` account
could not traverse the directory. Only CT114 `/etc` was corrected to 0755;
guest creation now runs with `umask 022`, while secret work retains 077.
The package-manager account then resolved DNS and package installation passed.

PVE `pct set --nameserver` persisted the setting but did not change the running
guest's resolver file. The staging provisioner now reconciles both live and
next-boot DNS. The focused verifier then passed guest identity, isolation,
exact deployed homelab commit, container commit/count, SQLite integrity,
timer state, backup freeze inclusion, local DNS, and trusted HTTPS.

Existing production Compose projects were not redeployed or stopped.
The final Git archive is synchronized to the Docker guests for consistent
`DEPLOYED_COMMIT` metadata. Full clean-host reconstruction remains untested;
network registries/base images remain external prerequisites. Retained staging
build/cache/release generations need a separate capacity/cleanup task.

See [the staging operations guide](../hosts/staging/README.md).

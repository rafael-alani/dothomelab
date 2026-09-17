# Scheduled update automation repair

The user required inspection and automation repairs without manually starting
any backup or update, even once. No runner mutation, forced WUD scan, image
pull, backup, or application update is part of this deployment.

## Findings

- The September 17 scheduled backup completed at 02:11:38 CEST and its
  `OnSuccess=` updater completed at 02:17:26. The timer remains daily at 02:00
  plus up to 15 minutes of random delay; no separate update timer exists.
- Historical logs show successful image changes for Audiobookshelf and Apps
  Portainer/Agent. FlareSolverr and Shelfarr/Libation were recreated with the
  same old image IDs, falsely reported as successful updates.
- CT102's ZFS root quota was 8 GiB, with about 67 MiB free; the backing rpool
  had 451 GiB available. The WUD Docker trigger resolved, rather than rejected,
  its Docker `followProgress` error callback. This permits a failed pull to be
  followed by stopping/recreating the old container.
- Cached discovery showed ten unsupported-registry errors: n8n, Storyteller,
  and eight LinuxServer applications. These were silently absent from the
  runner's update candidates. Cross-seed was an eleventh error: WUD selected
  `6-arm64` ahead of `6` on the amd64 guest.
- n8n's registry also returned HTTP 429 with Docker Hub's unauthenticated pull
  limit message. Hourly scans and event-driven full-host rescans after every
  replacement caused avoidable repeated registry requests.
- The guest runner's stdout was present under the journal identifier but not
  included by `journalctl -u` because `lxc-attach` changes its cgroup.

## Desired state and validation

Servarr uses a 32 GiB root quota, preserving all images and appdata. WUD stays
on its already-installed digest with read-only Git-managed compatibility code.
The code adds anonymous public registry token handling, constrains cross-seed
to major tag `6`, and rejects pull errors before application stop/removal.
Application labels, manual update exclusions, backup gate, health checks,
Storyteller/music interlocks, and `PRUNE=false` are preserved.

Discovery is scheduled at noon with Docker events disabled. The nightly
backup-gated runner still performs its fresh scan; these two daily scans are
more than six hours apart. Registry errors are reported as incomplete runs,
and a replacement on the old image cannot be reported as successful.

Local validation: seven isolated Node tests cover registry authentication,
tag constraints, and failed/successful pull callbacks. Fifteen Python tests
cover guards, GET-only audits, discovery errors and unchanged-image rejection.
Shell syntax and Git whitespace checks pass. Read-only probes using the exact
installed WUD classes successfully fetched public LSCR and GitLab tags and
manifests, and cross-seed's correct amd64 manifest. n8n token authentication
works but its manifest remains subject to the observed external rate limit.

The configuration is applied with Compose validation and `up --pull never`
only for WUD, retaining the existing image and populated store. No application
containers are recreated as part of the repair. The natural next nightly run
must establish that the registry quota has recovered and application updates
now complete; that outcome cannot be claimed from these passive checks.

## Recovery and rollback

Bootstrap uses the updated root size, exact WUD image, compatibility bind and
runner directly from Git. Existing appdata and `/root/.env` inputs are unchanged;
no new recovery secrets are needed. Restore the previous WUD Compose and
runner from Git or the retained guest deployment to undo the automation code,
then validate Compose and recreate WUD on the same retained image. Keep the
32 GiB root allowance; do not shrink a populated root to reproduce disk-full
conditions. No rollback image, database, snapshot or durable data was deleted.

Sources: [WUD custom registry configuration](https://github.com/getwud/wud/blob/main/docs/configuration/registries/custom/README.md),
[n8n official Docker image](https://github.com/n8n-io/n8n/blob/master/docker/images/n8n/README.md).
Compatibility behavior was checked against the installed image's JavaScript,
not assumed from newer upstream source.

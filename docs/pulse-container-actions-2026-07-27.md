# Pulse container actions and Jellyfin recovery — 2026-07-27

## Scope and authority

Pulse's existing unified agents in Docker LXCs `102`, `110`, and `112` now
enable command execution. Authenticated Pulse users can start, stop, and
restart Docker containers in those guests. The Proxmox source keeps its
propagated `PVEAuditor` role, so this change does not grant guest lifecycle,
storage mutation, network mutation, or shell access on the PVE host. Pulse's
`PULSE_DISABLE_DOCKER_UPDATE_ACTIONS=true` setting remains in force: image
updates stay exclusive to the backup-gated WUD handoff.

Pulse does not permit a report-only token to gain the `agent:exec` scope in
place. `configure-monitoring.py` therefore preserves the durable agent ID,
mints a fresh command-enabled token through Pulse's authenticated install
endpoint, and runs the signed unified installer without logging the token. A
clean build follows the same scoped enrollment path. Both normal reconciliation
and `--verify` now fail unless every declared unit is active with host, Docker,
and command execution enabled and an online container from every declared host
advertises the `restart` capability.

The Pulse login is consequently Docker lifecycle-administrator access. Its NPM
route remains private to LAN and Tailscale, and the production credential
remains only in `/root/.env`.

## Live diagnosis

Before the change, PVE 9.1.2 and both ZFS pools were healthy, and all managed
LXCs were running. Pulse was healthy, but all three agent units omitted
`--enable-commands`; attempted action plans returned HTTP 409 with the UI
message `Action execution is unavailable`.

Jellyfin was running and reported healthy with no restarts. Its read-only
`/media` bind resolved to the mounted `vault/shared` dataset, representative
files were visible, and recent playback/transcoding completed successfully.
The library monitor nevertheless repeatedly queued refreshes without loading
the user's new media, so a scoped container restart was appropriate. No media,
appdata, database, mount, or permission mutation was required.

## Live apply and verification

The pre-change unit from each Docker LXC is retained at
`/var/lib/pulse-agent/pulse-agent.service.pre-command-actions-20260727`.
Reconciliation installed Pulse agent `v6.1.2` with the original durable agent
IDs and fresh per-host tokens. The active Servarr, Infra, and Apps tokens each
have `agent:exec` plus the existing agent/config/Docker reporting scopes. After
matching live runtime token IDs, six superseded report-only or diagnostic
tokens were revoked; exactly the three active `dothomelab-{servarr,infra,apps}`
tokens remain.

Pulse's paginated resource verification passed for CT102, CT110, and CT112.
Each host has an online container advertising the `restart` capability, and
the complete running Docker inventory plus the required Infra Syncthing
container is present. Token rotation temporarily retained stale resource rows,
which exposed and fixed the verifier's former one-page assumption; no runtime
or resource was deleted to hide that transitional state.

Jellyfin restart request `dothomelab-jellyfin-restart-20260727` was planned,
approved by the authenticated administrator, and executed through Pulse as
action `act_93ad63f6ca202606c9b0fd9e70698558`. Pulse completed it at
`2026-07-27T16:03:43Z` with agent-attested typed read-after-write evidence:
the container was running before and running after the completed mutation.

Jellyfin's new Docker start time is
`2026-07-27T16:03:43.612824972Z`. It became healthy, completed core startup in
3.7 seconds, reattached directory watching for books, series, music, and
movies, and resumed the queued ebook refresh. The complete Apps `media`
verifier passed for Jellyfin, Seerr, Jellystat, their direct endpoints, project
membership, health, and update labels. No media, appdata, database, mount,
permission, network, or PVE guest state changed, so this routine lifecycle
repair did not justify an on-demand backup; the scheduled appdata job remains
the recovery path.

# Pulse container actions and Jellyfin recovery — 2026-07-27

## Scope and authority

Pulse's existing unified agents in Docker LXCs `102`, `110`, and `112` now
enable command execution. Authenticated Pulse users can start, stop, and
restart Docker containers in those guests. The Proxmox source keeps its
propagated `PVEAuditor` role, so this change does not grant guest lifecycle,
storage mutation, network mutation, or shell access on the PVE host. Pulse's
`PULSE_DISABLE_DOCKER_UPDATE_ACTIONS=true` setting remains in force: image
updates stay exclusive to the backup-gated WUD handoff.

`configure-monitoring.py` upgrades an existing Docker-monitoring agent in
place with Pulse's signed `--update` installer path and its saved runtime
token. A clean build mints the install command with `enableCommands=true` and
passes `--enable-commands`. Both normal reconciliation and `--verify` now fail
unless every declared agent unit is active with host, Docker, and command
execution enabled.

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

Pending final live evidence.

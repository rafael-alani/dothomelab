# Pulse

The `pulse` project runs the official `rcourtman/pulse:latest` community image
on Infra port 7655. NPM publishes `https://pulse.rafael.media` only to the LAN
and Tailscale. Authentication is fixed from `PULSE_AUTH_USER` and
`PULSE_AUTH_PASS` in Proxmox `/root/.env`. Authenticated Pulse users may run
Docker lifecycle actions such as restart, start, and stop through the unified
agents. Docker image-update actions remain disabled because WUD is the only
backup-gated update path.

`configure-monitoring.py` creates a least-privilege `pulse-monitor@pve` API
identity with the `PVEAuditor` role. That one PVE connection discovers every
current VM and LXC, including all four managed LXCs. Docker is an inside-guest
boundary: the same script installs Pulse's unified agent with Docker reporting
and command execution enabled in every VMID listed by `PULSE_DOCKER_CTIDS` in
`provision/inventory.env`. The agents act only inside their Docker guests; the
PVE API identity remains `PVEAuditor` and cannot start, stop, or restart guests.
Existing report-only agent tokens cannot gain the `agent:exec` scope in place,
so reconciliation securely mints a fresh command-enabled token while preserving
the agent's durable ID.

Keep `PULSE_DOCKER_CTIDS` synchronized whenever Docker is added to or removed
from an LXC. PVE discovers later LXCs automatically, but a new Docker LXC is
not fully monitored until its guest-local agent is declared, installed, and
verified. `configure-monitoring.py --verify` compares the live PVE LXC list
and each declared Docker host/container inventory with Pulse's resource API.
It also verifies that every declared agent is active with host, Docker, and
command execution enabled and that an online container on each host advertises
Pulse's `restart` capability. A unit flag without a connected command channel
therefore cannot silently return the UI to `Action execution is unavailable`.
It also requires the Infra `syncthing` application container to be online in
Pulse, so a stopped container cannot disappear from both the live Docker
inventory and the monitoring check unnoticed.

Pulse configuration, encrypted PVE credentials, token hashes, metrics, and
sessions persist under `/srv/appdata/docker/pulse`. The server image is
backup-gated through WUD; unified agents keep their upstream checksum/signature
verified auto-update path enabled and update from the running Pulse server.
PVE temperature/physical-disk collection and Pulse Docker update actions stay
disabled. Treat the Pulse login as Docker lifecycle-administrator access.

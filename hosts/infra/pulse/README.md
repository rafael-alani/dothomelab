# Pulse

The `pulse` project runs the official `rcourtman/pulse:latest` community image
on Infra port 7655. NPM publishes `https://pulse.rafael.media` only to the LAN
and Tailscale. Authentication is fixed from `PULSE_AUTH_USER` and
`PULSE_AUTH_PASS` in Proxmox `/root/.env`, and Docker lifecycle/update actions
are disabled because this deployment is for resource monitoring.

`configure-monitoring.py` creates a least-privilege `pulse-monitor@pve` API
identity with the `PVEAuditor` role. That one PVE connection discovers every
current VM and LXC, including all four managed LXCs. Docker is an inside-guest
boundary: the same script installs Pulse's unified agent with Docker reporting
and command execution disabled in every VMID listed by `PULSE_DOCKER_CTIDS` in
`provision/inventory.env`.

Keep `PULSE_DOCKER_CTIDS` synchronized whenever Docker is added to or removed
from an LXC. PVE discovers later LXCs automatically, but a new Docker LXC is
not fully monitored until its guest-local agent is declared, installed, and
verified. `configure-monitoring.py --verify` compares the live PVE LXC list
and each declared Docker host/container inventory with Pulse's resource API.

Pulse configuration, encrypted PVE credentials, token hashes, metrics, and
sessions persist under `/srv/appdata/docker/pulse`. The server image is
backup-gated through WUD; unified agents keep their upstream checksum/signature
verified auto-update path enabled and update from the running Pulse server.

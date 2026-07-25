# n8n and Pulse addition — 2026-07-25

## Scope and placement

Infra LXC 110 gains two independent, single-container Compose projects:

| Project | Image | Infra port | Durable state | Update path |
|---|---|---:|---|---|
| `n8n` | `docker.n8n.io/n8nio/n8n:latest` | 5678 | workflows, credentials, settings, and SQLite under `/srv/appdata/docker/n8n`; encryption key in `/root/.env` | backup-gated WUD |
| `pulse` | `rcourtman/pulse:latest` | 7655 | configuration, credential ciphertext, token hashes, sessions, and metrics under `/srv/appdata/docker/pulse` | backup-gated WUD |

Both NPM routes allow only `192.168.0.0/24` and `100.64.0.0/10`, deny all
other clients, retain WebSocket support, and use the existing wildcard
certificate. No router forwarding or public exposure is added. Homarr receives
an n8n and Pulse tile on each managed dashboard.

Infra's declared memory changes from 2 GiB to 4 GiB. Before the change it had
about 806 MiB available inside its old limit; the PVE host had about 17 GiB
available, so the increase does not require moving data or stopping guests.

## Pulse coverage contract

Pulse uses a dedicated `pulse-monitor@pve!dothomelab` token. The user receives
only the built-in `PVEAuditor` role at `/`, so the PVE source automatically
discovers all current and future LXCs without lifecycle permissions.

PVE cannot see Docker inventory inside unprivileged LXCs. The
`PULSE_DOCKER_CTIDS=(102 110 112)` inventory therefore drives installation of
Pulse's unified agent inside each Docker LXC with host and Docker reporting
enabled and command execution disabled. When Docker moves to another LXC,
update that array, bootstrap, verification, documentation, and the live agent
fleet together. Agent updates retain Pulse's upstream checksum/signature
verification path; Pulse Docker update actions remain disabled.

## Recovery behavior

`./bootstrap.sh` prepares both canonical appdata paths, deploys the projects,
creates or verifies the n8n owner, creates the least-privilege PVE token when
needed, registers the PVE source, installs missing Docker agents, reconciles
NPM and Homarr, and installs the updated sequential WUD runner. The focused
verifiers require private HTTPS health, exact Compose/WUD labels, canonical
appdata ownership, working n8n authentication, all declared LXCs in Pulse, and
Docker reports from every declared Docker LXC.

The first deployment uses `scripts/initialize-n8n-pulse-env.py` once to add
missing secrets without printing them. Subsequent rebuilds recover those
values from `/root/.env`; `PULSE_PVE_TOKEN_SECRET` is written there when the
PVE token is first created. Losing `N8N_ENCRYPTION_KEY` can make stored n8n
credentials unrecoverable.

## Live evidence

Pending deployment and focused verification.

## Upstream references

- [Pulse repository and Docker installation](https://github.com/rcourtman/Pulse)
- [Pulse unified-agent documentation](https://github.com/rcourtman/Pulse/blob/main/docs/UNIFIED_AGENT.md)
- [n8n Docker installation](https://docs.n8n.io/hosting/installation/docker/)
- [n8n reverse-proxy environment guidance](https://docs.n8n.io/hosting/configuration/configuration-examples/webhook-url/)

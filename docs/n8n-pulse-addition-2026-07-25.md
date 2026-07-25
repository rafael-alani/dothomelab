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

Before mutation, PVE 9.1.2 and both pools were healthy, canonical appdata had
about 514 GiB available, ports 5678/7655 were free, Infra had about 806 MiB
available inside its old 2 GiB limit, and the host had about 17 GiB available.
The verified rollback set is:

- `rpool/appdata/docker@pre-n8n-pulse-20260725T072506Z`;
- `/root/.env.pre-n8n-pulse-20260725T072506Z`, byte-matched to the pre-change
  environment and retained root-owned mode `0600`;
- mode-`0600` NPM and Homarr SQLite backups named `.pre-n8n-pulse`.

The live apply increased CT110 to 4 GiB without a restart and left about 2.4
GiB available after both services started. Both Compose files rendered on
Infra. n8n `2.31.6` and Pulse agent/server `v6.1.1` are healthy; n8n owner
authentication, direct/private HTTPS health, canonical appdata, exact image
channels, and backup-gated WUD labels passed.

NPM integrity is `ok` with 52 proxy hosts and six certificates. All eighteen
managed routes target the declared backend and are restricted to LAN/Tailscale.
Homarr integrity is `ok` with 16 managed apps, 48 items, and all 112 expected
layout rows. Both SQLite reconciliations passed against read-only copies before
they were applied live.

Pulse's PVE source is connected and returned LXCs `102`, `110`, `112`, and
`113`. Its three online Docker agents matched every running container:
Servarr 13/13, Infra 11/11, and Apps 16/16 (Apps also reports three stopped
containers). Every agent reports version `v6.1.1`, readiness, Docker enabled,
commands disabled, and checksum/signature-verified auto-update enabled. The
PVE identity has only propagated `PVEAuditor`; temperature/physical-disk
collection and Docker update actions are disabled.

The encrypted post-deployment backup
`host/afa-appdata/2026-07-25T07:41:10Z` completed successfully. It scanned
247.367 GiB of appdata, reused 245.699 GiB (99.3%), uploaded 1.668 GiB plus
metadata, included the mode-`0600` `/root/.env` recovery input, removed its
temporary ZFS snapshot, and triggered a successful backup-gated WUD run. PBS
`verify-new` then automatically started server-side verification of the exact
new snapshot. That asynchronous datastore task was not treated as an
application-deployment gate. The on-demand run is historical evidence from
this deployment, not policy: future routine changes rely on the daily timer
and do not start or wait for PBS verification.

The live `./bootstrap.sh --dry-run` reached recovery-environment validation and
exposed a pre-existing prerequisite for older, undeployed Apps definitions:
`IMMICHFRAME_API_KEY`, `PAPERLESS_GPT_OPENAI_API_KEY`,
`SLSKD_SOULSEEK_USERNAME`, and `SLSKD_SOULSEEK_PASSWORD` do not exist in the
current recovery environment or any retained environment copy. They are
external credentials and were not fabricated. Other missing internal values
for those same undeployed projects were likewise left outside this focused
change. n8n's built-in JavaScript task runner is operational; an external
Python task runner is not declared or verified.

A destructive clean-host rebuild was not performed, so the repository's
existing clean-bootstrap verification boundary remains. The focused n8n/Pulse
definitions, live deployment, private routes, dashboard entries, monitoring
coverage, recovery inputs, and rollback set are verified independently of the
pre-existing Apps prerequisite above.

## Upstream references

- [Pulse repository and Docker installation](https://github.com/rcourtman/Pulse)
- [Pulse unified-agent documentation](https://github.com/rcourtman/Pulse/blob/main/docs/UNIFIED_AGENT.md)
- [n8n Docker installation](https://docs.n8n.io/hosting/installation/docker/)
- [n8n reverse-proxy environment guidance](https://docs.n8n.io/hosting/configuration/configuration-examples/webhook-url/)

# Central WUD

WUD runs as a separate stack on infra. It watches infra through the local Docker socket and reaches apps (`192.168.0.112`) and servarr (`192.168.0.102`) through mutually authenticated Docker API endpoints on port 2376.

The UI/API is published only as `127.0.0.1:3001` inside LXC 110. The Proxmox-host updater uses `pct exec 110` to run `run-updates.py`; do not expose the unauthenticated UI directly to the LAN.

## PKI

Generate the CA and certificates into a new ignored/off-host directory:

```bash
scripts/generate-docker-api-pki.sh secrets/docker-api-pki
```

Install `ca.pem`, the matching `server-cert.pem`, and matching server `key.pem` as `/etc/docker/tls/{ca.pem,server-cert.pem,server-key.pem}` in apps and servarr. Install `ca.pem`, `client/client-cert.pem`, and `client/key.pem` as `/etc/dothomelab/wud-docker-api/{ca.pem,client-cert.pem,client-key.pem}` in infra. Private keys must be root-owned mode `0400`.

After copying certificates, run the common Docker API installer in each remote LXC with its host-specific systemd drop-in. The installer enables Docker live-restore before restarting dockerd and rolls back the added listener if validation fails.

The CA private key and WUD client key grant root-equivalent Docker access. Keep them outside Git, include an off-host recovery copy, and never expose port 2375.

## Update policy

All Docker watchers use `WATCHBYDEFAULT=false`. Eligible application containers must set:

```yaml
labels:
  wud.watch: "true"
  wud.watch.digest: "true"
  wud.trigger.include: "docker.backupgated"
```

The Docker trigger is `AUTO=false` and `PRUNE=false`. WUD may discover updates hourly, but only the PBS `OnSuccess=` updater executes mutations. WUD itself, databases, and legacy stacks remain excluded.

Use `run-updates.py --dry-run` to force a scan and report every watched
container's `docker.backupgated` association without invoking a mutation.

The sequential runner also checks Infra Nginx Proxy Manager and the Infra,
Apps, and Servarr Portainer status APIs and Portainer Agent ping endpoints
after WUD replaces those containers. A running container alone is insufficient
because an unassociated Portainer Agent can keep its process alive after
closing its API listener.

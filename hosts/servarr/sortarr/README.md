# Sortarr

Sortarr is a read-only Sonarr/Radarr analytics dashboard on CT102. It uses the
upstream `latest` image at the repository-pinned amd64 digest that reports
version 0.9.0. Upstream is in maintenance mode and does not publish a `0.9.0`
GHCR tag, so WUD watching is disabled and updates are manual.

The service:

- publishes only `192.168.0.102:9595`;
- joins `servarr-hello_default` to reach Sonarr and Radarr by container name;
- mounts only `/docker/sortarr` at `/data`, with no media or download mount;
- stores API keys, the Basic-auth password, and the session secret in mode-0600
  files below `/docker/sortarr/secrets`;
- trusts only the immediate Nginx Proxy Manager host at `192.168.0.110`;
- is exposed privately at `https://sortarr.rafael.media` to LAN and Tailscale;
- is linked from all three managed Homarr boards.

`scripts/initialize-sortarr-env.py` creates the dedicated Basic-auth password
and session secret in Proxmox `/root/.env`. It preserves the existing values
and reuses the recovered `SONARR_API_KEY` and `RADARR_API_KEY`. Retrieve the
password from production `/root/.env`; never copy it into Git or logs.

Focused recovery and deployment:

```bash
scripts/initialize-sortarr-env.py --env-file /root/.env
pct push 102 /root/.env /run/dothomelab.env --perms 0600
pct exec 102 -- bash -lc \
  'trap "rm -f /run/dothomelab.env" EXIT
   source /opt/dothomelab/hosts/common/load-env.sh
   load_dothomelab_env /run/dothomelab.env
   /opt/dothomelab/hosts/servarr/sortarr/configure.sh'
scripts/deploy-compose.sh 102 hosts/servarr/sortarr/compose.yaml
pct exec 102 -- /opt/dothomelab/hosts/servarr/sortarr/verify.sh
```

Rollback stops and removes only the `sortarr` container/project and disables
the managed NPM/Homarr/DNS entries in a repository revert. Retain
`/srv/appdata/docker/sortarr` for credentials, settings, and cache recovery.

Upstream references:

- <https://github.com/Jaredharper1/Sortarr>
- <https://github.com/Jaredharper1/Sortarr/wiki>
- <https://github.com/Jaredharper1/Sortarr/blob/main/docker-compose.yaml>

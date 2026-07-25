# Paperless-ngx

The `paperless-ngx` project runs three containers on Apps LXC 112:

- Paperless-ngx on `192.168.0.112:8002`;
- application-private PostgreSQL 18;
- application-private Valkey 9.

NPM publishes `https://paperless.rafael.media` only to LAN
`192.168.0.0/24` and Tailscale `100.64.0.0/10`. The project joins the external
Docker bridge `dothomelab-paperless`; Paperless-ngx has the stable network
alias `paperless-ngx` for the separately deployed Paperless-GPT project.

All durable paths are below `/srv/appdata/docker/paperless` and are included
in the encrypted appdata backup. Paperless originals stay there deliberately
so the same recovery input covers both metadata and documents. The production
`/root/.env` carries the PostgreSQL password, Paperless secret and initial
administrator credentials, and the fixed API token used by the dedicated
Paperless-GPT service account.

## Backup and restore

The daily PVE backup creates a portable `latest` dump, rotates the prior copy
to `previous`, and then briefly freezes Apps before snapshotting all appdata.
Before a database migration or manual upgrade, run the same dump and its
isolated restore test explicitly:

```bash
pct exec 112 -- /opt/dothomelab/hosts/apps/paperless-ngx/backup-database.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/paperless-ngx/restore-test.sh
```

The restore test starts an isolated PostgreSQL 18 container, restores the
custom-format dump, compares user and document counts, stops the test
container, and retains its data/evidence under
`/srv/appdata/docker/paperless/restore-tests`. Removing retained evidence is a
separate cleanup task.

For normal recovery, restore `/srv/appdata/docker` and `/root/.env`, then run
`./bootstrap.sh`. Bootstrap prepares the shared network, deploys
`paperless-ngx`, and later reconciles the dedicated Paperless-GPT API identity.

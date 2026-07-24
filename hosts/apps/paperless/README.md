# Paperless

The `paperless` project runs on Apps LXC 112:

- Paperless-ngx on `192.168.0.112:8002`;
- Paperless-GPT on `192.168.0.112:8003`;
- private PostgreSQL 18 and Valkey dependencies.

NPM publishes `https://paperless.rafael.media` and
`https://paperless-gpt.rafael.media`. Both routes allow only
`192.168.0.0/24` and Tailscale `100.64.0.0/10`. Keep Paperless-GPT private:
upstream provides no authentication, and anyone who reaches it can alter
Paperless documents, change its settings, and spend LLM credits.

All durable paths are below `/srv/appdata/docker/paperless` and are therefore
included in the encrypted appdata backup. The production `/root/.env` carries
the PostgreSQL password, Paperless secret/admin credentials, fixed 40-hex API
token for a dedicated password-disabled service superuser, and OpenAI API key.
Paperless-GPT uses OpenAI only; changing providers requires an explicit
Compose and recovery-contract change.

`PDF_UPLOAD` and `PDF_REPLACE` are disabled. Do not enable document replacement
until a logical dump and restore test have passed and original documents have
separate verified protection.

## Backup and restore

The daily PVE backup creates a portable `latest` dump (rotating the prior copy
to `previous`) and then briefly freezes Apps before snapshotting all appdata.
Before a database migration or manual upgrade, run the same dump explicitly
and restore-test it:

```bash
pct exec 112 -- /opt/dothomelab/hosts/apps/paperless/backup-database.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/paperless/restore-test.sh
```

The backup script keeps `latest` plus `previous` under
`/srv/appdata/docker/paperless/backups`. The restore test starts an isolated
PostgreSQL 18 container, restores the custom-format dump, compares user and
document counts, stops the test container, and retains its data and evidence
under `restore-tests`. Removing retained tests is a separate cleanup task.

For normal recovery, restore `/srv/appdata/docker` and `/root/.env`, then run
`./bootstrap.sh`. Bootstrap deploys the project, recreates the dedicated
password-disabled Paperless-GPT service superuser and fixed API token through
Django's ORM, reconciles the private NPM routes and Homarr tiles, and runs the
focused verifier.

# dothomelab

Git-managed configuration and recovery for Rafael's Proxmox homelab: media,
books, music, photos, documents, home automation, private tools, and staging.
The repository declares five LXCs and HAOS VM104 on PVE node `afa`; VM101 is
unmanaged. Start with the [user manual](USER_DOC.md) to use the services, or
the [documentation map](docs/README.md) to work on the homelab.

## Back up before migration

Recovery needs this repository, production `/root/.env`, current
`/srv/appdata/docker`, and `/vault/shared`. Appdata includes application
databases, native identities, and the HAOS recovery image. Keep the PBS
encryption key off-host. The encrypted daily appdata backup **excludes shared
media**; the scoped Proton path is not protection until authenticated and
restore-tested. See [backup coverage and recovery](docs/operations.md#backup-and-recovery)
before changing durable data.

## Bootup / restore

After providing clean PVE 9, importable `vault`, the recovery inputs, declared
hardware, and the unchanged router:

```bash
git clone https://github.com/rafael-alani/dothomelab.git /root/dothomelab
cd /root/dothomelab
./bootstrap.sh --dry-run
./bootstrap.sh
```

Run these on PVE. Read the [rebuild contract](docs/rebuild.md) for prerequisites,
`--appdata-source`, `--restore-latest`, staging-only deployment, and failure
behavior. A destructive clean-host rebuild has not been demonstrated.

| I want to… | Start here |
|---|---|
| Use a service or understand what is available | [User manual](USER_DOC.md) |
| See what is verified and what remains unfinished | [Dated status](docs/status.md) |
| Understand placement, storage, and boundaries | [Architecture](docs/architecture.md) |
| Deploy, diagnose, update, or recover | [Operations](docs/operations.md) |
| Make and validate a change | [Contributing](CONTRIBUTING.md), [development](docs/development.md) |
| Find a service runbook or historical evidence | [Documentation map](docs/README.md) |

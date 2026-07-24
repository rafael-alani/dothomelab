# Rebuild contract

## Outcome

`./bootstrap.sh` is the only in-repository entrypoint required after cloning.
It is designed for a clean PVE 9 installation and is safe to rerun: it never
destroys an existing guest, pool, shared dataset, non-empty appdata tree, or
PBS datastore. Existing guests are inspected and retained; clean rebuilds use
the declarative definitions in `provision/inventory.env`.

The implementation has passed shell/Python validation and a read-only dry-run
against the live node. It has not yet been proven by destroying and rebuilding
the physical host, so this is implemented recovery automation rather than
completed bare-metal restore evidence.

## Required inputs

1. PVE 9 is installed with hostname `afa`, bridge `vmbr0`,
   `192.168.0.250/24`, and gateway `192.168.0.1`.
2. The existing `vault` pool is importable. `vault/shared` contains the large
   shared data. The script imports `vault`; it never creates or reformats a
   pool because physical disk selection cannot be inferred safely.
3. Current appdata is at `/srv/appdata/docker`, is supplied with
   `--appdata-source PATH`, or is restored with `--restore-latest`.
4. The production Docker Compose environment is `/root/.env`. It may use
   normal Compose dotenv syntax, including unquoted values containing spaces.
5. The physical host exposes `/dev/net/tun`, `/dev/dri/card1`, and
   `/dev/dri/renderD128`.
6. The unchanged router continues to use `192.168.0.100` for LAN DNS and
   forwards public TCP 80/443 to `192.168.0.110`. New LXCs use static addresses,
   so DHCP reservations are not recovery dependencies.

VM101 and HAOS VM104 are explicitly excluded.

## Recovery material

The current direct recovery set is:

- this Git repository;
- `/root/.env`;
- `/srv/appdata/docker`, including captured native recovery state;
- `/vault/shared`;
- the existing `vault/pbs_datastore` when PBS history is retained.

After its explicit post-bootstrap authentication and restore test, Proton Drive
adds two rolling off-site generations each for the Obsidian subtree, photos
subtree, and `/root/.env`. Those remote generations are supplemental recovery
material, not a replacement for the canonical inputs above. They do not protect
the rest of `/vault/shared`.

`scripts/capture-native-recovery.sh` was run on 2026-07-24. It added the
current Tailscale identity, Samba private database, Infra account hash, PBS
root account hash, and PBS encryption key under appdata without changing
active service configuration. Snapshot
`host/afa-appdata/2026-07-24T12:38:45Z` contains those files; upload,
server-side verification, and a targeted five-file byte/metadata restore all
succeeded. Bootstrap recaptures native state after future rebuilds. A PBS-only
restore still requires an off-host encryption key because a key inside its own
encrypted archive cannot unlock that archive.

## Commands

Inspect without changing state:

```bash
./bootstrap.sh --dry-run
```

Build from already restored canonical data:

```bash
./bootstrap.sh
```

Copy a recovered appdata directory into a newly created empty dataset:

```bash
./bootstrap.sh --appdata-source /recovery/appdata/docker
```

Restore the newest retained PBS snapshot into an empty appdata dataset:

```bash
./bootstrap.sh \
  --restore-latest \
  --env-file /root/.env
```

For PBS-only restore, set either `PBS_ENCRYPTION_KEY_FILE` or
`PBS_ENCRYPTION_KEY_B64` in `/root/.env`. `PBS_ROOT_PASSWORD`,
`INFRA_ADMIN_PASSWORD`, `SAMBA_PASSWORD`, and `TAILSCALE_AUTH_KEY` are optional
replacement credentials when their captured appdata state is unavailable.

## What bootstrap does

1. Validates the PVE node, bridge, gateway, recovery environment, devices, and
   data ownership without printing secrets.
2. Imports `vault`; creates or reconciles only the child ZFS datasets and
   canonical mount properties.
3. Downloads Debian templates and creates protected, unprivileged CT113.
4. Installs PBS 4 on Debian 13, reconnects the existing datastore, recreates
   the backup identity/ACL, configures prune/GC/full verification, and installs
   the PVE client key/token/fingerprint.
5. Optionally restores appdata from PBS, then restores the PBS root credential.
6. Creates unprivileged Debian 12 CT102/110/112 with static IP/MAC identities,
   bind mounts, TUN, and GPU devices.
7. Installs Docker from Docker's signed repository and installs native
   Cockpit/Samba/Tailscale state with persistent credentials under appdata.
8. Generates a fresh internal Docker API CA, configures mutual TLS, deploys all
   ten Compose projects, reconciles the private Paperless NPM routes and Homarr
   tiles, installs the current WUD runner, and installs the
   disabled PVE-to-Infra Proton backup runner.
9. Recaptures native credentials/state and runs `provision/verify.sh`, including
   storage, all 38 containers, service APIs, database/application counts,
   mounts, Docker mTLS, PBS policy, Tailscale, and deployed Git commits.
10. Activates the daily backup timer only after setup and verification.

Step 10 refers to the daily PBS appdata timer. The Proton timer intentionally
remains disabled because browser login, Syncthing pairing, a first 194 GB photo
transfer, and destructive retention/restore validation cannot be completed by
an unattended clean-host bootstrap.

## Failure and rollback behavior

- Existing pools, guests, datasets, and non-empty data are never force-created
  or overwritten.
- A recovered appdata copy requires an empty target and uses `rsync` without
  deletion. Copy and PBS restore paths reserve free-space headroom first.
- `--restore-latest` alone authorizes replacement of the script-created empty
  appdata dataset. The restore is completed in a temporary ZFS child first.
- Restored PostgreSQL runtime PID markers are preserved outside their data
  directories before clean container startup; active matching databases are
  never altered.
- Repository deployment is staged at `/opt/dothomelab.next`; the prior copy is
  retained as `/opt/dothomelab.previous`.
- Compose never uses `down -v`; Docker image pruning remains disabled.
- Proton never writes to the live Obsidian or photos mounts. It stages large
  archives on `vault`, stages `/root/.env` only in CT110 `/run`, and removes
  an oldest remote generation only after the replacement is fully staged.
- Router, firewall, pools/disks, partitions, VMs, and public exposure are not
  mutated.

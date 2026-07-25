# Syncthing and Proton Drive backups

This Infra project runs Syncthing continuously and the official Proton Drive
CLI as an on-demand Compose profile. A PVE-host systemd service orchestrates a
fortnightly rolling backup because only the host is allowed to read
`/root/.env`.

## Current status

Observed live after the private-GUI rollout on 2026-07-25:

- Syncthing 2.1.2 was healthy and its GUI listened only on loopback.
- The server folder ID was the placeholder `obsidian-vault`, type
  `Receive Only`, with staggered 365-day versioning at `/versions`.
- The folder listed only one device, so the laptop and phone were not paired.
- Pi-hole has an exact local record for `syncthing.rafael.media`. NPM terminates
  HTTPS, forwards to `http://127.0.0.1:8384` with WebSockets, and allows only
  `192.168.0.0/24` and `100.64.0.0/10` before `deny all`.
- Static GUI authentication is configured. The username and strong source
  password are recovery secrets in PVE `/root/.env`; Syncthing stores only its
  bcrypt password hash in appdata.
- Proton was not authenticated, no checksum-verified generation existed, and
  the old guest timer was inactive.
- `/vault/shared/media/photos` was about 194 GB.

The multi-source runner is implemented in Git but has not yet been deployed or
run against Proton. Pairing, Proton authentication, the first restore tests,
and host-timer activation remain explicit user steps.

## Backup contract

Every successful cycle protects three independent sources:

| Dataset | Source | Proton directory | Archive |
|---|---|---|---|
| Obsidian | `/vault/shared/media/obsidian` after Syncthing receives it | `Obsidian` | gzip-compressed tar chunks |
| Photos | `/vault/shared/media/photos` | `Photos` | uncompressed tar chunks |
| Environment | PVE `/root/.env` | `Environment` | gzip-compressed tar chunks |

The three Proton directories live below
`PROTON_BACKUP_REMOTE_ROOT`, which defaults to
`/my-files/Backups/dothomelab`. Each generation is a timestamped directory
containing `MANIFEST`, `SHA256SUMS`, and 4 GiB archive parts.

The backup transaction is deliberately conservative:

1. The PVE wrapper checks whether 14 days have elapsed. A daily persistent
   timer only provides catch-up after downtime; it does not contact Proton when
   the backup is not due.
2. PVE copies `/root/.env` to CT110 `/run` with mode 0600. The temporary copy is
   removed on exit and is never placed in shared data or appdata.
3. Infra pauses Syncthing only while producing the Obsidian archive, then
   resumes it before the large photo stage.
4. All three sources are staged before any remote retention mutation.
   Obsidian/photos stage below `/vault/shared/.proton-backup-work`; environment
   staging remains in CT110 `/run`.
5. Before uploading a new generation, the runner permanently deletes the
   oldest matching generation when two already exist. It trashes and then
   deletes that exact Proton node UID; it never empties unrelated Proton trash.
6. The new generation is uploaded. Every remote part is downloaded one at a
   time and SHA-256 checked before success is recorded.
7. A partially completed cycle keeps its cycle ID and staged shared-data
   archives so the next daily due-check retries it. Datasets already verified
   in that cycle are not repeated.

There are therefore at most two named generations for each dataset. The exact
requested delete-before-upload policy briefly leaves only one good remote
generation while its replacement uploads. A failed upload retains that older
generation and retries the incomplete cycle. Proton notes that storage
reclamation after deletion can take up to three hours, so quota planning should
temporarily allow roughly three photo generations during rollover: about
582 GB at the currently observed 194 GB source size.

Photos are not compressed because JPEG/HEIC/video data gains little from gzip
and compression would add substantial CPU time. The photo tar reads the live
directory. If GNU tar detects a concurrent external write, staging fails and
the cycle retries rather than recording that run as successful. Avoid photo
writes during the initial long backup.

## Durable and temporary state

- Syncthing keys/config: `/srv/appdata/docker/syncthing`
- Syncthing GUI source credentials: PVE `/root/.env`
- Proton session, GPG/password-store, cache, and small success metadata:
  `/srv/appdata/docker/proton-drive`
- Obsidian vault: `/vault/shared/media/obsidian`
- Syncthing versions: `/vault/shared/media/.obsidian-versions`
- Photos: `/vault/shared/media/photos`
- Retryable large staging: `/vault/shared/.proton-backup-work`
- PVE `/root/.env` staging: CT110 `/run/dothomelab-proton-backup` only

The Proton container mounts both live shared sources read-only. Syncthing is the
only container with a read-write Obsidian mount. The dedicated Proton work
directory is read-write, private at mode 0700, and excluded from the photo
source tree.

The Proton `pass` store uses a dedicated no-passphrase GPG key in appdata so an
unattended timer can retrieve the browser-created session. This does not create
a new trust boundary: PVE root already controls CT110 and can read the source
data. The production environment is never committed or logged.

## Deploy the implementation

Run from the repository clone on PVE after checking out the intended committed
revision:

```bash
scripts/sync-guest-repo.sh 110
pct exec 110 -- \
  /opt/dothomelab/hosts/infra/obsidian-sync/prepare.sh
scripts/deploy-compose.sh 110 hosts/infra/obsidian-sync/compose.yaml
pct exec 110 -- \
  docker compose \
    -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
    --profile proton build proton-drive
pct exec 110 -- \
  /opt/dothomelab/hosts/infra/obsidian-sync/install-systemd.sh
backup/proton/install.sh
```

The final command installs the PVE service and daily due-check timer but leaves
the timer disabled on a first install. `./bootstrap.sh` performs the same
deployment on a rebuild.

## Complete Syncthing setup

The repository manages the exact Pi-hole record, private NPM route, wildcard
certificate, WebSockets, LAN/Tailscale allow rules, and GUI authentication.
`scripts/initialize-syncthing-env.py` creates missing first-deployment
credentials in `/root/.env` without printing them. Bootstrap then configures
Syncthing through its loopback REST API and verifies the stored password is a
bcrypt hash. Do not add this hostname to Cloudflare DDNS or publish another
route.

Open `https://syncthing.rafael.media` from the LAN or Tailscale and sign in with
`SYNCTHING_GUI_USERNAME` and `SYNCTHING_GUI_PASSWORD` from PVE `/root/.env`.
The focused live evidence and rollback boundary are in
`docs/syncthing-private-gui-2026-07-25.md`. Then complete pairing:

1. Confirm `Obsidian Vault` is Receive Only, versioning is Staggered with 365
   days, the folder path is `/vault`, and versions path is `/versions`.
2. Before pairing, make a separate laptop copy. Copy the laptop folder's
   existing **Folder ID** (not its label), then preserve it on Infra:

   ```bash
   pct exec 110 -- \
     /opt/dothomelab/hosts/infra/obsidian-sync/configure-syncthing.sh \
     EXISTING_LAPTOP_FOLDER_ID
   ```

   The script only replaces the unpaired, unseeded placeholder. It refuses an
   ID change once the server contains data or is paired.
3. Put the conservative rules from `stignore.example` on laptop and phone too.
   Audit `.obsidian/plugins` for tokens. The policy syncs `.obsidian` and
   vault-local `.trash` but excludes per-device workspace state.
4. Add laptop and phone device IDs to Infra and Infra's ID to both devices.
   Share the existing folder among all three. Keep laptop/phone Send & Receive
   and Infra Receive Only. Seed from the laptop backup, then wait for Syncthing
   to report Up to Date and verify representative file hashes on Infra.

## Authenticate, test, and enable

Authenticate interactively from PVE:

```bash
pct exec 110 -- \
  docker compose \
    -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
    --profile proton run --rm proton-drive auth login
```

Follow the printed URL in a browser. No Proton password is placed on the
command line.

Start the first complete cycle on PVE:

```bash
systemctl start dothomelab-proton-backup.service
journalctl -fu dothomelab-proton-backup.service
```

The first 194 GB photo upload plus byte-for-byte download verification can take
many hours and may be throttled by Proton. Do not enable the timer until the
service exits successfully, all three remote generation directories exist, and
at least one restore/extraction test per dataset has passed.

Inspect local status:

```bash
pct exec 110 -- \
  docker compose \
    -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
    --profile proton run --rm proton-drive backup status
```

After restore testing:

```bash
backup/proton/install.sh --enable
systemctl list-timers dothomelab-proton-backup.timer
```

## Restore without touching live data

The restore command downloads and checks a generation but never extracts it
over a live source.

For Obsidian or photos:

```bash
pct exec 110 -- \
  docker compose \
    -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
    --profile proton run --rm proton-drive \
    backup restore obsidian obsidian-YYYYMMDDTHHMMSSZ

pct exec 110 -- \
  docker compose \
    -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
    --profile proton run --rm proton-drive \
    backup restore photos photos-YYYYMMDDTHHMMSSZ
```

Verified chunks land below
`/vault/shared/.proton-backup-work/restore/<dataset>/<generation>`. Check free
capacity before a photo restore. Extract into a new empty comparison directory:

```bash
# Obsidian
cd /vault/shared/.proton-backup-work/restore/obsidian/obsidian-YYYYMMDDTHHMMSSZ
cat archive.tar.gz.part-* | gzip -dc | tar -xpf - -C /new/empty/restore

# Photos
cd /vault/shared/.proton-backup-work/restore/photos/photos-YYYYMMDDTHHMMSSZ
cat archive.tar.part-* | tar -xpf - -C /new/empty/restore
```

For the environment, create private volatile work and add the mount used by the
backup runner:

```bash
pct exec 110 -- install -d -o 1000 -g 1000 -m 0700 /run/proton-env-restore
pct exec 110 -- \
  docker compose \
    -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
    --profile proton run --rm \
    --volume /run/proton-env-restore:/volatile-work \
    proton-drive \
    backup restore environment environment-YYYYMMDDTHHMMSSZ
```

Copy the verified archive parts back to a private PVE recovery directory,
extract there, validate `root.env`, and only then decide whether to install it
as `/root/.env`. Never extract any generation directly over the live Obsidian,
photos, or environment path.

Run the focused verifier at any time:

```bash
pct exec 110 -- \
  /opt/dothomelab/hosts/infra/obsidian-sync/verify.sh
```

# Syncthing and Proton Drive backups

This Infra project runs Syncthing continuously and the official Proton Drive
CLI as an on-demand Compose profile. A PVE-host systemd service orchestrates a
fortnightly rolling backup because only the host is allowed to read
`/root/.env`.

## Current status

The [October 17–18 check](../../../docs/evidence/2026-10-17-proton-backup-activation.md)
confirmed Mac-to-Infra Obsidian sync and the first successful four-source Proton
cycle at **October 18, 05:53 CEST**. Every cloud part passed download/checksum
verification, all 43,950 shared-photo files passed an independent inventory and
content audit, and the scheduled due-check timer is enabled.

The live folder is now `mdshx-oxig9` (`cloud-sync`), Send & Receive, shared
with the Mac and Symphony VM101. Server versioning is disabled. The July
Receive Only/versioning configuration below is historical setup guidance;
do not apply it over the live folder without reviewing the current workflow.

## Backup contract

Every successful cycle protects four independent sources:

| Dataset | Source | Proton directory | Archive |
|---|---|---|---|
| Obsidian | `/vault/shared/media/obsidian` after Syncthing receives it | `Obsidian` | gzip-compressed tar chunks |
| Photos | `/vault/shared/media/photos` | `Photos` | uncompressed tar chunks |
| Immich originals | `/srv/appdata/docker/immich/upload/{upload,library}` | `Immich` | uncompressed tar chunks |
| Environment | PVE `/root/.env` | `Environment` | gzip-compressed tar chunks |

The four Proton directories live below
`PROTON_BACKUP_REMOTE_ROOT`, which defaults to
`/my-files/Backups/dothomelab`. Each generation is a timestamped directory
containing `MANIFEST`, `SHA256SUMS`, `RESTORE-SAMPLE`, and archive parts of up to
4 GiB. A single `part-00000` is the complete archive when it fits in one part.

The backup transaction is deliberately conservative:

1. The PVE wrapper checks whether 14 days have elapsed. A daily persistent
   timer only provides catch-up after downtime; it does not contact Proton when
   the backup is not due.
2. PVE copies `/root/.env` to CT110 `/run` with mode 0600. The temporary copy is
   removed on exit and is never placed in shared data or appdata.
3. Infra pauses Syncthing only while producing the Obsidian archive, then
   resumes it before the large photo stage.
4. Obsidian is uploaded first, then environment and Immich originals, and
   finally the large shared-photo library. Each source completes independently;
   the whole cycle stays pending until all four succeed. Large staging is under
   `/vault/shared/.proton-backup-work`; environment staging stays in CT110 `/run`.
5. Each archive includes `RESTORE-SAMPLE`: one representative source file and
   its SHA-256. The archive is extracted to a checksum stream and compared with
   that source digest; no extraction writes over a live source. Archive parts,
   the manifest, checksums, and sample metadata are downloaded and compared.
6. Only after the replacement passes verification does retention permanently
   remove the oldest generation, keeping two. It selects exact UIDs discovered
   within the dataset directory. Because the CLI addresses trash by name,
   permanent deletion additionally requires one uniquely named trash item with
   that same UID; ambiguous names fail safely. It never sweeps unrelated trash.
7. An incomplete cycle retains its ID and staged shared-data archives for retry.
   Already verified sources are skipped. If upload finished but success was not
   recorded, the saved remote generation is downloaded and verified first; a
   matching copy does not need another upload. Failure before verification cannot
   delete an older generation. A failed permanent-delete operation may leave
   a scoped node in trash; inspect it separately rather than purging by name.

Rollover temporarily needs three generations. The October 17 source inventory
was about 232 GB of shared photo file bytes and 4.8 GB of Immich originals,
plus notes and the small environment archive. Proton displayed 50.57 GB used
of 1039.00 GB before the first upload. Recheck available space as sources grow.
The two-generation deletion policy needs explicit task-level authorization
before activation, as required by `AGENTS.md`.

Photos are not compressed because JPEG/HEIC/video data gains little from gzip
and compression would add substantial CPU time. Photo and Immich tar archives read their live
directories. If GNU tar detects a concurrent external write, staging fails and
the cycle retries rather than recording that run as successful. Avoid photo
writes during the initial long backup.

## Independently audit shared-photo coverage

The scheduled job checks all archive-part hashes and one source-matched restore
sample. For an additional complete-source check, run the tracked
[audit helper](audit-photo-archive.py) inside CT110 so numeric ownership matches
the archived guest IDs. It reads the source and staged, uncompressed archive;
it does not extract files, upload data, delete backups, or alter success markers.

After placing the desired committed helper in CT110, invoke it from PVE with
an explicit retained generation path (replace the example cycle as needed):

```bash
pct exec 110 -- ionice -c 3 nice -n 19 python3 \
  /opt/dothomelab/hosts/infra/obsidian-sync/audit-photo-archive.py \
  /vault/shared/media/photos \
  /vault/shared/.proton-backup-work/staging/photos/photos-20261017T104109Z \
  --contents
```

Without `--contents`, it compares every non-directory path/type/size and link
target, rejects missing or duplicate entries and part-sequence gaps, and checks
source/part stability. With `--contents`, GNU tar also compares every archived
file's contents. Source changes during the check fail it. It emits safe JSON
counts and exit status; filenames and tar diagnostics are not printed. The
content pass reads the full archive plus source data and can take substantial
I/O time. Live files are not a frozen snapshot. This manual check must pass
alongside complete cloud download/checksum verification to claim both source
coverage and transport integrity. It is not yet a scheduled retention gate.

## Durable and temporary state

- Syncthing keys/config: `/srv/appdata/docker/syncthing`
- Syncthing GUI source credentials: PVE `/root/.env`
- Proton session, GPG/password-store, cache, and small success metadata:
  `/srv/appdata/docker/proton-drive`
- Private per-cycle runner logs (root-only):
  `/srv/appdata/docker/proton-drive/run-logs/<cycle>.log`
- Obsidian vault: `/vault/shared/media/obsidian`
- Syncthing versions: `/vault/shared/media/.obsidian-versions`
- Photos: `/vault/shared/media/photos`
- Retryable large staging: `/vault/shared/.proton-backup-work`
- PVE `/root/.env` staging: CT110 `/run/dothomelab-proton-backup` only

The Proton container mounts both live shared sources read-only at their
canonical paths and Immich upload storage read-only at `/sources/immich`.
Only its `upload/` and `library/` originals are archived; thumbnails, transcodes,
profiles, and database state are outside that archive. Immich database/appdata
recovery still belongs to PBS. Syncthing has the complete `/vault/shared` tree mounted
read-write at the same path so future folders can use their normal server path
without another Compose change. Only paths configured as Syncthing folders are
synced, but the container can read or write any shared path allowed to UID/GID
`1000:1000`; review every added folder carefully. The dedicated Proton work
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

Homarr links to the same private URL on its dashboard, Admin, and default
boards. Its tile ping is intentionally disabled because the Homarr bridge
must not bypass the LAN/Tailscale-only NPM policy to reach Syncthing's
loopback listener. Pulse requires `infra/syncthing` to be online through the
CT110 agent, and WUD enrolls it in `docker.backupgated` with a post-replacement
check against `/rest/noauth/health`.

1. Confirm `Obsidian Vault` is Receive Only, versioning is Staggered with 365
   days, the folder path is `/vault/shared/media/obsidian`, and versions path
   is `/vault/shared/media/.obsidian-versions`. Do not use the old `/vault`
   alias or `~`; `~` expands to Syncthing's `/var/syncthing` appdata.
2. Before pairing, make a separate laptop copy. Copy the laptop folder's
   existing **Folder ID** (not its label), then preserve it on Infra:

   ```bash
   pct exec 110 -- \
     /opt/dothomelab/hosts/infra/obsidian-sync/configure-syncthing.sh \
     EXISTING_LAPTOP_FOLDER_ID
   ```

   The script only replaces the unpaired, unseeded placeholder. It refuses an
   ID change once the server contains data or is paired. When that folder is a
   pending offer from an already configured device, the script accepts and
   shares it with the offering device.
3. Put the conservative rules from `stignore.example` on laptop and phone too.
   Audit `.obsidian/plugins` for tokens. The policy syncs `.obsidian` and
   vault-local `.trash` but excludes per-device workspace state.
4. Add laptop and phone device IDs to Infra and Infra's ID to both devices.
   Share the existing folder among all three. Keep laptop/phone Send & Receive
   and Infra Receive Only. Seed from the laptop backup, then wait for Syncthing
   to report Up to Date and verify representative file hashes on Infra.

For a future Syncthing folder anywhere below shared storage, enter its complete
server path, for example `/vault/shared/media/another-folder`. No container
mount change is required. Use a separate versioning directory for each folder,
preferably below `/vault/shared/media/.syncthing-versions/`, and confirm the
target directory's ownership before enabling synchronization.

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

The October 17 activation uses a transient first-run unit to start this service
and enable the timer only after it succeeds. Check that unit before starting a
second manual job; see the dated evidence linked above. The runner now verifies
one real source-file extraction and every remote archive part for each dataset.

Start the first complete cycle on PVE:

```bash
systemctl start dothomelab-proton-backup.service
journalctl -fu dothomelab-proton-backup.service
```

The host journal reports the cycle and final result. Detailed guest progress is
in `/srv/appdata/docker/proton-drive/run-logs/<cycle>.log` on PVE and CT110;
`pct exec` output is not reliably captured in the host journal. A failed service
is stopped, even if its last uploaded archive remains visible in Proton.

The first roughly 232 GB shared-photo upload plus byte-for-byte download verification can take
many hours and may be throttled by Proton. Do not enable the timer until the
service exits successfully, all four remote generation directories exist, and
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

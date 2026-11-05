# Maintenance automation and remaining recovery gaps — November 5, 2026

This follows the [software maintenance](2026-11-05-maintenance.md). Rafael asked
to remove avoidable manual work, repair n8n/Docker Hub and Aurral/DroppedNeedle,
document undeclared behavior, and leave unused Paperless-GPT without a provider
credential. Work is published on `codex/homelab-maintenance-2026-11-05`.

## Changes and evidence

| Area | Repair | Actual verification |
|---|---|---|
| Routine OS maintenance | Successful scheduled PBS backup now runs same-codename Debian/PVE/PBS updates, then bounded CT114/115 build-cache cleanup, then WUD | Installed policy on PVE and all six LXCs; systemd validation and actual whole-fleet unattended-upgrades/cache dry run passed |
| n8n / Docker Hub | Direct Docker Hub reference bypasses the failing n8n mirror; WUD selects upstream's latest stable release and retains the major-2 restriction | Mirror manifest returned 429, Hub returned 200; identical image redeployed; live n8n and WUD checks passed |
| n8n owner recovery | Initial credentials seed only an unconfigured installation; restored account state stays authoritative | Existing owner identity/password differed from old seeds. Preserved the enabled account; no credential reset. Current owner login remains untested |
| Paperless-GPT | Explicit opt-in flag defaults false; no external API key required while disabled; bootstrap, proxy and Homarr agree | No GPT container; private proxy row disabled; tile removed; optional-service and Infra verifiers passed |
| Aurral | Current path-mapping API, current storage-health POST, automatic library refresh, sanitized errors and writable font cache | Real integration checks passed; full refresh indexed 1,595 music files with no failed files; generated audio passed through Aurral and Navidrome |
| DroppedNeedle | Retired after generated-flow acceptance; idle container removed, appdata/image retained | SQLite integrity passed and five work tables were empty before retirement; no remaining container |
| Contentflow | Existing exact image/source enrolled in Compose and bootstrap; recovery inputs moved into canonical appdata | Both archive hashes verified; actual image archive loaded; exact image/mounts and n8n-to-Contentflow health passed |
| Bootstrap | Disabled GPT no longer blocks environment validation; valid slskd passwords no longer incorrectly require hex encoding | Full live `./bootstrap.sh --dry-run` passed |
| Fleet verification | Counts account for retired services, optional GPT, enrolled Contentflow and native production blog | Final fleet results recorded below |
| qBittorrent 5.3 access settings | Rebuild helper and verifier understand both legacy Preferences keys and the new WebUI section | Live API already had the exact internal subnet and required localhost authentication; old verifier was a false failure. Three compatibility tests cover both formats, scoped edits and unsafe input |
| Proton mount verification | Exact structured Compose mount checks replace adjacent-line YAML matching | The old work-directory check accidentally read the next source mount's read-only flag; source/work access policy and the protected backup runtime are preserved |
| Automatically updated release checks | Mealie API version follows its actual stable image tag; Apps Portainer follows the allowed 2.45 patch channel and requires matching server/agent/API versions; Docker Hub checks accept its equivalent explicit `docker.io/` prefix | Removes stale version/registry-spelling assertions without bypassing health, data or supported-channel checks |

Implementation milestones are `aeb920e`/`8865954` (n8n), `1afae29` (optional GPT),
`51f5e9c` (OS/cache), `158380b` (Aurral/Contentflow), and `5f66d6f` (generated-track
Navidrome acceptance and font cache). Specialist runbooks own operating commands;
this report owns the dated evidence. Existing documentation layout is retained
under [ADR 0001](../decisions/0001-documentation-ownership.md).

## Update boundaries

The [routine maintenance policy](../../hosts/common/README.md) installs no second
update timer and never reboots, removes kernels/packages, prunes images/volumes,
or switches OS major releases. Unattended-upgrades keeps its conffile/dependency
safeguards. Docker engine/Compose upgrades, OS major migrations, WUD itself,
Immich, databases/extensions, Gluetun and the declared bespoke application cohorts
still require coordinated review and rollback. These are intentional manual
boundaries, not missed automatic updates.

The new handoff's actual future scheduled **apply** has not yet occurred. Its
fleet dry run is recorded in PVE `/run/dothomelab-os-update-check.log`; journal
and unattended-upgrades logs are the durable execution evidence after it runs.
Package installation alone does not prove every process loaded patched libraries.
PVE kernel activation still needs an explicitly authorized reboot. WUD does not
rewrite Git: align the recovery image baseline with schema-compatible retained
data before a future restore. No full clean-host rebuild was performed.

n8n remained at stable **2.46.6**, image ID
`sha256:941cefd8db2e3fbaed43fb01336077a807aa54c593858772a1e5c93f345a881c`.
Its immutable image digest is
`sha256:8602f5dfacbe2c931eeafd010de0e68182310e9f309921e780ab69182e92b3ae`.
Upstream's plain numeric **2.47.2** tag was marked prerelease. The adapter uses
[GitHub's latest stable endpoint](https://api.github.com/repos/n8n-io/n8n/releases/latest)
and fails closed on invalid/rate-limited metadata; it does not select a beta to
make the update count disappear. Anonymous registry limits still exist; no paid
Docker Hub account or shared credential was introduced.

## Music acceptance and retirement

The genuine generated flow **Homelab Library Blend** has ID
`b5984425-1d88-486f-aeef-48dbbe3e0c44`. It generated one completed track from the
then-small indexed library, with zero failed/pending/downloading jobs. Its job
`9a355bcf-9966-433b-ac2f-02d37c291f24` returned authenticated HTTP 206 audio.
The library was subsequently fully refreshed; the accepted generation was kept.

Upstream does not publish disabled flows to Navidrome. Saving the real generated
track as **Homelab Library Blend — saved generation** produced static playlist
`d06fa540-4406-44dc-adc1-4f4e665e85b1`. Authenticated Navidrome playlist lookup,
track lookup and raw audio range all passed (206, 4,096 bytes), including after
the font-cache deployment. The source flow remains **unscheduled**; no recurring
download preference was assumed. Physical speaker/device playback was not tested.
The maintained `flow-acceptance.py --verify --navidrome` repeats read-only acceptance;
creation and fixed-playlist publication are separate explicit modes.

DroppedNeedle had no queued downloads, searches, drop imports, held imports or
free-music jobs. Its database passed `PRAGMA integrity_check`, and the local image
and quiet rollback Compose validation passed before stopping it. Its root-private
retained image ID is
`sha256:a0d991c436546f6a5b678abd864ce661744d5ff9e1ef022285d1b53d0c7ede9e`.
Its container receipt is CT112
`/srv/appdata/docker/runtime-cleanup/20261105T214758Z-216392/containers.json`.
The configuration, `cache/library.db`, artwork/cache, plugins and manual imports
remain under `/srv/appdata/docker/droppedneedle`; music and slskd downloads were
not deleted. Its disabled route and absent dashboard tile remain appropriate.
The existing private network is still used by slskd and Aurral.

## Contentflow and recovery

[Contentflow](../../hosts/infra/contentflow/README.md) is the custom Python n8n
companion from the local `/Users/rafael/Repos/n8n` project. It prepares Obsidian
publication bundles/delivery receipts and reviews incoming media. Five workflows
exist: Ready notes and Incoming media active; Archive preview, Apply reviewed
archive and Integration smoke test inactive. External publication is disabled,
and media scans still use example inputs. This is separate from the native blog
publisher; no new social publishing or real-media archive workflow was activated.

The application source repository has no configured Git remote. Its exact
committed source and exported running image now live at CT110
`/srv/appdata/docker/contentflow/recovery/5ac453771bad66662275362217394a59cfb07d7f/`.
`release.json` pins image identity and both SHA-256 hashes. Protected deployment
settings, API token, state and example media are canonical appdata; Obsidian is
a read-only shared-media mount. Bootstrap verifies/loads the image archive and
deploys the declared Compose contract after n8n. The backend has Pulse coverage;
Homarr's existing n8n tile is its user entry point, with no standalone public API.

Actual archive loading and service checks passed on the existing guest. This is
not an isolated empty-host restoration. These newly captured artifacts enter the
**next scheduled PBS backup**, not the earlier protected pre-upgrade snapshot.
Shared media remains outside appdata PBS, and the physical-host/PBS failure-domain
and full-rebuild limitations from the original maintenance report remain.

## Retained artifacts and cleanup

| Artifact | Owner, reason and cleanup condition |
|---|---|
| DroppedNeedle appdata, local image and cleanup receipt above | Homelab maintenance; explicit rollback. Keep until Rafael approves final deletion after replacement acceptance |
| Aurral `data/recovery/pre-generated-flow-20261105T212219Z.db` | Homelab music maintenance; integrity-checked pre-generation database. Retain until the new flow state has an accepted backup and rollback is no longer needed |
| Homarr `db.sqlite.pre-managed-20261105T212528.65265` | Dashboard maintenance; pre-optional-service reconciliation rollback. Retain until accepted backup/cleanup approval |
| NPM `database.sqlite.pre-optional-gpt-20261105T212632Z` | Proxy maintenance; pre-disable rollback. Same retention condition |
| Contentflow `/opt/contentflow` | Contentflow operator; old guest checkout retained after removing active mounts. Remove only after canonical recovery acceptance; current recovery no longer depends on it |
| Contentflow canonical recovery pair | Current required recovery inputs, not disposable diagnostics |
| Dated `/opt/dothomelab.previous*` archives | Infrastructure deployment rollback; retained by normal sync lifecycle, no unapproved deletion |

Current/previous project releases, all durable data and prior maintenance rollback
assets remain. CT114 and CT115 build cache both report **0 B** after this work;
their retained images report 17.53 GB and 10.68 GB respectively. No additional
image/volume deletion was needed. The two unidentified Apps volumes and all
earlier database/HA rollback artifacts retain the conditions in the preceding
[maintenance report](2026-11-05-maintenance.md).

## Final validation and limits

Focused regression checks passed: Aurral 2, optional GPT 4, optional dashboard 1,
WUD compatibility 6, WUD runner 16, qBittorrent format compatibility 3 and n8n
owner recovery 3. Bash syntax uses PVE's supported Bash, not macOS's older system
Bash. Documentation links and diff hygiene pass. No secrets are included in
these files.

After retirement, fresh WUD discovery found **46 watched, 46 active associated
containers, zero retired entries, zero discovery errors and no update candidates**.
The scheduled backup's `OnSuccess` still targets the same WUD service; its installed
OS pre-step and four-hour timeout match Git. Both build caches are empty and
canonical appdata reports approximately 130 GiB free.

All fleet-verifier sections passed against the resulting live inventory, resumed
from each repaired assertion instead of repeating already-passed storage checks.
This was not one uninterrupted invocation. The checks cover storage/media,
HAOS/native recovery artifacts, all six guests, 89 running containers, Staging
applications and native blog, Production dependencies, shared observability,
Docker mTLS, WUD, every declared focused application verifier, and PBS policy
and authenticated listing (31 retained snapshots).

Pulse verifies all six LXCs and Docker coverage on CT102/110/112/114/115.
Homarr has 27 managed apps, 81 tiles and 243 layouts; Aurral and n8n remain
reachable, GPT and DroppedNeedle are absent as intended. Contentflow is a
background service accessed through n8n. Shared Grafana datasource/fleet checks,
five endpoint probes, seven scrapes and five alert-rule evaluations pass;
a fresh sanitized HTTPS 404 probe reached Loki. This does not claim real user
device playback, current n8n owner login, or public media WAN access.

PVE diagnostic logs are `/run/dothomelab-fleet-verify-{follow-up,app-tail,final-tail,remaining,last-services,account-backup}.log`;
earlier logs retain the now-corrected failures. The implementation is published
through `e2e4e27`; final documentation is a descendant on the same maintenance
branch. CT102/110/112/113 are synchronized to that final published revision.
CT114 keeps `db2f54f33797f0cb63879a1ca7f4a4a5527f230b` and CT115
`9c2c15414382082ffb787fb4e912002564cbc902`, with separately installed maintenance
helpers. Their application releases remain unchanged. No task worktree was
created; unrelated existing worktrees and local documentation drafts are retained.

Successful disposable check containers use automatic removal. Transfer copies
and generated verifier-resume scripts under `/run` are removed after their
maintained source and canonical recovery inputs are verified. The dated rollback
artifacts listed above remain intentionally retained.
Monitoring has no external notification receiver or external uptime observer;
container health and internal probes do not establish WAN/client acceptance.

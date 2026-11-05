# Update automation and reproducibility audit — 2026-10-27

Historical pre-maintenance audit. The [November 5 maintenance](2026-11-05-maintenance.md)
supersedes these version/readiness findings and records the completed updates.

The homelab is running, but it is neither fully updated nor currently ready for
an unattended clean rebuild. WUD is successfully updating some eligible
containers after backups; recurring registry failures leave gaps. OS packages
have no unattended installation mechanism. Several deliberately manual services
have newer releases, including security fixes. Bootstrap currently stops at a
missing optional-service credential, and recovery declarations have drifted from
the running inventory and image versions.

## Scope and evidence

Inspected PVE `afa` through SSH and all six managed LXCs through `pct exec`.
VM104's Supervisor API supplied Home Assistant versions and update settings.
VM101 was stopped and remains outside the managed rebuild scope. No packages or
images were installed, containers restarted, backups initiated, or restores
performed. APT indexes were refreshed to avoid reporting stale candidates;
this changed package metadata only. Documentation is the only repository change
from this audit; unrelated local research drafts were preserved.

Methods: filtered Docker inspection and service version endpoints; WUD's
GET-only audit and container cache; systemd units/journals; fresh APT candidates,
holds and unattended-upgrade configuration; official upstream releases; Git
remote refs; bootstrap dry-run; the read-only live media-contract verifier;
PBS backup/verification task results; canonical recovery file presence and
checksums. Environment values, authentication tokens and encryption keys were
not included in output or this report.

| Source | Observed revision/state |
|---|---|
| Canonical local checkout and remote review branch | `codex/blog-production-activation`, `454ac00274ad9acfeda450e7c916596c54d8e210` |
| Remote default branch | `main`, `ee1c217cc56c011eede9cf728acb2b1938d5218d` |
| PVE checkout | Clean, same review branch, `d881ef99de78497a90372bac61f449a62ee1fb55` |
| CT102 archive | `a4f1374011546c7899a6a43ace5c1a93b6100edb` |
| CT110/114/115 archives | `9c2c15414382082ffb787fb4e912002564cbc902` |
| CT112 archive | `f35bedc93b5660b7ae93e0f569be36b55129f310` |
| Native blog staging and production | `71caea006993fd43cc55cfc66ae3181267f38a65` |

All six LXCs and HAOS were running. Docker reported 89 running containers across
CT102/110/112/114/115 (21/19/42/6/1), with no unhealthy status reported. A running
container without a health check is not proof of application workflow health.
Native blog publisher/web services were active; publication activation was
enabled. The staging poller's latest result was successful.

## Automatic updates: working, but incomplete

WUD is backup-gated through the daily appdata backup's `OnSuccess` service. Its
own periodic updating/pruning is disabled; no independent WUD timer was found.
The installed runner matches the repository copy. It watches eligible
containers on CT102, CT110 and CT112. Databases, Immich, Gluetun, WUD itself,
several special integrations and shared observability are deliberately manual.

The October 27 backup completed at **02:17:54 CET**. WUD began immediately,
updated Jellyfin, Lidarr, Shelfarr and Shelfarr-Libation successfully, then ended
at **02:21:38 CET with exit 1** because discovery was incomplete. n8n returned
HTTP 429 and Readarr returned `no manifest found`. October 26 also updated
Homarr, Pulse, qBittorrent and Radarr despite those two discovery failures.
The journal establishes this partial failure; the service's later reset
`Result=success` property alone does not establish that the last update run passed.

The passive audit found **48 watched containers**:

- 38 had neither an error nor an available update in WUD's cached view of their
  configured channel. This is not an independent registry recheck of all 38.
- n8n and DroppedNeedle showed available updates.
- Eight had HTTP 429 discovery errors: Bazarr, Lidarr, NZBGet, Prowlarr,
  qBittorrent, Radarr, Readarr and Sonarr. Their latest status is unknown,
  not proof that all eight are outdated.

| Exception | Finding and reason |
|---|---|
| n8n | Running **2.31.6**, upstream **2.45.4**. It is auto-eligible but recurring nightly 429 errors have prevented discovery/update. This is a genuine automation gap. [Release](https://github.com/n8n-io/n8n/releases/tag/n8n@2.45.4). |
| Readarr | Retired upstream. Its declared `lscr.io/linuxserver/readarr:develop` returned an image index with an empty `manifests` array during direct registry inspection. The running cached image is not a dependable fresh-pull recovery input. Retirement/replacement needs a deliberate data-preserving decision. [Project](https://readarr.com/), [image deprecation](https://github.com/linuxserver/docker-readarr). |
| Apps Portainer server/agent | **2.39.8**, while Infra/Servarr run **2.45.3**. Apps explicitly restricts WUD to `^2\.39\.\d+$`; it will not move to 2.45.3 automatically. This is policy restriction, not a failed update. [Release](https://github.com/portainer/portainer/releases/tag/2.45.3). |
| DroppedNeedle | Update is intentionally skipped; retain the live service unchanged until the generated Aurral flow passes acceptance. It is excluded from clean bootstrap. |

CT114 has its separate review-branch poller. CT115 application-code releases
remain manual. Native blog content publication is automatic. These mechanisms
do not maintain PVE/Debian packages or all application dependencies.

## OS and engine maintenance backlog

No `unattended-upgrades` package, enabled periodic installation configuration,
or package holds were found on PVE or the six LXCs. APT timer presence alone
does not mean updates are installed. Some package indexes were very stale
before this audit, so initial cached counts were misleading.

| Machine | Upgradable packages | Candidates from security origins | Notable installed → candidate |
|---|---:|---:|---|
| PVE | 201 | 57 | PVE manager 9.1.2 → 9.2.24; kernel/ZFS packages also pending |
| CT102 Servarr | 110 | 53 | Docker 29.0.1 → 29.9.2; Compose 2.40.3 → 5.6.1 |
| CT110 Infra | 97 | 40 | Docker 27.4.1 → 29.9.2; Compose 2.32.1 → 5.6.1; Tailscale 1.98.8 → 1.104.2 |
| CT112 Apps | 99 | 36 | Docker 27.5.0 → 29.9.2; Compose 2.32.3 → 5.6.1 |
| CT113 PBS | 88 | 31 | PBS 4.2.3 → 4.2.8 |
| CT114 Staging | 87 | 29 | Docker 29.8.2 → 29.9.2; Compose 5.6.0 → 5.6.1 |
| CT115 Production | 95 | 34 | Base Debian pending; Docker 29.9.2 and Compose 5.6.1 already current |
| **Total** | **777** | **280** | Package instances across machines, not unique packages or vulnerabilities |

PBS has an enabled enterprise source returning **HTTP 401 Unauthorized**.
Its non-subscription source also exists and supplied candidates, but the refresh
exited 100. Resolve the intended subscription/source configuration before PBS
maintenance. No source was changed here. No unattended-upgrade policy should
blindly introduce Docker major upgrades or reboot PVE; schedule maintenance
with service checks and the existing authorization/rollback boundaries.

## Manual application maintenance

These are observed newer releases, not blanket approval of a direct upgrade.
Keep compatible cohorts together, review intervening changes and perform the
required backup/restore work for durable-data risk.

| Service | Installed | Available/review target | Why manual / next work |
|---|---|---|---|
| Immich server + ML | 3.0.3 | [3.3.5](https://github.com/immich-app/immich/releases/tag/v3.3.5) | Review intermediate releases, app/database compatibility and rollback. |
| Immich PostgreSQL | 14.19, VectorChord 0.4.3 | PG14 current minor 14.24; supported-major migration needed | PG14 support ends November 12, 2026. Use a compatible Immich image and tested logical migration. |
| Home Assistant Core | 2026.7.4 | 2026.10.4 | Live Supervisor reports update available. |
| Home Assistant OS | 18.1 | 18.4 | Live Supervisor reports update available; refresh recovery inputs around approved maintenance. |
| HA apps | Mosquitto 7.1.0; Spotify 0.18.0; File editor 6.0.0; Music Assistant 2.9.9 | 7.1.3; 0.19.0; 6.3.0; 2.10.8 respectively | All four have automatic updates disabled. |
| Umami | 3.4.0 | [3.4.1](https://github.com/umami-software/umami/releases/tag/v3.4.1) | Manual pinned observability stack; upstream explicitly recommends this security hotfix to self-hosters. |
| Prometheus | 3.13.1 | [3.15.1](https://github.com/prometheus/prometheus/releases/tag/v3.15.1) | Manual; new release includes security fixes. |
| Grafana / Loki / Alloy | 13.2.4 / 3.7.3 / 1.21.1 | [13.3.0](https://github.com/grafana/grafana/releases/tag/v13.3.0) / [3.7.9](https://github.com/grafana/loki/releases/tag/v3.7.9) / [1.21.2](https://github.com/grafana/alloy/releases/tag/v1.21.2) | Review shared monitoring stack and all three Alloy collectors. |
| WUD | 8.3.0 | [9.6.0](https://github.com/getwud/wud/releases/tag/9.6.0) | Major update; validate the local compatibility layer and backup-gated runner. |
| Gluetun | June 29 rolling build, commit `93cc5a4` | [Stable 3.41.3](https://github.com/passteque/gluetun/releases/tag/v3.41.3); newer rolling digest also exists | Review VPN/provider changes and dependent downloaders as a cohort. |
| Cleanuparr | 2.10.0 | [2.10.12](https://github.com/Cleanuparr/Cleanuparr/releases/tag/v2.10.12) | Download-state integration; manually controlled. |
| Listenarr | 1.2.2-canary | [1.5.0-canary](https://github.com/Listenarrs/Listenarr/releases/tag/v1.5.0-canary) | Prerelease channel; integration acceptance required. |
| Aurral | 2.0.0-test.7 | [2.12.0](https://github.com/lklynet/aurral/releases) | Request/music integration and existing acceptance conditions. |
| Beets | 2.12.0 | [2.14.1](https://github.com/beetbox/beets/releases/tag/v2.14.1) | Canonical music writer; preserve metadata/writer contract. |
| Bar Assistant | 5.15.3 | [6.9.0](https://github.com/karlomikus/bar-assistant/releases/tag/v6.9.0); v5 image also changed | Review server, Salt Rim, Meilisearch and Redis compatibility together; no unreviewed major jump. |
| Sortarr | Pinned May 3 image | Newer `latest` digest | Exact target application version not established; review before replacing pin. |
| Python helper images | June 16 `python:3.13-alpine` digest | Newer same-tag digest | Recreate and check the affected helpers deliberately. |

The earlier Immich v1-to-v3 / VectorChord migration is **already complete**:
the live app reports 3.0.3 and uses the Immich PostgreSQL image with VectorChord.
Do not repeat the old migration merely because historical migration scripts
remain. The pending work is a reviewed current app upgrade and PostgreSQL
lifecycle plan. [Immich upgrade guidance](https://docs.immich.app/install/upgrading/)
does not support downgrading after an upgrade; a rollback must restore compatible
data. [PostgreSQL's support policy](https://www.postgresql.org/support/versioning/)
confirms the PG14 deadline and current minors.

Application-local database/cache patch backlog:

- PinePods, BookOrbit, Paperless and Jellystat PostgreSQL **18.4 → 18.6**;
  SnapOtter **17.10 → 17.11**. Umami PostgreSQL is already 17.11.
- Grimmory MariaDB **11.4.8 → 11.4.13** within its LTS line.
  [MariaDB 11.4 releases](https://mariadb.com/docs/release-notes/community-server/11.4/what-is-mariadb-114).
- PinePods Valkey **8.1.9 → 8.1.11**; Paperless **9.1.1 → 9.1.3**;
  Immich **9.1.0 → 9.1.3**. These include recent security fixes; there is no
  need to change PinePods' major version merely to receive them.
  [Valkey releases](https://github.com/valkey-io/valkey/releases).
- SnapOtter/Bar Assistant Redis image is **8.8.1**, versus
  [8.10.3](https://github.com/redis/redis/releases/tag/8.10.3).

HA Supervisor 2026.10.4 is current with auto-update enabled and reports healthy
and supported. Govee is current with auto-update enabled. Blackbox 0.29.1 is
current. Salt Rim's deployed v4 digest matches the current v4 image, and
Meilisearch 1.15.2 matches its pinned v1.15 line; neither observation establishes
that the whole cocktail stack should stay on those major/minor lines forever.
HA custom integrations/HACS and application source dependency audits were not
exhaustively assessed.

## Reproducibility and recovery

### Verified recovery foundations

- The scheduled encrypted PBS snapshot
  `host/afa-appdata/2026-10-27T01:04:22Z` completed successfully: approximately
  303.247 GiB logical appdata plus the environment archive. All eight declared
  database hooks ran; the job froze the five Docker guests for its consistent
  appdata snapshot. PBS server verification finished **05:37:33 CET**, successfully.
  Installed backup helper content matches the repository. Verification is not
  a restore rehearsal.
- The operator-side PBS encryption key exists and its checksum matches PVE's
  current key; only the comparison result was exposed. Native recovery inputs
  are present in canonical appdata.
- The canonical HAOS VMA and checksum sidecar exist; rechecking its SHA-256
  passed. This proves archive integrity against the saved checksum, not bootability.
- ZFS pools reported healthy. The live media-contract verifier passed without
  write probes, including canonical directories, mounts, ownership and free-space
  floors. Shared media remains separate from appdata.
- All four current Docker staging applications (Meta Egg, Film-introspect,
  Stillroom and Form & Field) have source bundles containing their recorded
  release commits. No fresh unpack/build/restore test was performed.
- The scoped Proton cycle completed October 18. The separate
  [October 27 reverification and protected-runner evidence](2026-10-17-proton-backup-activation.md#reverification-october-27-2026)
  records cloud checks. This audit checked the live timer/journal, not another
  cloud download. The next full cycle is expected November 2; successful
  intervening daily checks are intentionally not-due results.

### Concrete blockers and gaps

| Priority | Gap | Consequence / needed correction |
|---|---|---|
| High | `./bootstrap.sh --dry-run` stops because `PAPERLESS_GPT_OPENAI_API_KEY` is missing | Paperless-GPT is not running, but environment validation and bootstrap enrollment require it unconditionally. Make enrollment conditional or deliberately configure the real service. Never use a dummy key. Later dry-run stages remain unproven. |
| High | Default clone selects older `main` | The README clone command resolves to `ee1c217`, while current reviewed work is retained remotely at `454ac00` on the review branch. Establish an explicit accepted recovery revision/clone path without silently promoting main. |
| High | Git image declarations differ from runtime | Mealie declares 3.21.0 but runs 3.29.0; Apps Portainer declares 2.39.5 but runs 2.39.8. Rebuild can select older binaries against newer state. Immich declares floating `release` despite its manual policy, so a fresh pull can instead upgrade it unexpectedly. Capture accepted recovery versions/digests and align verifiers; WUD does not write successful updates back to Git. |
| High | Readarr fresh image index is empty | A clean guest cannot rely on its locally cached runtime image. Decide retirement/replacement or preserve a verified retrievable image under an explicit recovery contract. |
| High | Contentflow is undeclared | Healthy `contentflow-contentflow-1` uses `contentflow:local` and `/opt/contentflow/compose.yaml` in CT110's replaceable guest root (placement corrected against the November 5 live check). Durable state is mounted under canonical appdata, but source/build/Compose and fixture media are outside homelab recovery declarations. Retained state alone cannot rebuild this runtime. |
| High | HA recovery point is old | Canonical full VM image is July 25; newest exported native backup is July 26. Daily PBS protects those same old files, not current HA VM state. Refresh canonical inputs and establish ongoing exports; inspect any newer guest-local backups before claiming a current recoverable configuration. |
| Medium | No demonstrated full clean rebuild | Neither clean PVE → six LXCs + restored HAOS nor recovery of the new native blog path was exercised here. Current health and a checksum are insufficient acceptance. |
| Medium | Limited local restore headroom | Appdata uses about 370 GiB with 74.4 GiB free, above the 64 GiB floor but insufficient for a second complete appdata copy on that pool. Arrange suitable isolated capacity for a full restore rehearsal. |
| Coverage boundary | Shared media and same-host PBS | `/vault/shared` uses about 12.1 TiB and is excluded from daily appdata PBS. PBS resides on the same physical host. Scoped Proton coverage is not a full offsite copy of the entire lab/media collection. |

Different guest archive commits are evidence of incremental deployment, not
proof that every older archive is broken. Installed active helpers were checked
where relevant, and the current blog app revision agrees between staging and
production. A service-by-service recovery manifest would make this relationship
explicit instead of inferring it from guest archive versions.

The bootstrap dry-run's temporary environment file was removed. No successful
test containers, migrations, build caches or new rollback artifacts were created.
Existing retained artifacts and worktrees were not removed by this audit.

## Recommended order

1. Address security maintenance for Umami, Prometheus and Valkey, and plan the
   PVE/LXC OS backlog in bounded maintenance windows. Resolve PBS's unauthorized
   package source first for that guest. Keep these deliberate changes, not one
   fleet-wide blind upgrade.
2. Repair WUD discovery/retry/reporting and the n8n missed-update case; handle
   Readarr's retirement separately. Existing shared monitoring has no configured
   notification receiver, so dashboard visibility alone does not deliver alerts.
3. Remove the bootstrap credential blocker and establish the exact recovery
   revision/image manifest. Declare Contentflow's recovery contract and refresh
   HA backups before calling the entire setup reproducible.
4. Upgrade Immich and plan its PostgreSQL major migration before PG14 EOL;
   review HA and the remaining manual cohorts. A major database change requires
   logical dumps, isolated restoration and verified rollback under repository policy.
5. Run an isolated recovery rehearsal with sufficient capacity and record what
   actually restores, including native identities, project source bundles,
   integrations and HA boot. Do not substitute this audit for that evidence.

## Checks and limits

Repository docs/link checking and the repository-only media-contract check passed.
The live read-only media-contract check passed. The bootstrap dry-run failed at
the credential validation described above. No full fleet verifier was invoked
because some verifiers create probes. No destructive clean rebuild, new backup,
isolated restore, complete user-workflow acceptance, or exhaustive vulnerability
scan was performed. Release availability is as observed October 27 and can change.

This report and its status/index links are local documentation drafts. No
production deployment, branch promotion or maintenance release occurred.

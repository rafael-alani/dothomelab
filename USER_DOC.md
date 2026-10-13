# Homelab user manual

This manual describes the services and workflows declared by this checkout of
dothomelab. It is for Rafael, invited service users, and the operator. Each app
has its own account and permissions; the dashboard is a starting point, not a
shared login. The [status page](docs/status.md) records what was actually
checked, at which revision, and what remains unfinished.

The first documentation review is dated **2026-10-12**, against code baseline
`c2661dd`. Existing service runbooks and acceptance records underpin these
workflows; this review did not repeat authenticated journeys or device tests.
Rolling applications can change their interfaces independently of Git. Where
exact labels are documented below they come from the linked runbook; otherwise
the steps describe the task without assuming a particular button label.

## Getting started and access

1. Connect to the home LAN, or the configured Tailscale path for private HTTPS
   services. A public DNS result does not grant access to a private route.
2. Open [Homarr](https://rafael.media) and select a service, or use its direct
   address below. A dashboard tile can exist before a service is configured.
3. Sign in with that application's account. Ask the operator for access;
   production secrets are not distributed through this manual.
4. Complete any first-login password/MFA setup offered by the app. SnapOtter
   and Stirling-PDF have documented first-login requirements.
5. Try a small representative task and verify the result. If a page loads but
   your task fails, use [troubleshooting](#troubleshooting).

Private managed routes allow the home LAN and Tailscale address range. Several
older routes have different policies; do not assume every `rafael.media` host
is private. `stream.rafael.ink` and `join-stream.rafael.ink` are the documented
public Jellyfin/invitation origins. The older Home Assistant route is also
public. The [dated route inspection](docs/evidence/2026-10-12-documentation-baseline.md)
records the limits of the access review.

## Concepts and roles

| Term or role | Meaning here |
|---|---|
| Service user | Can use only the app/library permissions granted to their account |
| Application administrator | Manages that app's users, settings, and integrations; not automatically a host operator |
| Homelab operator | Has PVE/root access and is responsible for deployment, data protection, and recovery |
| Pulse user | Has Docker lifecycle control through enabled guest agents; treat this login as administrative |
| Canonical library | The permanent media tree, organized by its assigned acquisition service |
| Reader | Consumes canonical files without reorganizing them, such as BookOrbit or Navidrome |
| Appdata | Databases, configuration, progress, and service state under `/srv/appdata/docker` |
| Shared data | Large files under `/vault/shared`; excluded from the appdata PBS backup |

Use each service for its assigned job. Shelfarr organizes ebooks, Listenarr
organizes audiobooks, Lidarr organizes music, and PinePods owns active podcasts.
Grimmory and Audiobookshelf have narrowly controlled metadata-writing roles.
Storyteller and Aurral flows use separate derived libraries. Moving files by
hand or through a reader can break those relationships.

## Capability index

This index covers the repo's user and administrator entry points. Supporting
databases, proxies, workers, and retained services are explained afterward.
Availability and acceptance are tracked separately in [status](docs/status.md).

| Goal | Service / entry point | Who and important limits | Workflow |
|---|---|---|---|
| Find services | [Homarr](https://rafael.media) | Dashboard account; app logins remain separate | [Get started](#getting-started-and-access) |
| Request films or series | [Seerr](https://jellyseerr.rafael.media) | Granted request permissions; fulfillment depends on sources | [Watch and request](#watch-and-request-films-or-series) |
| Play films, series, or music | [Jellyfin](https://stream.rafael.ink) | Jellyfin account/library permissions | [Watch and request](#watch-and-request-films-or-series) |
| Invite a Jellyfin user | [Wizarr](https://wizarr.rafael.media) | Administrator; use public invite origin for remote guests | [Invite](#invite-someone-to-jellyfin) |
| Inspect movie/TV downloads and subtitles | [Radarr](https://radarr.rafael.media), [Sonarr](https://sonarr.rafael.media), [Bazarr](https://bazarr.rafael.media) | Operator; avoid bypassing the owner of an import | [Acquisition](#inspect-acquisition-and-playback-history) |
| Inspect sources and transfers | [Prowlarr](https://prowlarr.rafael.media), [qBittorrent](https://qbittorrent.rafael.media), NZBGet via the dashboard or Servarr port 6789 | Operator; VPN/cohort and stalled-removal rules apply | [Acquisition](#inspect-acquisition-and-playback-history) |
| Inspect stalled imports or storage analytics | [Cleanuparr](https://cleanuparr.rafael.media), [Sortarr](https://sortarr.rafael.media) | Operator; Cleanuparr controls removals, Sortarr is read-only | [Acquisition](#inspect-acquisition-and-playback-history) |
| Review playback history | [Jellystat](https://jellystat.rafael.media) | Authorized account; history depends on its Jellyfin integration | [Acquisition](#inspect-acquisition-and-playback-history) |
| Discover/request music | [Aurral](https://aurral.rafael.media) | Aurral account; generated flows still need acceptance | [Music](#request-and-listen-to-music) |
| Play the music library | [Navidrome](https://navidrome.rafael.media), Jellyfin | Service account; desktop/mobile playback has separate acceptance | [Music](#request-and-listen-to-music) |
| Inspect music acquisition | [Lidarr](https://lidarr.rafael.media), [slskd](https://slskd.rafael.media) | Operator; one shared Soulseek identity and canonical organizer | [Music](#request-and-listen-to-music) |
| Acquire ebooks | [Shelfarr](https://shelfarr.rafael.media) | Authorized account; direct providers/uploads/Libation are restricted | [Books](#acquire-and-read-books) |
| Acquire audiobooks | [Listenarr](https://listenarr.rafael.media) | Authenticated account; manually updated canary deployment | [Books](#acquire-and-read-books) |
| Read ebooks/PDFs/comics/manga | [BookOrbit](https://bookorbit.rafael.media), [Kavita](https://kavita.rafael.media) | App account/library permission; readers see files read-only | [Books](#acquire-and-read-books) |
| Listen to audiobooks | [Audiobookshelf](https://audiobookshelf.rafael.media) | Library account; active podcasts are in PinePods | [Books](#acquire-and-read-books) |
| Correct canonical book metadata | [Grimmory](https://grimmory.rafael.media), Audiobookshelf | Operator-reviewed publication only | [Metadata](#review-book-metadata) |
| Create an aligned readaloud | [Storyteller](https://storyteller.rafael.media) | Account and exact ebook/audio pair; explicit processing choice | [Readalouds](#create-an-aligned-readaloud) |
| Subscribe to and sync podcasts | [PinePods](https://pinepods.rafael.media) | PinePods account; GPodder for progress sync | [Podcasts](#subscribe-to-and-sync-podcasts) |
| Use desktop music or a portable player | SMB, Kew, Feishin, HifiMule/EchoList | Local client/card; server health is insufficient | [Desktop and ECHO](#use-desktop-media-and-snowsky-echo) |
| Store/browse photos | [Immich](https://immich.rafael.media) | Immich account; original photo files need separate protection | [Photos](#use-photos-and-a-slideshow) |
| Show a photo slideshow | [ImmichFrame](https://immichframe.rafael.media) | Private route; scoped Immich read key | [Photos](#use-photos-and-a-slideshow) |
| Archive and find documents | [Paperless-ngx](https://paperless.rafael.media) | Paperless account/permissions | [Documents](#archive-and-process-documents) |
| Assist document metadata with AI | [Paperless-GPT](https://paperless-gpt.rafael.media) | Pending external key; private, no native auth, sends content to OpenAI | [Documents](#archive-and-process-documents) |
| Process PDF files | [Stirling-PDF](https://pdf.rafael.media) | Authenticated user; complete first-login setup | [Documents](#archive-and-process-documents) |
| Process other files/media | [SnapOtter](https://snapotter.rafael.media) | Authenticated user; 500 MiB configured upload limit | [Documents](#archive-and-process-documents) |
| Sync research attachments | [Zotero WebDAV](https://zotero.rafael.media/zotero/) | Personal Zotero library only; separate WebDAV credentials | [Zotero](#sync-zotero-attachments) |
| Manage recipes and cocktails | [Mealie](https://mealie.rafael.media), [Bar Assistant / Salt Rim](https://bar.rafael.media) | Separate app accounts; Bar API/search are supporting routes | [Kitchen](#manage-recipes-and-cocktails) |
| Download a media URL | [yt-dlp Web UI](https://yt-dlp.rafael.media) | Authenticated user; output is outside appdata backup | [Downloads](#download-media-from-a-url) |
| Use home automation | [Home Assistant](https://ha.rafael.media) | HA account; device/integration permissions apply | [Home](#use-home-assistant) |
| Receive an Obsidian copy / access shared files | [Syncthing](https://syncthing.rafael.media), SMB, [Cockpit](https://vault.rafael.media) | Device pairing or operator credentials; receive-only vault | [Files](#sync-obsidian-and-access-shared-files) |
| Build private automation | [n8n](https://n8n.rafael.media) | n8n account; public webhook ingress disabled | [Automation](#build-private-automation) |
| Inspect and operate the fleet | [Pulse](https://pulse.rafael.media), Portainer, [PVE](https://proxmox.rafael.media), [PBS](https://backup.rafael.media) | Operator; changes obey the operations contract | [Administration](#administer-the-homelab) |
| Inspect metrics or query stored logs | [Prometheus](https://prometheus.rafael.media), [Loki](https://loki.rafael.media/ready) | Private operator tools; Loki has no declared log shipper | [Administration](#administer-the-homelab) |
| Test a development branch | [Film-introspect staging](https://film-introspect.staging.rafael.media) | Private demo; scoped staging credentials | [Staging](#test-a-staging-branch) |

## Watch and request films or series

**Goal:** get an available title into your Jellyfin library and play it.
You need the relevant Jellyfin library and Seerr request permissions.

1. Search Jellyfin first; if the title is available, open it and play it.
2. If missing, open Seerr, choose the exact film or series, and submit the
   request allowed by your account. Check the request's status.
3. Acquisition runs through Radarr/Sonarr and the configured download clients.
   Wait for import and library discovery, then try playback in Jellyfin.

**Success:** the intended title is in the correct library and plays on your
actual client. A completed download is an intermediate step. Requests can wait
for approval, sources, quality matches, or import. Ask the operator to inspect
the owning queue; do not manually move/delete torrent files to force progress.

## Invite someone to Jellyfin

As a Wizarr administrator, configure the intended Jellyfin server and invitation
permissions, then create the invitation from
[the public invitation origin](https://join-stream.rafael.ink). Give the
resulting invitation to the intended person through your normal channel.
The recipient redeems it and signs into Jellyfin at
[stream.rafael.ink](https://stream.rafael.ink).

**Success:** a real recipient can redeem, sign in, and access only the intended
libraries. The private `wizarr.rafael.media` origin is for LAN/Tailscale use;
do not give a remote guest a private-origin link. First-admin setup and real
redemption remain acceptance items until exercised. See [Wizarr](hosts/apps/wizarr/README.md).

## Inspect acquisition and playback history

Use Radarr for films, Sonarr for series, Lidarr for music, Shelfarr for ebooks,
and Listenarr for audiobooks. Inspect the owning service's queue/import error
before looking at qBittorrent or NZBGet. Prowlarr manages search sources; Bazarr
handles the configured subtitle workflow. Sortarr provides read-only storage
analytics; Jellystat provides playback statistics.

Cleanuparr removes managed stalled torrents through the owning Arr with
blocklisting and replacement searches. Do not directly remove those torrents
in qBittorrent. It deliberately tolerates longer private-tracker stalls and
fails closed on connectivity errors. Cross-seed is a strict background
BitTorrent helper under the Gluetun-only policy; neither tool is a user import
path. See [Cleanuparr](hosts/servarr/cleanuparr/README.md),
[Sortarr](hosts/servarr/sortarr/README.md), and [cross-seed](hosts/servarr/cross-seed/README.md).

## Request and listen to music

1. Sign into Aurral, identify the desired artist/album, and request it. Check
   its durable Activity history rather than submitting the same request again.
2. Aurral asks Lidarr to search immediately. If still unresolved after the
   configured grace period, request-scoped Soularr may use slskd and hand the
   result to Lidarr. Retries are deliberately limited.
3. Once imported and scanned, find the album in Navidrome or Jellyfin and play
   a track. Verify artist, album, track order, and playback on your device.

Lidarr organizes permanent music. Aurral only writes its separate flow library
and scoped download state. Discovery can use the configured Last.fm history,
but a generated flow still needs end-to-end acceptance. Existing DroppedNeedle
is retained for that transition; do not start a second organizer or change its
live restart policy as ordinary use. Read [Aurral](hosts/apps/aurral/README.md)
and [Soularr](hosts/servarr/soularr/README.md) for the acquisition/recovery rules.

## Acquire and read books

**Prerequisite:** access to the acquisition service and intended reader.

1. Request an ebook through Shelfarr or an audiobook through Listenarr. Select
   the intended work, language, edition, and format before requesting.
2. Let the owning service import from its completed download. Shelfarr copies
   ebooks into their canonical author/title folders; Listenarr publishes
   audiobooks while preserving seeding with hardlink/copy behavior.
3. Open ebooks/PDFs/comics/manga in BookOrbit or Kavita. Open audiobooks in
   Audiobookshelf. Allow their scan/watch schedule to discover the import;
   Audiobookshelf has a daily fallback scan and its watcher is disabled.
4. Open a representative chapter/page, check cover/title, and confirm progress
   resumes under the same account.

Shelfarr's direct providers, non-admin upload, and Audible/Libation integration
are disabled. Its retained Audiobookshelf connection reads inventory; it is
not a second audiobook organizer. Readarr remains a retained legacy service,
not the current book acquisition entry point. Do not use a reader to move or
rename canonical files. Physical KOReader/Kobo setup and current BookOrbit
administrator credential alignment need separate acceptance; see
[Shelfarr](hosts/servarr/shelfarr/README.md), [Listenarr](hosts/servarr/listenarr/README.md),
[BookOrbit](hosts/apps/bookorbit/README.md), and [Kavita](hosts/apps/kavita/README.md).

## Review book metadata

This is an operator-assisted workflow because publication changes shared files
outside the appdata backup. Establish the focused rollback described in the
service runbook before publishing.

For an EPUB, inspect a native proposal in Grimmory and compare identifier,
title, author, language, edition, and format with the intended work. Accept only
an unambiguous match. Missing/conflicting identity stays in review. Grimmory's
completeness score is not confidence that it found the right book.

For an audiobook, review the recording metadata in Audiobookshelf. Its native
embed tool must use stream copy, keep the existing chapters and its backup
copy, and pass codec/duration/chapter verification. **Never publish audiobook
metadata through Grimmory**: its representative M4B pilot destroyed streams
and chapters and was rolled back. Automatic matching/merging/moving remains
disabled. See [Grimmory](hosts/apps/grimmory/README.md) and
[Audiobookshelf](hosts/apps/audiobookshelf/README.md) for exact checks.

## Create an aligned readaloud

The canonical EPUB and audio must have the identical two-component
`author/title` relative key. Storyteller's reconciler verifies and stages copies
into its separate library; it does not guess a match or modify either source.

1. Open Storyteller's **Books** view after the pair is imported.
2. Choose **Missing readaloud**, select the desired pair, then **Actions →
   Begin processing → Continue where left off**.
3. Let the single-worker queue finish. Processing can be lengthy. Open the
   result and test text/audio alignment, chapter playback, and resume.

Ambiguous pairs, changed sources, or insufficient space are held for review.
Ask the operator to inspect the reconciler report; do not edit its database or
rename originals to force the queue. Accepted readalouds and source copies are
outside appdata PBS and are not disposable cache. See
[Storyteller](hosts/apps/storyteller/README.md).

## Subscribe to and sync podcasts

1. Sign into PinePods and add the feed or import an OPML subscription list.
2. Download/play an episode and confirm progress is saved in the web app.
3. For a compatible mobile client, enable **Settings → Podcast Sync Settings**
   in PinePods, then use the same HTTPS origin and your PinePods credentials
   with the client's GPodder integration.
4. Play/pause on each device and verify episode actions reach the other client.

OPML transfers subscriptions, not progress. Do not migrate progress by editing
databases. Audiobookshelf's former podcast library and files are retained but
inactive. Episode downloads are outside appdata PBS. Server-side GPodder
acceptance exists; a physical mobile client still needs its own test. See
[PinePods](hosts/apps/pinepods/README.md).

## Use desktop media and SNOWSKY ECHO

On the home LAN, connect Finder to `smb://192.168.0.110/Media` with the Samba
account. The read-only share supplies `/Volumes/Media/music` for Kew. The
[macOS helper](clients/macos-media/README.md) reconnects the mount; it provides
no offline cache. With a Tailscale exit node, follow its **Allow Local Network
Access** guidance if native SMB routing fails. Feishin can instead use the
Navidrome server and your Navidrome account; validate actual playback locally.

For SNOWSKY ECHO, follow the [desktop/card runbook](clients/snowsky-echo/README.md):
sync the pinned HifiMule profile into `Music/Managed`, then use EchoList's
separate `Music/Playlists` tree. Optionally preview and run the PinePods episode
compiler into `Podcasts/PinePods`. Check summaries/free space, eject safely,
refresh the device library, and test playback. These are local card operations;
never select canonical server music as an output destination. Physical-device
acceptance remains distinct from installer/compiler tests.

## Use photos and a slideshow

Use your Immich account to upload or browse photos and albums. Verify an
uploaded original opens before relying on mobile auto-upload. Immich's database
and configuration recovery does not establish protection of shared originals.

Open ImmichFrame on a LAN/Tailscale-connected display to show the configured
Immich collection. Its scoped read key and saved settings are managed by the
operator. An empty frame can mean key permissions, collection settings, or
connectivity; do not reset its database as a configuration fix. Keep the frame
private. See [ImmichFrame](hosts/apps/immichframe/README.md) and its
[repair evidence](docs/immichframe-repair-2026-09-17.md).

## Archive and process documents

In Paperless-ngx, sign in, upload a small representative document, wait for
processing, correct its title/tags/metadata, and verify search and original
download. Paperless stores originals with its appdata so documents and metadata
share the recovery input. Check processing errors before uploading duplicates.

Paperless-GPT is a separately declared assistant awaiting its external API key.
It sends selected document content to OpenAI and has no native authentication;
the private network boundary is essential. Automatic PDF upload/replacement is
disabled. Do not assume its dashboard tile means it is available. See
[Paperless-ngx](hosts/apps/paperless-ngx/README.md) and
[Paperless-GPT](hosts/apps/paperless-gpt/README.md).

For a one-off PDF task, sign into Stirling-PDF, complete first-login setup,
select the required tool, upload a copy, run it, download the result, and open
it to verify the intended pages/content. Retain the source until satisfied.

SnapOtter similarly provides file-processing tools for images, video, audio,
PDFs, and files. Sign in, complete the password change, select the relevant
tool, supply a copy, and inspect the downloaded output. The configured upload
limit is 500 MiB; installed packs and the running version determine available
tools. No individual conversion was retested for this manual. Use its
[official tool reference](https://docs.snapotter.com/) for tool-specific
options, and the [local runbook](hosts/apps/snapotter/README.md) for deployment
constraints.

## Sync Zotero attachments

Zotero account sync handles bibliographic metadata. This WebDAV service handles
**personal-library attachments only**; group-library attachments cannot use it.

1. In Zotero open **Settings → Sync → File Syncing**, enable **My Library**
   attachment sync, and choose **WebDAV**.
2. Enter `https://zotero.rafael.media/zotero/` and your operator-provided WebDAV
   username/password, then click **Verify Server**.
3. Run Zotero's native sync. Open a known attachment on the other client.

If metadata arrives without the attachment, inspect the originating client's
upload/sync status before changing the server. A downstream reader may need
refresh/reopen after native sync. Never upload directly into application
databases. See [Zotero](hosts/apps/zotero-webdav/README.md) and the
[October incident](docs/zotero-lxc-outage-2026-10-07.md).

## Manage recipes and cocktails

Use Mealie with its own account to add/import a recipe, review the ingredients
and instructions, and save it. Reopen the saved recipe to check the import;
website imports can require manual correction.

Use Salt Rim at `bar.rafael.media` for the Bar Assistant interface. Complete
account setup, manage your bar's ingredients and cocktail recipes, and verify
saved records can be found again. The separate API and search hosts support
that interface and are private integration endpoints. API/search failures need
the operator's [whole-project runbook](hosts/apps/bar-assistant/README.md).
Neither journey was newly authenticated during the documentation review.

## Download media from a URL

Sign into yt-dlp Web UI, submit a supported media URL, choose the available
format/options, and wait for the job to finish. Verify the result plays before
removing your source reference. Site authentication, availability, and extractor
support can cause individual failures even when the service is healthy.

Output lives in the separate shared yt-dlp directory; it is not automatically
an organized Jellyfin library import and is outside appdata PBS. Do not supply
account cookies through chat or task logs. See [yt-dlp](hosts/apps/yt-dlp-web-ui/README.md).

## Use Home Assistant

Sign into Home Assistant, open the relevant dashboard, and control only the
intended device/automation. Confirm the device's actual state as well as the
dashboard response. Device-specific integrations and automations are durable
HAOS application state, not a complete device catalog in this repository.
The authenticated Homarr origin can embed its Hub dashboard.

Adding integrations, changing devices, or restoring HAOS is operator work;
preserve the managed VM and its native backups. See [HAOS](docs/haos-vm.md).

## Sync Obsidian and access shared files

Use Syncthing's private authenticated GUI to review the received vault. The
homelab folder is **Receive Only** at `/vault/shared/media/obsidian`; edit on
your paired device. Confirm it reaches an up-to-date state and review conflicts
before assuming every device has the same files. Phone pairing and any new
folder need explicit setup. The previous laptop seed is documented; it is not
proof of today's device sync.

Use the read-only `Media` SMB share for consumption. `Vault` is a separate
read-write administrative share; it is not an alternative file organizer.
Cockpit's administrative file access exposes appdata to the operator, while
SMB deliberately does not export it. SMB is LAN-only under the declared policy.
See [Syncthing/Proton](hosts/infra/obsidian-sync/README.md) and
[file access](hosts/infra/cockpit/README.md). Syncthing replication/versioning is
not an independent off-site backup; Proton remains disabled pending acceptance.

## Build private automation

Sign into n8n, create or edit a workflow, configure credentials in n8n's own
credential interface, and test it with limited inputs before activation. Review
the execution result and the actual downstream effect. Workflow actions use the
permissions of the supplied credentials; sharing an editor is privileged.

The editor and webhook routes are private to LAN/Tailscale. An internet service
cannot be assumed to reach a webhook. The operator must preserve both n8n
appdata and `N8N_ENCRYPTION_KEY` to recover stored credentials. See
[n8n](hosts/infra/n8n/README.md).

## Administer the homelab

Use Pulse to inspect guests, Docker containers, health, and capacity. Its Docker
agents allow lifecycle actions; image updates stay with backup-gated WUD.
PVE monitoring uses `PVEAuditor`, which cannot start/stop guests. Use Portainer
on the appropriate guest for supported inspection, keeping desired deployment
configuration in Git. PVE owns guests/storage; PBS owns backup history.

Prometheus exposes metrics/query functionality. Loki exposes an ingestion/query
API with no native auth, and has no declared log shipper; an empty log result
does not itself mean a collector is broken. Pi-hole and NPM are operator tools
for DNS/proxy administration. WUD's unauthenticated UI is loopback-only and is
not a user-facing dashboard. See [operations](docs/operations.md) before changes.

## Test a staging branch

Open the private Film-introspect staging URL with its configured access. It
starts in demo mode for UI/API and persisted-note development. Production
Jellyfin/Bazarr playback integrations are not implicitly supplied.

For a code change, push the intended application change to its declared
`staging` branch. The two-minute poller builds before cutover, checks health,
and either accepts the candidate or returns to the previous data generation.
Confirm the visible change and existing notes after deployment. A failed
candidate is held for review/retry; do not repeatedly modify data pointers.
The [staging runbook](hosts/staging/README.md) owns enrollment and rollback.

## Supporting and retained services

Databases/caches, Gluetun, FlareSolverr, Deunhealth, Portainer agents,
Cloudflare DDNS, Soularr, cross-seed, the Storyteller reconciler, and the
music-metadata writer support the workflows above; they do not need separate
consumer workflows. Bar API/search, health/Hello routes, and the HA observer
are integration or diagnostic endpoints.

DroppedNeedle is retained for a pending transition, Readarr remains legacy,
and Shelfarr's Libation companion is uncredentialed with its integration
disabled. Old Obsidian/OpenWebUI routes are not evidence of supported running
services. Live-only ContentFlow and an extra staging route are recorded as
drift in [status](docs/status.md), outside this checkout's declared capability
and recovery contract.

## Settings and integration boundaries

| Setting or input | Where it belongs | Result / restriction |
|---|---|---|
| Playback, reading, and progress preferences | Your account in the relevant app/client | Use the same identity on each device; accounts are not shared across apps |
| App users, libraries, or invitation permissions | Native app administration | An operator must preserve declared library paths and data ownership |
| Service ports, mounts, image channels, scan/recovery configuration | Git and the owning service runbook | UI-only changes may be lost or reconciled on rebuild |
| External API credentials and recovery secrets | Operator-managed PVE `/root/.env`, or the explicitly documented app credential store | Never put values in Git, issues, or this manual |
| Zotero attachment URL / GPodder / Navidrome connection | Client settings using the origins above | Test actual file or progress transfer; a successful login is not the whole workflow |
| Staging integrations | Explicit staging-prefixed configuration | Demo mode does not receive production keys automatically |

The important data distinction is between application records and user files.
Paperless originals live with appdata; media, photos, episode downloads, Aurral
flows, and Storyteller assets live in shared storage. See the
[coverage table](docs/operations.md#backup-and-recovery) before treating an
application export, synchronized copy, or healthy server as a backup.

## Troubleshooting

| Problem | First useful action |
|---|---|
| Private service inaccessible | Confirm LAN/Tailscale, DNS, and the exact hostname; report whether it is a timeout, 403, or 502 |
| Login fails | Use the correct app account; ask the operator to check recovery-account drift rather than reset shared credentials |
| Media requested but absent | Check the owning acquisition queue, then scan/import state; do not move/delete files |
| Playback/reading fails on one device | Try one representative item, record client/version and error; server health is not device acceptance |
| Zotero metadata syncs but files do not | Verify WebDAV and run native sync on the originating client |
| SMB/Kew loses music | Follow the native route/mount checks in the macOS guide |
| Unsure whether data is backed up | Consult the [coverage table](docs/operations.md#backup-and-recovery); shared media is excluded |

Report the goal, service, time, client, expected/actual result, and a sanitized
error. Never include passwords, API keys, account cookies, or private document
contents in issue logs. Recovery and destructive cleanup are operator workflows
with their own scope and verification.

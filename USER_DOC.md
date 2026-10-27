# Homelab user manual

Start at [Homarr](https://rafael.media) or a service below. Connect to the home
LAN or configured Tailscale path for private HTTPS services. Each application
has its own account and permissions; Homarr does not provide a shared login.
Some older routes have different access policies, so a `rafael.media` hostname
alone does not mean private access.

This manual describes Git-declared workflows. [Status](docs/status.md) records
last verification, unavailable services, and pending account/device acceptance.
Detailed deployment procedures belong to the [service runbooks](docs/reference/service-policies.md).

## Roles and data

Service users work within their granted libraries and permissions. Application
administrators manage that app; the homelab operator manages hosts, deployment,
and recovery. Pulse access also grants Docker lifecycle control.

Acquisition services organize permanent libraries; readers consume them.
Application state lives in appdata, while large media lives in shared storage.
**Shared media is outside appdata PBS backups**; see [coverage](docs/operations.md#backup-and-recovery).
Obtain accounts from the operator and keep credentials out of issue/task logs.

## Capability index

| Goal | Entry points | Instructions |
|---|---|---|
| Watch or request films/series | [Jellyfin](https://stream.rafael.ink), [Seerr](https://jellyseerr.rafael.media) | [Watch/request](#watch-and-request-films-or-series) |
| Take notes while a film keeps playing | [Film-introspect staging](https://film-introspect.staging.rafael.media) | [Screening notes](#take-notes-during-a-screening) |
| Invite a Jellyfin user | [Wizarr](https://wizarr.rafael.media) | [Invitations](#invite-someone-to-jellyfin) |
| Inspect acquisition | [Radarr](https://radarr.rafael.media), [Sonarr](https://sonarr.rafael.media), [Bazarr](https://bazarr.rafael.media), [Prowlarr](https://prowlarr.rafael.media), [qBittorrent](https://qbittorrent.rafael.media); NZBGet on Servarr port 6789 | [Queues](#inspect-acquisition) |
| Inspect stalls/storage/playback | [Cleanuparr](https://cleanuparr.rafael.media), [Sortarr](https://sortarr.rafael.media), [Jellystat](https://jellystat.rafael.media) | [Queues](#inspect-acquisition) |
| Request and play music | [Aurral](https://aurral.rafael.media), [Navidrome](https://navidrome.rafael.media); operator tools [Lidarr](https://lidarr.rafael.media), [slskd](https://slskd.rafael.media) | [Music](#request-and-listen-to-music) |
| Acquire and read books | [Shelfarr](https://shelfarr.rafael.media), [Listenarr](https://listenarr.rafael.media), [BookOrbit](https://bookorbit.rafael.media), [Kavita](https://kavita.rafael.media), [Audiobookshelf](https://audiobookshelf.rafael.media) | [Books](#acquire-and-read-books) |
| Review book metadata | [Grimmory](https://grimmory.rafael.media), Audiobookshelf | [Metadata](#review-book-metadata) |
| Create readalouds | [Storyteller](https://storyteller.rafael.media) | [Readalouds](#create-an-aligned-readaloud) |
| Listen to podcasts | [PinePods](https://pinepods.rafael.media) | [Podcasts](#subscribe-to-and-sync-podcasts) |
| Use desktop/portable media | SMB, Kew, Feishin, HifiMule/EchoList | [Desktop and ECHO](#use-desktop-media-and-snowsky-echo) |
| Browse photos / show a slideshow | [Immich](https://immich.rafael.media), [ImmichFrame](https://immichframe.rafael.media) | [Other services](#use-other-services) |
| Archive/process documents | [Paperless](https://paperless.rafael.media), [Stirling-PDF](https://pdf.rafael.media), [SnapOtter](https://snapotter.rafael.media) | [Other services](#use-other-services) |
| AI-assisted document metadata | [Paperless-GPT](https://paperless-gpt.rafael.media) — pending external key | [Restrictions](#use-other-services) |
| Sync research attachments | [Zotero WebDAV](https://zotero.rafael.media/zotero/) | [Zotero](#sync-zotero-attachments) |
| Recipes, cocktails, URL downloads | [Mealie](https://mealie.rafael.media), [Bar Assistant](https://bar.rafael.media), [yt-dlp](https://yt-dlp.rafael.media) | [Other services](#use-other-services) |
| Home automation | [Home Assistant](https://ha.rafael.media) | [Other services](#use-other-services) |
| Sync Obsidian / access files | [Syncthing](https://syncthing.rafael.media), SMB, [Cockpit](https://vault.rafael.media) | [Files](#sync-obsidian-and-access-shared-files) |
| Private automation | [n8n](https://n8n.rafael.media) | [Other services](#use-other-services) |
| Fleet administration / observability | [Pulse](https://pulse.rafael.media), Portainer, [PVE](https://proxmox.rafael.media), [PBS](https://backup.rafael.media), [Prometheus](https://prometheus.rafael.media), [Loki](https://loki.rafael.media/ready) | [Administration](#administer-the-homelab) |
| Test a development branch | [Film-introspect staging](https://film-introspect.staging.rafael.media), [Form & Field studio](https://ff.staging.rafael.media/create) | [Staging](#test-a-staging-branch) |

## Watch and request films or series

1. Search Jellyfin first and play the title if available.
2. If missing, choose the exact film/series in Seerr and submit a request using
   your granted permissions. Check its status instead of requesting it again.
3. After Radarr/Sonarr import and library discovery, play it on your client.

Success means the intended title plays in your permitted library. A request can
wait for approval, sources, quality matches, or import; use the owning queue to
investigate. Do not move/delete torrent files to force progress.

## Take notes during a screening

Open [Film-introspect](https://film-introspect.staging.rafael.media) from the LAN
or Tailscale. Search a film title: Meta Egg looks up its metadata online and
searches for matching English subtitle releases when you select the result.
Selecting a discovered film saves its metadata in Meta Egg. Opening a matching
subtitle version automatically saves its timed transcript for reuse after
restarts; the movie video is not copied. Choose the release matching your copy.
If subtitle setup is missing or the
provider cannot supply a track, the app explains the remaining step. It needs
no Jellyfin account. **Sintel (2010)** is bundled with licensed English subtitles
for trying the complete workflow without provider setup. Play the
[official film](https://video.blender.org/videos/watch/0eb052d0-fd51-43e6-aa33-ecdbf77a5d40)
on another screen to try the workflow.

1. Search for **Sintel**, choose the result and cut, then open the screening and
   choose the English subtitle track.
2. Under **Sync with the screen**, use **External screen — set the clock**.
   Enter the film's elapsed time and press **Sync now**, or sync to a matching
   line of dialogue. Use **−0.5 s** / **+0.5 s** to correct alignment.
3. Focus **Quick note** at the moment you want to capture. Its timestamp and
   subtitle view hold while the film and app clock keep advancing.
4. Press **Save & catch up** or **Cmd/Ctrl+Enter**. The note keeps the held
   timestamp, and the subtitles return to where the film is now. Saved notes
   appear under **Notes in this cut**; the film does not need to pause.

The app does not automatically detect an external film's clock, pauses or seeks.
Realign it when needed. Metadata discovery does not guarantee a matching
transcript. Subtitle downloads require the operator's OpenSubtitles application
key and remaining provider allowance; a release label does not prove the copy
playing on screen. Jellyfin session following is an optional separately
configured integration. See the
[pilot evidence](docs/evidence/2026-10-22-screening-standalone-pilot.md) and
[operator runbook](hosts/staging/README.md#film-introspect-settings).

## Invite someone to Jellyfin

As a Wizarr administrator, configure the intended server and permissions, then
create the invitation from [join-stream.rafael.ink](https://join-stream.rafael.ink).
The recipient redeems it and signs into [Jellyfin](https://stream.rafael.ink).
Verify access to the intended libraries. Remote guests need a public-origin
invitation; `wizarr.rafael.media` is private. Setup details:
[Wizarr](hosts/apps/wizarr/README.md).

## Inspect acquisition

Check the owning service's queue/import error before its download client:
Radarr for films, Sonarr for TV, Lidarr for music, Shelfarr for ebooks, Listenarr
for audiobooks. Prowlarr manages sources; Bazarr handles subtitles. Sortarr is
read-only storage analytics and Jellystat shows playback statistics.

Cleanuparr handles managed stalled torrents through the owning Arr with
blocklisting/replacement searches. Never delete those directly in qBittorrent.
Cross-seed is a VPN-only background helper, not an import path. Operator details
are in the [acquisition runbooks](docs/reference/service-policies.md).

## Request and listen to music

1. Select an artist/album in Aurral and request it; track it in **Activity**.
2. Lidarr searches immediately. Eligible unresolved requests can later use
   Soularr/slskd, with deliberate grace periods and retry limits.
3. After import/scan, find the album in Navidrome or Jellyfin. Check artist,
   track order, and actual playback.

Lidarr owns permanent music; Aurral's generated flows use a separate library.
Generated-flow acceptance is still pending in status. Do not start another
organizer or change retained DroppedNeedle during that transition. See
[Aurral](hosts/apps/aurral/README.md) for requests and flows.

## Acquire and read books

1. Request the intended work, language, edition, and format through Shelfarr
   (ebooks) or Listenarr (audiobooks).
2. Let the owner import the completed download. Readers discover canonical
   files through their scan/watch schedule; Audiobookshelf has a daily fallback
   scan with its watcher disabled.
3. Open ebooks/PDFs/comics/manga in BookOrbit or Kavita, and audiobooks in
   Audiobookshelf. Check a page/chapter and progress resume.

Readers must not move/rename canonical files. Shelfarr's direct providers,
non-admin uploads, and Libation integration are disabled; Readarr is legacy.
Physical reader setup follows [BookOrbit](hosts/apps/bookorbit/README.md) or
[Kavita](hosts/apps/kavita/README.md). Acquisition constraints are in
[Shelfarr](hosts/servarr/shelfarr/README.md) and [Listenarr](hosts/servarr/listenarr/README.md).

## Review book metadata

This is operator-assisted publication with focused rollback. In Grimmory,
review EPUB proposals against identifier, title, author, language, and edition.
Its completeness score is not identity confidence; ambiguous matches stay held.

For audiobooks use Audiobookshelf's reviewed native embed tool with stream copy,
existing chapters, and a retained backup. Verify codec, duration, and chapters.
**Never write audiobooks through Grimmory**; its M4B pilot destroyed streams and
chapters. Exact procedures: [Grimmory](hosts/apps/grimmory/README.md) and
[Audiobookshelf](hosts/apps/audiobookshelf/README.md).

## Create an aligned readaloud

The EPUB/audio need the identical canonical `author/title` key. Storyteller
stages verified copies without modifying either source.

1. In **Books**, filter **Missing readaloud** and select the imported pair.
2. Choose **Actions → Begin processing → Continue where left off**.
3. Let the single-worker queue finish, then test alignment, chapters, and resume.

Ambiguity, changed sources, or low space need the operator's reconciler report;
do not edit SQLite or rename originals to force processing. Accepted readalouds
are not disposable cache. See [Storyteller](hosts/apps/storyteller/README.md).

## Subscribe to and sync podcasts

1. In PinePods add a feed or import OPML; download/play an episode and check
   saved progress.
2. Enable **Settings → Podcast Sync Settings** for GPodder. Configure a
   compatible client with the PinePods HTTPS origin and your account.
3. Play/pause on each client and verify progress reaches the other.

OPML transfers subscriptions, not progress. Audiobookshelf's former podcasts
are retained but inactive; do not migrate progress by editing databases.
See [PinePods](hosts/apps/pinepods/README.md) for client-sync details.

## Use desktop media and SNOWSKY ECHO

On the LAN, connect Finder to `smb://192.168.0.110/Media` with your Samba account.
Kew reads `/Volumes/Media/music`; the [macOS helper](clients/macos-media/README.md)
reconnects without providing an offline cache. Its guide covers Tailscale exit
node **Allow Local Network Access**. Feishin can use Navidrome and your account.

For ECHO, follow the [card runbook](clients/snowsky-echo/README.md): HifiMule sync
into `Music/Managed` → EchoList into `Music/Playlists` → optional PinePods compiler
into `Podcasts/PinePods` → check/eject → refresh and test on-device. Never select
canonical server music as an output destination.

## Sync Zotero attachments

Zotero account sync handles metadata; WebDAV handles personal-library
attachments only, not group-library attachments.

1. Open **Settings → Sync → File Syncing**, enable **My Library**, select **WebDAV**.
2. Enter `https://zotero.rafael.media/zotero/` and the operator-provided WebDAV
   credentials; click **Verify Server**.
3. Run native Zotero sync and open a known attachment on the other client.

If only metadata arrives, inspect the originating client's upload status, then
refresh/reopen the downstream reader. See [Zotero](hosts/apps/zotero-webdav/README.md).

## Sync Obsidian and access shared files

Syncthing receives `/vault/shared/media/obsidian` as **Receive Only**. Edit on a
paired device, verify the server reaches up-to-date, and review conflicts.
New devices/folders need explicit pairing; see [Syncthing](hosts/infra/obsidian-sync/README.md).

SMB `Media` is read-only consumption; `Vault` is read-write administration, not
an alternative media organizer. Both follow the LAN-only policy. Cockpit offers
operator file access, including appdata that SMB does not export. See
[file access](hosts/infra/cockpit/README.md). Replication is not off-site backup.

## Use other services

Sign into the appropriate app and complete any first-login password/MFA steps.
Use a small input first and inspect the result before replacing an original.

| Service | Workflow and local restriction |
|---|---|
| Immich | Upload/browse photos and albums; open an original to confirm upload. Shared originals need separate protection. |
| [ImmichFrame](hosts/apps/immichframe/README.md) | Open the private slideshow on a LAN/Tailscale display. Empty results need key/collection/connectivity checks, not a database reset. |
| [Paperless](hosts/apps/paperless-ngx/README.md) | Upload → wait for processing → correct title/tags → verify search and original download. Originals live in appdata. |
| [Paperless-GPT](hosts/apps/paperless-gpt/README.md) | Pending a real API key. Sends selected content to OpenAI, has no native auth, stays private; automatic PDF replacement is disabled. |
| [Stirling-PDF](hosts/apps/stirling-pdf/README.md) | Choose a tool → upload a copy → process → download and inspect pages/content. |
| [SnapOtter](hosts/apps/snapotter/README.md) | Choose a file/media tool → upload a copy → process and inspect output. Configured limit: 500 MiB; installed version/packs determine tools. [Tool reference](https://docs.snapotter.com/). |
| Mealie | Add/import a recipe, correct ingredients/instructions, save and reopen it. |
| [Bar Assistant](hosts/apps/bar-assistant/README.md) | Use Salt Rim at `bar.rafael.media` for ingredients/cocktails; save and find the record again. API/search hosts are supporting endpoints. |
| [yt-dlp](hosts/apps/yt-dlp-web-ui/README.md) | Submit URL/options → wait → verify playback. Site/extractor restrictions can fail a job. Output is separate from organized libraries. |
| [Home Assistant](docs/haos-vm.md) | Use the relevant dashboard and confirm actual device state. Device-specific configuration lives in HAOS; integrations/restores require operator work. |
| [n8n](hosts/infra/n8n/README.md) | Configure credentials in-app → test limited inputs → inspect downstream effects → activate. Public webhook ingress is disabled. |

## Administer the homelab

Pulse shows guests, containers, and capacity; its agents allow Docker lifecycle
actions but image updates stay with WUD. PVE monitoring is read-only through
`PVEAuditor`. Use the guest's Portainer for inspection while keeping desired
configuration in Git. PVE owns guests/storage; PBS owns backup history.

For the private blog, open [Umami](https://analytics.staging.rafael.media) and
select **The Night Archive — staging**. The expanded Pages report distinguishes
pageviews from estimated visitors; inspect Referrers and the `map-fit` /
`map-fullscreen-toggle` events separately. The [Blog dashboard](https://grafana.staging.rafael.media/d/blog/blog)
shows endpoint checks and server requests. Those requests include assets and
bots, so they should not equal readership counts. Sign in with the operator
account; the [runbook](hosts/staging/blog-observability/README.md) owns credentials
and configuration. Alerts currently have no notification receiver.

Prometheus exposes metrics queries. Loki receives the blog's sanitized access
logs through Alloy and has no native auth; keep it private. Pi-hole/NPM are
operator DNS/proxy tools. WUD's UI is
loopback-only. Follow [operations](docs/operations.md) before making changes.

## Publish a project to production

Production is a separate, explicitly requested release from the application's
`main` branch. Pushing code or reviewing staging does not publish it. The blog's
reserved destination is **https://rafael.ink**; its scaffold leaves the existing
placeholder unchanged until the [activation command](hosts/production/README.md#activation)
is run. The remote blog `main` branch is currently absent; accepting and promoting
a chosen review revision remains a separate step.

In Umami select **The Night Archive — production** for public readership and
**The Night Archive — staging** for preview traffic. Grafana has a separate
**Blog — production** dashboard. Monitoring is prepared while the app is off;
notification delivery and external uptime observation are not configured.

## Test a staging branch

Open the separate [Staging Homarr board](https://rafael.media/boards/Staging)
for staging applications. Newly registered apps appear within roughly two
minutes; disabled Symphony apps and removed Compose registrations disappear.
Your main and mobile home boards stay unchanged. Operator details are in the
[staging runbook](hosts/staging/README.md#push-a-staging-release).

[The Night Archive](https://blog.staging.rafael.media) serves the blog privately
on LAN/Tailscale. Code follows its private repository's `staging` branch.
The connected `Blog/` tree controls the private preview's complete structure.
Deleting a section, topic or article removes it on the next successful sync/build;
Git seed content cannot restore it. Descriptions may stay empty, including on
published articles. Public releases still require separate approval.

For writing, open `Blog/_Start here` in your Mac Obsidian vault and insert a Blog
template inside a topic. Embed existing notes with `![[Note name]]`; their YAML
is ignored. Add `cover-media` and `cover-alt` for grid cards. `Blog/Articles.base`
separates drafts and published selections. Both preview on staging after sync;
production still requires an approved release and its hosting configuration.
Excalidraw embeds now follow their original notes and recursively linked resources.
Rename an article note or menu folder to change its website label; order stays in
`_index`. Synced edits refresh the static preview automatically without restarting
the website. The [publisher runbook](hosts/infra/blog-publisher/README.md) owns setup and recovery.

Film-introspect uses Meta Egg’s online discovery and bundled Sintel catalog for its
[screening note workflow](#take-notes-during-a-screening). Jellyfin is optional;
process health alone does not prove alignment with an externally playing film.

Push the intended application change to its declared `staging` branch. The
two-minute poller builds before cutover and accepts a healthy candidate or
restores the previous data generation. Confirm the change and existing notes.
Failed candidates are held for review/retry; do not modify data pointers to
force them. Enrollment/rollback: [staging runbook](hosts/staging/README.md).

## Troubleshooting

Change personal preferences in the app/client, users and library permissions
in native administration, and deployment settings through the operator's Git
configuration. External credentials belong only in the documented secret store.
Background workers, databases, and proxies support the workflows above; a
retained container or old dashboard tile does not establish a supported service.

| Problem | First useful action |
|---|---|
| Private service inaccessible | Check LAN/Tailscale, DNS, hostname; distinguish timeout, 403, and 502 |
| Login fails | Check the app identity and account drift; do not reset shared credentials to diagnose it |
| Requested media absent | Check acquisition queue, import, then reader scan; do not move/delete files |
| One client fails | Record client/version and a representative item; server health does not prove device acceptance |
| Zotero files absent / SMB unavailable | Use the specific client workflow above |

Report goal, service, time, client, expected/actual result, and sanitized error.
Recovery and cleanup follow [operations](docs/operations.md); secrets and private
content never belong in issue logs.

## Remove a development project

Use the [coordinated removal process](hosts/staging/README.md#coordinated-project-removal)
for Mac, VM, staging and GitHub cleanup. Preview with `agentctl project plan`,
review its exact inventory, then apply/resume the saved plan. Retirement and
removal of active copies are separate stages; recovery history is retained.

## Archive photos selected in Immich

Use [Stillroom staging](https://stillroom.staging.rafael.media) with owner albums
named `Archive: …`. Wait for tracking, then trash the album assets and leave
them in trash until archiving finishes. First complete the disposable sample
check in Activity. Originals and companions move to `/shared/archive/temp`
(`/vault/shared/archive/temp` on PVE) after the five-minute undo window.
Sort completed batches into `archive/body-update` between runs. Restoring in
Immich alone cannot restore moved files; use the documented filesystem restore.
See the [staging workflow](hosts/staging/README.md#stillroom-external-library-archiving).

# Copy-ready agent prompts for the media pipeline

Date: 2026-07-25

Run these prompts in order, one agent at a time. Do not dispatch the six agents
in parallel. Give the next prompt only after the prior phase is committed,
pushed, deployed, and its evidence is present in the repository.

Each prompt directs the agent to implement the phase, not merely propose it.
The agent may make reasonable in-scope decisions after inspecting live state
and current official upstream documentation. A contradiction that could cause
data loss, public exposure, or an unrecoverable migration is a reason to stop
and report, not a reason to guess.

The placement and Compose boundaries are fixed across all six prompts:

- Shelfarr and Soularr run on CT102 `servarr`.
- BookOrbit, Storyteller, PinePods, Aurral, and Navidrome run on CT112 `apps`.
- Each primary application is a separate repository-managed Docker Compose
  project with its own Compose file.
- A primary application's private database, cache, broker, worker, or required
  companion container belongs in that same Compose project and private
  network. Existing first-class services such as slskd and the
  `servarr-hello` project remain independent.

## Part 1 of 6 — storage, ownership, recovery, and integration foundation

```text
Implement part 1 of 6 of the books/audiobooks/podcasts/music pipeline in
/Users/rafael/Repos/dothomelab.

First read AGENTS.md, the homelab-operator skill, and
docs/media-pipeline-plan-2026-07-25.md in full. This is an implementation task,
not an architecture discussion. Inspect live state before changing it using
root@192.168.0.250 and pct exec for LXCs. Do not SSH into LXCs. Do not print or
source /root/.env.

Scope this phase to the shared contract and recovery/integration scaffolding.
Do not deploy Shelfarr, BookOrbit, Storyteller, PinePods, Aurral, Soularr, or
Navidrome yet.

Treat future placement as fixed: Shelfarr and Soularr belong on CT102;
BookOrbit, Storyteller, PinePods, Aurral, and Navidrome belong on CT112. Each
primary application will have its own Compose project, with its private
supporting containers in the same project.

Required work:

1. Re-inspect PVE/ZFS capacity, CT102 and CT112 configs, bind mounts, UID/GID
   mappings, ACLs, existing media/appdata directory ownership, Docker project
   state, backup timer state, and the current deployed commit. Record a concise
   preflight without exposing filenames or secrets.
2. Reconcile and declare the canonical host paths from the master plan in
   provision/inventory.env and bootstrap/provisioning code. Preserve the
   existing top-level paths. Create only missing exact directories. Do not
   recursively chmod or chown anything.
3. Keep CT112's broad /data mount read-only. Declare only the narrow
   read-write mounts that later phases genuinely require. Avoid consuming an
   mp number until its exact target is known and verified. CT102 already has
   the required shared RW view; do not broaden anything else.
4. Define one shared relative book-key contract for Shelfarr's future ebook
   and audiobook output. Do not invent current Shelfarr template syntax in
   code; document the required resulting directory shape so parts 2 and 3 can
   configure it from the then-current official settings.
5. Add non-secret .env.example placeholders and comments only for values that
   are already confirmed as necessary by current official upstream docs.
   Provide idempotent secret-initialization helpers later where appropriate;
   never commit generated values.
6. Add or extend a repository verifier for the media data contract. It must
   validate path existence, expected dataset/mount source, read-only versus
   read-write access from the correct guest/user context, and sufficient free
   space without writing probe files into canonical media. Make it useful to
   every later phase.
7. Update bootstrap dry-run behavior, docs/rebuild.md, README's architecture
   tree only where appropriate, and a new phase-1 evidence document. State
   explicitly which shared data is outside PBS and which future state will be
   inside appdata.
8. Do not start an on-demand backup for this routine, non-durable foundation
   change. Confirm the recent scheduled job is successful and WUD still has no
   independent timer.

Verification:

- run relevant syntax and shell checks;
- run bootstrap.sh --dry-run;
- run the new media-contract verifier locally where possible and live on the
  affected host/guests;
- prove no existing Compose project or service was restarted or changed;
- prove the backup-to-WUD success-only relationship is unchanged;
- inspect git diff for secrets and unrelated changes.

Preserve the repository's one-command recovery invariant. Record rollback and
remaining prerequisites. Finish with intentional commits, push the completed
phase to the current upstream branch, and report exact verification evidence.
Do not claim later applications are deployed.
```

## Part 2 of 6 — Shelfarr ebook acquisition and BookOrbit

```text
Implement part 2 of 6 of the books/audiobooks/podcasts/music pipeline in
/Users/rafael/Repos/dothomelab.

Read AGENTS.md, the homelab-operator skill,
docs/media-pipeline-plan-2026-07-25.md, the part-1 evidence, and current
official Shelfarr and BookOrbit documentation before acting. Inspect live
state first. This is an end-to-end implementation and deployment task, not a
design-only answer. Operate LXCs through pct exec and never expose production
environment values.

End state for this phase:

- Shelfarr is a separate repository-managed project on CT102 because CT102
  already owns the download clients and has RW access to canonical media.
- BookOrbit is a separate repository-managed project on CT112.
- A user-owned or public-domain EPUB can be fulfilled through Shelfarr,
  organized under the canonical ebook root using the shared book key, followed
  by a BookOrbit scan and successful reading/download.
- Kavita and Readarr remain available for rollback/parallel comparison. Do not
  delete, overwrite, or migrate away their appdata.

Required implementation:

1. Revalidate current upstream image names, required companion services,
   ports, health endpoints, environment, storage, BookOrbit API integration,
   reverse-proxy requirements, and upgrade notes from primary sources. Use
   upstream application :latest/rolling stable tags as directed by the master
   plan. Keep application databases on explicit supported major tags with
   wud.watch=false.
2. Add separate hosts/servarr/shelfarr and hosts/apps/bookorbit projects, each
   with its own Compose file, prepare, verify, README, deterministic appdata
   paths, least privilege, meaningful health checks, resource limits where
   useful, and no production secrets in Git. Keep every application-private
   supporting container in its owning project's Compose file and network.
3. Keep Shelfarr's Audible/Libation beta disabled and uncredentialed. If the
   current upstream Compose requires an idle companion for normal operation,
   include only the minimum documented component in Shelfarr's Compose project
   and prove it stays inactive. Do not add direct-download providers or new
   indexers. Connect only the user's existing authorized Prowlarr and
   qBittorrent/NZBGet endpoints.
4. Configure Shelfarr's ebook output to
   /vault/shared/media/books/ebooks (the corresponding CT102 path is /data/...)
   with the shared relative book-key directory contract. Shelfarr is the sole
   physical organizer.
5. Deploy BookOrbit with canonical books mounted read-only initially, its small
   durable state and application-local database under
   /srv/appdata/docker/bookorbit, and current upstream hardening that is
   compatible with the homelab. Put BookOrbit's PostgreSQL/pgvector container
   in the BookOrbit Compose project. Use its supported explicit database
   major, not latest, and exclude the database from WUD.
6. Keep BookOrbit physical rename and embedded-file metadata writes disabled.
   Configure separate ebook/PDF/comic libraries only where current paths
   actually exist. Configure the supported filesystem output plus BookOrbit
   library sync/scan integration in Shelfarr; do not invent a Book Dock API.
7. Add idempotent production-secret initialization for BookOrbit and any
   Shelfarr secret that must survive rebuilds. Write values only to
   /root/.env, never display them, and document all placeholders in
   .env.example.
8. Add a BookOrbit database logical-dump pre-backup hook and a safe isolated
   restore test based on the repository's existing patterns. Never copy a live
   PostgreSQL data directory as a migration or restore method.
9. Add private NPM routes for shelfarr.rafael.media and
   bookorbit.rafael.media, preserving the wildcard certificate, LAN/Tailscale
   ACL, WebSockets if required, and final deny. Reconcile Homarr idempotently.
   Do not add public exposure.
10. Integrate both projects into bootstrap, guest repo sync, deployment order,
    WUD sequential checks, expected inventory/count verification, backup and
    restore docs, .env.example, README, and focused evidence.

Acceptance test:

- run docker compose config before deployment;
- use a DRM-free user-owned or public-domain sample;
- exercise Shelfarr's request/approval/fulfillment/import lifecycle. Prefer a
  legal end-to-end existing source; if source acquisition cannot be exercised,
  use Shelfarr's supported manual fulfillment and separately verify every
  existing Prowlarr/download-client API connection without adding a source;
- verify the resulting file path follows the shared book key and record source
  and destination hashes;
- prove BookOrbit discovers it through the configured integration/scan and can
  serve/read/download it;
- verify OPDS and the KOReader/Kobo configuration surfaces. Test a physical
  device only if available; otherwise document the exact remaining device-side
  action without claiming it passed;
- prove BookOrbit cannot modify the canonical ebook bytes;
- run the logical dump and isolated restore test;
- verify direct health, logs, UID/GID, mounts, DNS, private HTTPS, Homarr, WUD
  enrollment/exclusions, bootstrap dry-run, focused verify scripts, and
  provision/verify.sh;
- prove Kavita and Readarr still work and their state is untouched.

Do not start a routine on-demand PBS backup. Use a task-specific backup only
if live inspection identifies existing durable data that this phase will
migrate. Preserve rollback artifacts. Update the phase evidence, commit all
completed work, push it, synchronize the intended commit to affected guests,
and leave the live deployment traceable to Git.
```

## Part 3 of 6 — Shelfarr audiobook acquisition and Audiobookshelf

```text
Implement part 3 of 6 of the books/audiobooks/podcasts/music pipeline in
/Users/rafael/Repos/dothomelab.

Read AGENTS.md, the homelab-operator skill,
docs/media-pipeline-plan-2026-07-25.md, and the evidence for parts 1 and 2.
Inspect live state and current official Shelfarr and Audiobookshelf docs before
changing anything. Continue the existing Shelfarr project rather than
deploying a second request manager. Use pct exec for LXCs and do not expose
secrets.

End state for this phase:

- Shelfarr handles both ebook and audiobook requests while remaining the sole
  canonical file organizer.
- Audiobooks are written under the canonical audiobook root with the exact
  same relative book-key contract as ebooks.
- Audiobookshelf remains the canonical audiobook listening/progress service,
  sees the library read-only, and is scanned after a Shelfarr import.
- Readarr and Audiobookshelf's current podcast state remain available. Do not
  delete or retire them in this phase.

Required implementation:

1. Reinspect current Shelfarr format, path-template, completed-download,
   qBittorrent/NZBGet remote-path, and Audiobookshelf integration behavior from
   current upstream docs and the live API surfaces.
2. Configure the audiobook output at
   /vault/shared/media/audiobooks (CT102 /data/... path) with the same
   normalized per-book relative key used by the ebook branch. Support one M4B
   and ordered multi-file audio without flattening tracks or colliding
   editions.
3. Keep staging and incomplete downloads outside the final library. Preserve
   seeding behavior and do not make Audiobookshelf, BookOrbit, or Storyteller
   rename Shelfarr-owned files.
4. Configure Shelfarr's supported Audiobookshelf library/inventory sync and
   scan trigger using a scoped application token stored in /root/.env. Add
   only placeholders to Git and never print the token.
5. Review and harden the existing Audiobookshelf project, prepare, verifier,
   private NPM route, WebSockets, Homarr entry, backup docs, and WUD sequential
   health gate as needed. Keep the upstream application latest channel and
   backup-gated WUD.
6. Keep /audiobooks read-only. Do not enable automatic M4B merge, source-tag
   writing, cover writing, or other media mutation. App config, metadata,
   progress, and application backups remain writable in appdata.
7. Update bootstrap, recovery docs, verification, expected counts only when
   actual container placement changes, the overall media plan evidence, and
   the exact first-run library settings.

Acceptance test:

- run docker compose config before deployment;
- use a DRM-free user-owned or public-domain audiobook;
- exercise request, approval, acquisition or supported manual fulfillment,
  completed-download import, naming, and Audiobookshelf scan;
- prove the final relative directory key is the same as the ebook branch would
  produce for the same work;
- verify single-file or multi-file chapter ordering, metadata display,
  browser playback, seek/resume, and a mobile/offline surface if a client is
  available;
- record hashes before and after the Audiobookshelf scan/play test and prove
  the source bytes were not changed;
- verify Shelfarr's ebook workflow from part 2 still passes;
- verify direct health, logs, permissions, mounts, DNS, private HTTPS,
  WebSockets, Homarr, WUD gates, recent backup state, bootstrap dry-run,
  focused verify scripts, and provision/verify.sh;
- verify Readarr and the existing Audiobookshelf podcast library/data are
  unchanged.

Do not run a routine on-demand PBS backup and do not delete any old service,
database, appdata, download, or media. Record rollback and evidence, commit and
push the completed phase, sync the intended commit to the affected guests, and
leave live state traceable to Git.
```

## Part 4 of 6 — Storyteller as an automatic paired-book path

```text
Implement part 4 of 6 of the books/audiobooks/podcasts/music pipeline in
/Users/rafael/Repos/dothomelab.

Read AGENTS.md, the homelab-operator skill,
docs/media-pipeline-plan-2026-07-25.md, and all prior phase evidence. Inspect
live PVE/CT112/storage/resources and current official Storyteller
self-hosting, scanner/import-mode, alignment, mobile, and stalign
documentation before acting. This phase must make Storyteller a first-class
path for nearly every confident ebook+audiobook pair, not a sparse manual
experiment.

Safety and ownership are non-negotiable:

- canonical Shelfarr ebook and audiobook trees are read-only inputs;
- never use Storyteller reference-in-place, move-from-canonical, or hard links
  to canonical files;
- never edit Storyteller's database to automate imports or processing;
- only DRM-free user-owned or public-domain media may be processed;
- the pairing/processing queue is sequential and resource bounded.

Required implementation:

1. Revalidate the current official Storyteller image, data layout, health
   endpoint, secret-key handling, watch/import modes, supported processing
   interfaces, readaloud output, current vulnerability floor, and resource
   guidance. Use registry.gitlab.com/storyteller-platform/storyteller:latest
   if it remains the official stable rolling image.
2. Add a separate repository-managed hosts/apps/storyteller project with its
   own Compose file, prepare, verify, README, private
   storyteller.rafael.media NPM route, Homarr entry, bootstrap/deploy
   integration, backup/restore classification, and backup-gated WUD. Keep any
   containerized reconciler, worker, or other Storyteller-private supporting
   service in this Compose project. Add a busy-job guard so WUD never replaces
   Storyteller during an active import/alignment.
3. Generate the Storyteller secret reproducibly from a persistent value in
   /root/.env into a mode-0600 runtime/appdata file if the current Compose
   secret interface requires it. Never log or commit the value.
4. Keep small irreplaceable database/config/manifest state in appdata. Put
   large disposable staging, cache, source copies, and readaloud assets under
   the planned shared Storyteller paths when the current layout supports a
   safe split. If /data is indivisible, measure projected growth and implement
   a documented capacity guard so rpool/appdata cannot silently fill. State
   exactly which assets PBS covers and which are reproducible/outside PBS.
5. Add only narrow Storyteller RW mount(s); preserve CT112 /data as read-only.
   Inspect UID/GID mapping and use targeted ownership on newly created exact
   paths only. Never recursively alter existing shared/appdata trees.
6. Implement an idempotent pairing reconciler in Git. For new acquisitions it
   must compare the exact relative book key used by Shelfarr, accept exactly
   one EPUB side plus one supported audiobook side, support multi-file audio,
   copy through a temporary per-book directory, verify copies, then atomically
   publish one Storyteller watch folder. It must maintain a durable manifest
   containing source paths/identity, size, mtime or hashes, stage state,
   Storyteller state, attempts, and last error.
7. Conflicts, incomplete pairs, multiple EPUBs, changed sources, unsafe names,
   low free space, or copy/hash failure must be reported and skipped without
   modifying either canonical source. Legacy fuzzy matches may be listed as
   candidates but must never auto-stage on title similarity alone.
8. Run reconciliation through a reproducible companion service in the
   Storyteller Compose project, with scheduling installed by bootstrap if a
   separate timer is required. Prevent overlapping runs, bound work per
   invocation, keep logs free of secrets, and expose a dry-run plus
   status/report command.
9. Configure Storyteller auto-import so staged copies become one matched book.
   Because the stage contains disposable copies, a current supported
   move-to-library mode is acceptable. A mode that moves canonical files is
   not.
10. Automate alignment only through a supported current Storyteller
    processing interface or the official stalign tool. Prefer the server's
    supported queue so mobile progress and assets remain native. If no stable
    non-interactive trigger exists, do not reverse-engineer the database:
    auto-import all confident pairs, provide the exact “ebook+audiobook but not
    aligned” bulk view/action, and document this single resource-aware human
    gate.
11. Start with one processing job at a time, conservative turbo/parallel
    settings, and explicit CPU/memory limits. CT112 was observed with 5 vCPUs,
    12 GiB assigned and about 5.5 GiB available; the host had about 14 GiB
    available. Re-measure. Increase CT112's declared memory only if live host
    reserve remains safe and update inventory/bootstrap together. Prove other
    Apps remain healthy during a complete alignment.
12. Add database/integrity backup checks appropriate to the current
    Storyteller store, cache cleanup guidance that never deletes source or
    accepted readalouds, update/rollback docs, and focused live verification.

Acceptance test:

- run docker compose config before deployment;
- use one matched public-domain or user-owned EPUB+audiobook pair placed through
  the canonical Shelfarr-compatible directory keys;
- record canonical hashes, run the reconciler twice, and prove exactly one
  verified staged/imported item with no recopy on the second run;
- complete one real alignment. Storyteller documents that CPU processing may
  take hours, so monitor it to terminal success rather than declaring success
  when it merely starts;
- verify the produced readaloud, reading/listening position switching in a
  supported Storyteller reader or exported EPUB Media Overlay surface, and
  unchanged canonical hashes;
- create one intentional ambiguous fixture and prove it is reported but not
  staged;
- test restart/idempotency, low-space/error behavior without filling storage,
  direct health, logs, permissions, mounts, DNS, private HTTPS, Homarr,
  WUD-busy protection, recent backup state, bootstrap dry-run, all focused
  verifiers, and provision/verify.sh;
- rerun the part-2 ebook and part-3 audiobook acceptance checks.

Do not delete source media, Storyteller assets, old apps, or rollback data. Do
not start a routine on-demand backup. Record exact runtime/resource/alignment
evidence and any unavoidable UI action. Commit and push the completed phase,
sync the intended commit to affected guests, and leave live state traceable to
Git.
```

## Part 5 of 6 — PinePods and podcast separation

```text
Implement part 5 of 6 of the books/audiobooks/podcasts/music pipeline in
/Users/rafael/Repos/dothomelab.

Read AGENTS.md, the homelab-operator skill,
docs/media-pipeline-plan-2026-07-25.md, and all prior phase evidence. Inspect
live CT112, the existing Audiobookshelf podcast library/data, appdata, mounts,
NPM, backup hooks, and the current official PinePods repository and server
documentation before changing anything. Use pct exec for LXCs and never expose
credentials.

End state:

- PinePods is the canonical podcast subscription, download, playback, and
  progress service.
- Podcast episodes live in a PinePods-owned subtree under
  /vault/shared/media/podcasts and remain outside the appdata PBS backup.
- PinePods database/config/backups are under /srv/appdata/docker/pinepods and
  recoverable through logical dumps plus a tested restore.
- Audiobookshelf remains canonical for audiobooks. Its old podcast state and
  files remain recoverable until migration acceptance; no data is deleted.

Required implementation:

1. Revalidate the current official PinePods application image, Compose
   services, ports, health/readiness, PostgreSQL data-dir guidance, Valkey
   requirement, PUID/PGID behavior, OIDC/admin bootstrap, GPodder API, client
   support, backup/restore, and upgrade notes.
2. Add a separate hosts/apps/pinepods project with its own Compose file. Keep
   the PinePods application, its PostgreSQL service, its Valkey service, and
   any other PinePods-private supporting containers in that project and
   private network. Enroll the upstream application :latest stable channel in
   backup-gated WUD. Use the upstream-supported explicit PostgreSQL and Valkey
   majors with wud.watch=false.
3. Store database, configuration, and portable logical dumps under canonical
   appdata. Mount only the PinePods episode subtree read-write. Do not give
   PinePods write access to all shared media and do not reuse Audiobookshelf's
   appdata.
4. Add idempotent secret initialization into /root/.env for database/admin or
   OIDC values that must survive rebuilds. Add only placeholders and safe
   generation instructions to .env.example.
5. Add a current logical-dump pre-backup hook and an isolated restore test.
   Verify row/object counts and application readability from the restored
   database. Never restore by copying PostgreSQL files between major versions.
6. Add a private pinepods.rafael.media NPM route, required WebSockets/headers,
   LAN/Tailscale ACL, Homarr reconciliation, direct and external health gates,
   bootstrap order, WUD sequential behavior, counts, recovery docs, and
   focused evidence.
7. Inventory existing Audiobookshelf podcast subscriptions, episode files,
   progress, and users without logging private feed credentials. Use
   supported OPML/GPodder/API export/import where available. Preserve private
   feed secrets only in /root/.env or application state, never Git.
8. Prove PinePods first. Only after representative subscription, download,
   playback, progress sync, and restore tests pass may Audiobookshelf's
   podcast library be marked inactive and its writable podcast mount removed
   from desired-state Compose if that does not strand data. Preserve the old
   directory and Audiobookshelf appdata. If progress cannot be migrated
   through a supported interface, record it precisely rather than editing
   either database.

Acceptance test:

- run docker compose config before deployment;
- subscribe to a public test feed or a user-authorized feed;
- refresh, download one episode, play/seek/resume it, and verify progress in
  the web app plus one native or GPodder-compatible client when available;
- verify OPML export and re-import behavior without duplicating subscriptions;
- verify the episode path is in the PinePods shared subtree and outside PBS;
- run a current logical dump, isolated restore, database checks, and an
  application query against the restored copy;
- verify application latest/WUD enrollment and database/cache exclusions;
- verify direct health, logs, UID/GID, mounts, DNS, private HTTPS, Homarr,
  recent backup state, bootstrap dry-run, focused verifiers, and
  provision/verify.sh;
- verify Audiobookshelf audiobook playback and all earlier book/Storyteller
  paths still pass.

Do not delete old podcast files, Audiobookshelf state, databases, volumes, or
images. Do not start a routine on-demand PBS backup. Record migration limits,
first-run client actions, rollback, and exact evidence. Commit and push the
completed phase, sync the intended commit to affected guests, and leave live
state traceable to Git.
```

## Part 6 of 6 — Aurral, Soularr, Navidrome, and full convergence

```text
Implement part 6 of 6 of the books/audiobooks/podcasts/music pipeline in
/Users/rafael/Repos/dothomelab.

Read AGENTS.md, the homelab-operator skill,
docs/media-pipeline-plan-2026-07-25.md, every prior phase evidence document,
and current official Aurral, Soularr, slskd, Lidarr, and Navidrome
documentation. Inspect live CT102/CT112, media mounts, existing Lidarr,
Prowlarr, download clients, slskd, DroppedNeedle, Jellyfin, SMB, NPM, WUD,
backups, and host resource headroom before changing anything. This is both the
music implementation and the final convergence gate for all six phases.

Fixed ownership model:

- Lidarr is the sole owner/organizer of the permanent music library.
- Prowlarr with qBittorrent/NZBGet is one acquisition route.
- Soularr with slskd is the Soulseek route into Lidarr.
- Aurral is the discovery/request surface and owns only its appdata plus a
  separate optional flow library.
- Navidrome and Jellyfin read the permanent library; Navidrome may also read
  the separate Aurral flow library.
- DroppedNeedle must not remain a competing writer to the permanent music
  root after the new path is accepted. Preserve its appdata and rollback
  Compose; do not delete it.

Required implementation:

1. Revalidate all current upstream images, stable rolling tags, required
   mounts, API compatibility, ports, health endpoints, path mappings, and
   upgrade notes. Use upstream application :latest/rolling stable channels
   for Aurral, Soularr, Navidrome, and slskd when officially published and
   compatible with the accepted pipeline. Enroll eligible applications in
   backup-gated WUD with digest watching and meaningful sequential checks.
2. Add three separate repository-managed projects:
   hosts/apps/aurral on CT112, hosts/servarr/soularr on CT102, and
   hosts/apps/navidrome on CT112. Give each its own Compose file, prepare,
   verify, README, appdata, least privilege, health checks, resource bounds,
   bootstrap/deploy integration, recovery docs, and no secrets in Git. Keep
   any application-private supporting containers in the owning application's
   Compose project and private network; do not create a combined music stack.
3. Keep Soularr on CT102 with Lidarr and the existing download/media
   automation. Keep Aurral and Navidrome on CT112. Update inventory,
   bootstrap, guest deployment order, expected project/container counts, and
   the media-contract verifier to reflect those fixed placements. Soularr's
   appdata must be writable through CT102's existing /docker mount, not
   expected from CT112. Do not broaden either guest's mounts or add a new
   guest.
4. Give Aurral read-only visibility of the permanent music library and
   read-write access only to its separate flow/download root. Connect it to
   Lidarr and the selected discovery/listening integrations using secrets from
   /root/.env. Main-library requests must go through Lidarr.
5. Give Soularr only the config, slskd-download, and API access current
   upstream requires. Soularr on CT102 must use CT102's existing read-write
   /data view; slskd remains its independent project on CT112 and is reached
   over its private API. Verify that Soularr/Lidarr's CT102 download path and
   slskd's CT112 /slskd-downloads path resolve to the same
   /vault/shared/media/slskd host tree, and configure the current upstream
   path mapping accordingly. Do not add a mount or let Soularr write the final
   library directly.
6. Reconcile slskd from its old DroppedNeedle-specific pinned version to the
   current upstream latest stable channel only after a task-specific rollback
   is ready and Soularr compatibility is proven. Add an active-transfer/import
   guard so WUD does not replace slskd or Soularr mid-job. Preserve Soulseek
   identity, authentication, shares, appdata, and current download files.
7. Validate the new path while DroppedNeedle remains available. After a real
   Soularr-to-Lidarr import passes and the user-facing Aurral flow is accepted,
   remove DroppedNeedle from normal startup/active library writing so a clean
   bootstrap cannot recreate two permanent-library owners. Preserve its
   Compose/appdata/images for rollback and document the exact re-enable
   command. Do not delete anything.
8. Deploy Navidrome with appdata for its database/cache/config, the canonical
   music root read-only, and the Aurral flow root read-only if enabled. Use the
   official latest application image and backup-gated WUD. Configure Subsonic
   clients without committing credentials.
9. Add private aurral.rafael.media and navidrome.rafael.media NPM routes with
   authentication, wildcard certificate, LAN/Tailscale ACL, required
   WebSockets/headers, and Homarr entries. Soularr needs no externally exposed
   route unless current upstream provides a necessary authenticated UI; keep
   it private if added.
10. Preserve Jellyfin's read-only scan of the same permanent music folder and
    the existing authenticated SMB Media share for Kew. Do not grant either
    writer ownership.
11. Add all environment placeholders, secret initializers, WUD runner checks,
    busy guards, expected container/project counts, bootstrap order, recovery
    classification, verification, and phase evidence. Record that music and
    Aurral flow files remain outside the PBS appdata backup.

Music acceptance:

- run docker compose config before every deployment;
- use user-owned, Creative Commons, or public-domain material;
- from Aurral, create a request that reaches Lidarr and completes through the
  existing Prowlarr plus qBittorrent/NZBGet route where an authorized result is
  available;
- separately exercise Soularr -> slskd -> Lidarr with a representative
  authorized album;
- verify Lidarr alone imports, renames, and places each result exactly once;
- verify no DroppedNeedle or Aurral write occurred in the permanent root;
- verify Navidrome scans and streams the result through its direct and private
  HTTPS routes and Subsonic API; test Feishin if a client is available;
- verify Jellyfin sees/plays the same library read-only and Kew can read it
  through the existing SMB mount if the Mac client is available;
- create and serve one Aurral flow in its separate Navidrome-visible library,
  and prove it did not pollute Lidarr's permanent root;
- verify slskd auth/connectivity/share/search/download, Soularr state, path
  mapping, hashes, permissions, health, logs, WUD busy/update behavior, and
  rollback.

Final convergence acceptance:

1. Rerun every focused prepare/verify script from parts 1-6.
2. Rerun one representative ebook request/import/BookOrbit scan.
3. Rerun one representative audiobook request/import/Audiobookshelf scan.
4. Rerun Storyteller reconciliation idempotently and verify one aligned
   readaloud plus one safely rejected ambiguous fixture.
5. Refresh/play/resume one PinePods episode and verify current logical dump
   plus isolated restore evidence.
6. Verify every new route resolves through Pi-hole to NPM, is private to
   LAN/Tailscale, has valid HTTPS, and has no public exposure.
7. Verify all application rolling images are backup-gated, all
   databases/caches are major-pinned and excluded, active jobs block unsafe
   replacement, pruning is disabled, and WUD still runs only after a
   successful scheduled appdata backup.
8. Run bootstrap.sh --dry-run and provision/verify.sh, validate counts,
   mounts, appdata location, shared-data exclusions, DEPLOYED_COMMIT, Homarr,
   and recovery documentation.
9. Confirm all unrelated services and native services remain healthy.
10. List remaining device-only sign-ins or acceptance choices. Do not call an
    unperformed client test successful.

Do not run a routine on-demand backup, prune images/volumes, delete old
databases/appdata/media, expose services publicly, or retire Kavita/Readarr/
Audiobookshelf data without recorded acceptance. Preserve all rollback
artifacts. Finish the complete plan and final evidence, commit and push all
completed changes, synchronize the intended commit to every affected guest,
and leave the clean-build repository capable of reproducing the accepted
pipeline.
```

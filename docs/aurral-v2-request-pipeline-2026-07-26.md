# Aurral v2 request-pipeline repair — 2026-07-26

## Scope and diagnosis

Live inspection found Aurral `1.76.51` configured with
`integrations.lidarr.searchOnAdd=false`. Aurral 1.x synthesized its Requests
page from Lidarr queue/history and did not retain its own request records.
Consequently the newly requested albums were successfully added to Lidarr but
never searched and did not appear in Aurral:

- Elvis Presley — `35 Hits`, Lidarr album ID `1311`
- Toto — `Fahrenheit`, Lidarr album ID `1318`

Lidarr also retained 23 terminal queue records with `status=completed`,
`sizeleft=0`, and `trackedDownloadState=importFailed`. Those records included
old downloads and were rendered by Aurral 1.x as current `Available` or
`Downloading` requests.

The previous Aurral container had its own generated Soulseek identity.
Upstream v2 removes that built-in client in favour of external slskd.

## Desired pipeline

1. Aurral v2 stores every album request in `aurral_history`.
2. `searchOnAdd=true` immediately starts Lidarr's normal search.
3. Lidarr searches through Prowlarr and uses its torrent/Usenet clients.
4. After a 10-minute grace period, the guarded Soularr runner reads Aurral's
   history read-only and exposes only requested album IDs from the last seven
   days to Soularr. A durable attempt ledger enforces a six-hour retry cooldown.
5. Soularr searches through the existing slskd instance and account, writes
   only the shared slskd download tree, and asks Lidarr to import.
6. Lidarr remains the sole writer and organizer of the permanent music library.

Aurral flow and playlist downloads also use the same external slskd API and
identity. Aurral has the narrow slskd download-tree write access required to
transfer its completed flow jobs, no permanent-library write access, and no
`SOULSEEK_*` environment variables.

## Safety and rollback

The Aurral image is pinned to `2.0.0-test.7` and digest
`sha256:a2ce2e4ae4767c3fb445728c3af2e972823b874c7813d290a2054b736100bbf6`;
it is excluded from WUD because v2 is a prerelease. Before live migration,
preserve a SQLite online backup and a named ZFS snapshot of canonical appdata.
Keep the v1 image locally. Rollback is to stop v2, restore the pre-migration
SQLite database (or appdata snapshot), and redeploy the prior v1 Compose
revision; never edit the migrated database by hand.

The Soularr scheduler fails closed when the Aurral database or v2 history table
is missing. `SOULARR_REQUESTS_ONLY=true` is the default and must not be disabled
until Lidarr's recovered monitoring set is deliberately curated.

`clear-stale-lidarr-queue.py --apply` removes only terminal queue metadata and
passes `removeFromClient=false` and `blocklist=false`. It does not delete a
download-client item, source folder, or media file.

## Acceptance evidence

- The scheduled appdata backup completed successfully at
  `2026-07-26 02:02:50 CEST`. The migration additionally retained SQLite online
  backup
  `/srv/appdata/docker/aurral/data/recovery/aurral-v1-pre-v2-20260726T101500Z.db`
  with `PRAGMA integrity_check=ok`, ZFS snapshot
  `rpool/appdata/docker@pre-aurral-v2-20260726T101500Z`, and the local v1 image.
- An isolated, network-disabled migration of a copied database passed before
  production: database integrity remained `ok`, `users` survived,
  `aurral_history` was created, and the v2 process ran as UID/GID `1000:1000`
  with zero effective capabilities.
- Live Aurral passed its Lidarr, external slskd, storage-transfer, Navidrome
  path, health, private HTTPS, mount, image/digest, database-history, runtime
  UID, and capability checks. No `SOULSEEK_*` variable remains on the
  container; slskd reported `Connected, LoggedIn`.
- Cleanup removed 23 initial and three subsequently surfaced terminal
  `completed` / `importFailed` queue rows. Each deletion used
  `removeFromClient=false` and `blocklist=false`; no active download matched
  the selector.
- Aurral v2 re-requested Elvis Presley `35 Hits` (Lidarr album `1311`) and Toto
  `Fahrenheit` (album `1318`) at `2026-07-26T10:29:07Z`. Both durable requests
  appeared immediately and launched Lidarr `AlbumSearch` commands `703839` and
  `703840`; both commands completed.
- The Toto search grabbed
  `Toto - Fahrenheit (2020) [FLAC 24-192]` through qBittorrent. At final
  inspection Lidarr showed the request as `Downloading` with `1,812,353,041`
  bytes remaining. It had not completed or imported, so no download/import
  success is claimed.
- The lock-protected zero-grace Soularr acceptance cycle selected the two
  recent Aurral requests, skipped Toto because it was in Lidarr's active queue,
  and searched the shared authenticated slskd service for Elvis. It evaluated
  38 peer results against Lidarr's selected 35-track release and rejected all
  non-matches. Aurral consequently showed Elvis as `Not found`; no incorrect
  files were enqueued and no import success is claimed.
- Soularr, Aurral, slskd, and the Servarr project passed focused verification.
  Soularr remains private, request-only, lock-guarded, and limited to a
  10-minute Lidarr-first grace period, seven-day request window, and six-hour
  per-album retry cooldown.

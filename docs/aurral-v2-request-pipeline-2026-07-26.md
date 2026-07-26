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
   days to Soularr.
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
it is excluded from WUD because v2 is a prerelease. Before live migration, preserve a SQLite online backup and a
named ZFS snapshot of canonical appdata. Keep the v1 image locally. Rollback is
to stop v2, restore the pre-migration SQLite database (or appdata snapshot),
and redeploy the prior v1 Compose revision; never edit the migrated database
by hand.

The Soularr scheduler fails closed when the Aurral database or v2 history table
is missing. `SOULARR_REQUESTS_ONLY=true` is the default and must not be disabled
until Lidarr's recovered monitoring set is deliberately curated.

`clear-stale-lidarr-queue.py --apply` removes only terminal queue metadata and
passes `removeFromClient=false` and `blocklist=false`. It does not delete a
download-client item, source folder, or media file.

## Acceptance evidence

Record the live migration backup name, deployed Git commit, v2 integration
tests, durable Activity rows, Lidarr search commands, stale-queue before/after
counts, request-scoped Soularr selection, slskd state, and any completed Lidarr
import here after deployment. An initiated search or peer queue is not evidence
of a completed download/import.

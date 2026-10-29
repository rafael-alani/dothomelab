# Prowlarr reconnect and Cyberpunk Season 1 retrieval — 2026-10-29

## Result and scope

Six public sources were reconnected: 1337x, EZTV, ExtraTorrent.st, BT.etree,
Torrentsome and Torrenttip. A newly accessible 1337x release supplied all ten
Cyberpunk: Edgerunners Season 1 episodes advertised as 4K. Sonarr accepted it
and qBittorrent began downloading it in `tv-sonarr`. Download completion,
actual video resolution, native-versus-upscaled provenance and the eventual
Jellyfin 4K import remain unverified.

The existing library is intact: Jellyfin's read-only catalogue contains ten
Season 1 episodes at 1920×1080 and ten Season 2 episodes at 3840×2160. Season 1
uses Sonarr profile 9, `Cyberpunk - 1080p fallback to 4K`, with upgrades enabled
and the 2160p cutoff. Both seasons remain monitored. The earlier 1080p import
preserved its source torrent and used hardlinks for all ten episodes.

Rafael explicitly limited reconnection to public indexers. Saved credentials
for BTSchool, HDClone and RailgunPT were not tested or changed. Before that
clarification, automatic approval review blocked blanket credentialed tests;
work proceeded with explicit public-indexer filters only.

Environment: PVE `afa`, CT102 Servarr, CT112 Jellyfin/Seerr; Prowlarr
2.7.0.5723. Runtime code is `11cd53e79c65acbe6a95d0d08b00279cf2abc5f3` on
`codex/stillroom-settings`, including network repair `8771037`. Both commits
were pushed and the CT102 `DEPLOYED_COMMIT` was verified. No main promotion or
application image upgrade occurred.

## Cause and repair

Prowlarr shared Gluetun's VPN namespace, while FlareSolverr used the ordinary
Docker bridge. Their public egress addresses differed. Prowlarr's
[FlareSolverr implementation](https://github.com/Prowlarr/Prowlarr/blob/develop/src/NzbDrone.Core/IndexerProxies/FlareSolverr/FlareSolverr.cs)
reuses challenge cookies and the browser user agent for its own request; the
different outbound addresses explained repeated challenge failures. Moving a
temporary solver into the VPN restored EZTV, then the permanent repair also
restored 1337x and ExtraTorrent.

FlareSolverr now shares Gluetun, exposes no direct LAN port and serves Prowlarr
at `http://127.0.0.1:8191`. Its image was unchanged. CT102's limit increased
from 4 to 6 GiB without a guest restart; FlareSolverr has a 2 GiB cap. Only
FlareSolverr was recreated; the existing Gluetun, qBittorrent, NZBGet and
Prowlarr containers continued running.

An earlier concurrent browser-test batch exhausted the old 4 GiB budget and
caused memory pressure and an OOM kill. That batch was stopped and FlareSolverr
restarted. Subsequent tests were sequential. Final memory use was about
3.4 GiB, with memory-pressure averages at zero over the latest 10 and 60 seconds.
The Compose, inventory, verifier and reconciliation policy now preserve this
network arrangement and the recovered indexers.

| Public source | Change and evidence |
|---|---|
| 1337x | Enabled at `https://1337x.to/`; Prowlarr and Sonarr tests passed; returned the Season 1 candidate |
| EZTV | Enabled with the shared VPN solver; Prowlarr and Sonarr tests passed |
| ExtraTorrent.st | Enabled with the shared VPN solver; Prowlarr and Sonarr tests passed |
| BT.etree | Added the solver tag; Prowlarr test passed; this is a music source |
| Torrentsome | Replaced dead `torrentsome205.com` with schema-supported `torrentsome270.com`; added solver tag; Prowlarr test and actual TV query passed |
| Torrenttip | Replaced dead `torrenttip186.top` with schema-supported `torrenttip250.top`; added solver tag; actual TV query returned four matching results; its existing Sonarr entry remains enabled |

Torrenttip's generic Sonarr connection test returned no recent releases in its
configured categories, but its actual TV search succeeded. Torrentsome is
searchable in Prowlarr; no corresponding Sonarr entry was observed, so automatic
Sonarr coverage for that source is not claimed.

Remaining public limits: ACG.RIP and EBookBay failed TLS; Magnet Cat failed on
its main and a supported alternate URL; Torrent[CORE] still failed through the
solver. Torrent Downloads passed a generic Prowlarr test but returned no TV
results, and its alternate mirror timed out; it remains disabled. Internet
Archive passed its initial connection test but timed out on this title search
and retained a health warning. Four intentionally disabled public definitions
remain in the policy. Private-tracker health warnings were left untouched.

## Season 1 retrieval

The repaired public search queried eleven enabled public TV sources explicitly;
it did not invoke a Sonarr search that could contact private trackers. The
[Tenrai-Sensei release](https://1337x.to/torrent/6558211/Tenrai-Sensei-Cyberpunk-Edgerunners-BD-4k-HEVC-10bit-x265-Dual-Audio/)
lists `S01E01` through `S01E10`, English/Japanese audio and a Season 1 trailer.
qBittorrent's actual metadata independently confirmed those ten episode paths.
The torrent is about 19.8 GB, hash
`a759f18cc838b14683703afe8abbda08cb82728a`.

The release title omitted the season number and Sonarr could not parse it.
Adding the verified `S01` label and spelling its advertised `4k` as `2160p`
mapped it to series 56 and exactly ten Season 1 episodes. Sonarr initially
rejected nine advertised seeders against its threshold of ten. A scoped,
temporary change to that public indexer's threshold allowed the explicit
request; the normal threshold of ten was immediately restored and verified.
No seed counts or episode contents were fabricated.

Sonarr's queue tracks the torrent against Season 1 with download status OK.
qBittorrent reported active transfer with one connected seed. This establishes
that retrieval started, not that 4K is already available in Jellyfin. The
existing 1080p files remain the playback fallback. The previously misidentified
NEST Season 2 release remains blocklisted for the Season 1 request, with its
downloaded files retained.

## Verification and retained state

- Python syntax, proxy reconciliation self-check, shell syntax and quiet live
  Compose validation passed. The documentation checker and whitespace check pass.
- Full Servarr verification passed: all 13 declared containers, VPN namespace,
  qBittorrent VPN binding, application endpoints, persistent database counts,
  23 supported configured indexers, eight solver tags and shared-data mounts.
- Pulse verification passed for all LXCs and Docker guests 102/110/112/114/115.
  Existing Homarr links for Prowlarr, Sonarr, qBittorrent and Jellyfin returned
  HTTP 200. FlareSolverr is an internal dependency without a new dashboard tile.
- No service or download data was deleted. The temporary solver container,
  temporary Prowlarr proxy/tag and disposable search transport files were removed.
  CT114/115 build caches measured 21.07/9.7 GB; unrelated caches were not pruned.
- Operator-owned audit records remain in
  `/srv/appdata/docker/prowlarr/operations/reconnect-2026-10-29/`, including
  before/after public settings, sanitized tests, search results and retrieval
  decisions. Retain until the new download/import and the repair are accepted.
- The anonymous `/config` volume from the temporary solver is retained:
  `0fef72f3b137dfd86589a8f9da6057b710dfbc8b3fa1d62a61d0c093d197f82b`.
  Its owner and review-before-authorized-deletion condition are in `probe.json`;
  no running container uses it.

PVE recovery branch `codex/recovery-prowlarr-20261029` retains pre-operation
checkout `db2f54f33797f0cb63879a1ca7f4a4a5527f230b`. CT102 retains the original
deployed archive at `/opt/dothomelab.previous.20261029T153323.2080258`
(`a4f1374`), the earlier archive at
`/opt/dothomelab.previous.20261029T151012.2045790` (`974c2899`), and the first
repair at `/opt/dothomelab.previous` (`8771037`). These operator rollback
artifacts remain until acceptance and explicit cleanup authorization.

Rollback requires restoring the prior Compose/proxy arrangement together,
including proxy host `http://flaresolverr:8191`, and public settings from the
audit records. Validate Compose quietly before recreating FlareSolverr. Reduce
the guest memory limit only after resolving browser memory pressure. The
02:24 scheduled appdata backup succeeded; no new backup or restore test ran.
Shared media is outside that appdata backup. No recovery claim exceeds these
retained code/configuration records and preserved media files.

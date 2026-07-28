# Prowlarr indexer repair — 2026-07-28

## Observed failure

Prowlarr was healthy as a container, Gluetun's native health check passed, and
representative failed domains resolved through the VPN. The red dashboard was
therefore not a Prowlarr, VPN-tunnel, or DNS outage.

Read-only database and API inspection found 32 enabled indexers. Prowlarr's
health API reported:

- nine configured Cardigann indexers whose definition IDs were absent from the
  complete live schema catalog;
- fourteen indexers in long-term failure backoff;
- Prowlarr 2.4.0.5397 was behind available 2.5.2.5491.

The exact unsupported public definitions were `badasstorrents`, `bitsearch`,
`glodls`, `idope`, `nyaapantsu`, `solidtorrents`, `therarbg`, `torlock`, and
`yourbittorrent`. None appeared in the 625-resource Prowlarr 2.4 schema catalog
or after the 2.5.2 update. Prowlarr itself instructed that those configured
entries had no definition and would not work.

Recent sanitized logs classified the remaining repeated failures as
Cloudflare protection, one HTTP 403/1006 response, and an invalid TLS
certificate at EBookBay. FlareSolverr was healthy, but three
Cloudflare-protected definitions lacked the proxy's matching tag.

## Rollback and update

The scheduled appdata backup completed successfully at 02:16 CEST. Before
changing Prowlarr, an online SQLite backup plus the exact `config.xml` was
created mode 0600 under:

```text
/docker/prowlarr/Backups/codex-manual/20260728T1918Z
```

Only Prowlarr was pulled and recreated after `docker compose config --quiet`.
Gluetun, qBittorrent, NZBGet, the Arr applications, and FlareSolverr remained
running. Prowlarr started healthy on 2.5.2.5491 with SQLite migration 44. The
prior and replacement image IDs remain available locally for rollback.

## Reproducible repair

`hosts/servarr/hello/reconcile-prowlarr-indexers.py` now fails closed and:

- deletes only the nine exact public name/definition pairs confirmed absent
  from the current schema catalog;
- refuses to delete an unexpected unsupported definition;
- never lists a private tracker as an automatic deletion target;
- applies the existing `flaresolverr` tag to the five exact supported public
  definitions observed behind Cloudflare;
- retains but disables seven supported public entries that failed bounded live
  acceptance, instead of deleting their configuration;
- offers explicit, non-persistent tests only when an operator names an indexer
  or a Prowlarr-declared base URL.

Bootstrap runs the reconciler after deploying the Servarr Compose project.
The focused Servarr verifier rejects future unsupported definitions, missing
FlareSolverr tags, or re-enabled entries from the confirmed-unavailable set.
External indexer availability is deliberately not a general bootstrap gate.

## Live acceptance

The initial explicit Prowlarr tests covered only the nine public entries still
listed in the long-term/current failure health checks. Targeted retests then
verified the repaired FlareSolverr scope and one declared alternative for each
definition that offered a plausible current mirror. No private tracker login
or CAPTCHA test was repeated.

ACG.RIP and Internet Archive passed end to end. Torrent Downloads passed one
direct Prowlarr test but then returned HTTP 429 to all four downstream Arr
validation requests, so it was also retained disabled. Seven supported public
entries failed bounded acceptance:

| Retained disabled | Evidence |
|---|---|
| 1337x | configured URL and one declared alternative failed; HTTP 403/1006 / Cloudflare |
| EBookBay | only declared host failed certificate validation |
| ExtraTorrent.st | configured URL and one declared alternative failed after FlareSolverr |
| EZTV | configured URL and one declared alternative failed after FlareSolverr |
| Magnet Cat | configured URL and one declared alternative failed after FlareSolverr |
| Torrent[CORE] | only declared host failed after FlareSolverr |
| Torrent Downloads | direct Prowlarr test passed; Sonarr, Radarr, Lidarr, and Readarr validation each returned HTTP 429 |

Final live state:

- Prowlarr health API returned zero entries;
- 23 indexers remain configured: 16 enabled and seven retained disabled;
- BTSchool, HDClone, and RailgunPT remained enabled and were not tested;
- the unsupported-definition count is zero;
- all five declared Cloudflare targets carry the FlareSolverr tag;
- Prowlarr, Gluetun, FlareSolverr, qBittorrent, NZBGet, Sonarr, Radarr, Lidarr,
  and Readarr are running and healthy.

All public-indexer warnings also cleared from the Sonarr, Radarr, Lidarr, and
Readarr health APIs after the retained-disabled policy synced. Sonarr still
reports a BTSchool proxy failure; the Prowlarr BTSchool resource itself remains
enabled without a current Prowlarr health error, and this repair deliberately
did not repeat the user's manual private-tracker login/CAPTCHA test. Readarr
also retains its unrelated pre-existing qBittorrent gateway warning at
`172.18.0.1:8080`.

The disabled entries can be re-enabled after a future explicit test passes.
To roll back the complete Prowlarr state, stop only Prowlarr, preserve the
current database/config, restore the two files from the manual rollback
directory as UID/GID 1000:1000 and mode 0600, and start Prowlarr on the retained
prior image.

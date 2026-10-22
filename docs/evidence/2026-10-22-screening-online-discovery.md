# Screening online discovery — 2026-10-22

The prior catalog-only pilot returned `data:[]` for **At Eternity's Gate**.
It never queried an online source. The staging screening path now resolves
uncatalogued film metadata through Wikidata and can query OpenSubtitles for
English subtitle releases after the user selects the film. Jellyfin is optional.
This closes metadata discovery and the application handoff; live transcript
retrieval remains pending the owner's dedicated OpenSubtitles application key.

## Installed revisions

| Component | Commit |
|---|---|
| Film-introspect | `566d22c4183499e0bf45ef4c66972147756d4789` |
| Meta Egg | `f95343b748380b1d4a16e44290afc96c198eda3b` |
| Homelab runtime archive | `1ed87e0056414594f353c86c3eb5dd9807f86ec5` |

The application `staging` branches were advanced without changing main.
Homelab configuration is on `codex/screening-mvp-staging`. The old guest archive
is retained at `/opt/dothomelab.retained-a6485b1-before-discovery`; the earlier
`/opt/dothomelab.previous` was not deleted. App release and independent data
generations are retained by the deployer. No schema or production integration
was changed. The committed PVE setup archive is
`/root/dothomelab-screening-discovery-1ed87e0`.

## Verification

On the operator Mac and private CT114 preview:

- Original assertion failed against the old staging API with an empty film list.
- The same query now returns only `wikidata-Q47006131`, **At Eternity's Gate**,
  year **2018**, runtime **6600 seconds**. The same-title painting is excluded.
- The Film-introspect API proxy and native browser both return this result.
  Selecting it retains metadata and reports `transcriptStatus:not_configured`;
  cut selection and Open screening remain disabled. Repeating the same query
  produces a selectable result again.
- The existing Sintel catalog identity and transcript still return **26 cues**,
  beginning at **107.25 seconds**. No alternate transcript was substituted.
- Pre/post deployment totals match: **2 timelines, 1 note**. This checks counts,
  not every stored value; the deployer additionally passed SQLite integrity.
- Both app verifiers passed, containers were healthy, `DEPLOYED_COMMIT` matched,
  and the staging poller timer remained active. Compose was validated before
  each rollout. Unrelated applications were not redeployed.

Meta Egg passed 55 tests, including 11 discovery tests, typecheck, lint,
boundaries, formatting, production build, and two compiled smoke tests. Tests
cover the screening HTTP seam, film/subtitle identity, key absence, auth/quota
failures, split/partial-track exclusion, malformed data, and download-host
validation. A real Wikidata request from the implementation also passed.
Film-introspect passed 20 tests, discovery/catalog/Jellyfin HTTP+SQLite smoke
modes, typecheck and build. Its exact Bun build ran from a disposable temporary
copy because macOS restricted Bun ancestor-directory access in the working
folder; the actual Docker build subsequently passed on CT114. Homelab's scoped
environment tests (3), deployment tests (9), documentation checks and diff checks
passed. Provider test subtitles are synthetic fixtures, not the commercial film.

## Remaining acceptance and recovery

No dedicated `STAGING_META_EGG_OPENSUBTITLES_API_KEY` was present. Only its
presence was checked; no unrelated production token was reused. The initializer
now passes this dedicated value only to Meta Egg. The owner must obtain a key
through [OpenSubtitles consumers](https://www.opensubtitles.com/en/consumers),
store it in PVE `/root/.env`, render Meta Egg's environment and redeploy as
specified in the [staging runbook](../../hosts/staging/README.md#meta-egg-screening-api).

A valid matching subtitle for this film, live provider authentication/download
quota, exact release alignment, and full-screening clock drift remain unverified.
Metadata alone cannot establish any of them. English single-file whole-film
tracks are the MVP scope; source release/FPS labels do not identify a cinema
cut. Discovery caches are bounded process memory and reset on restart, not
canonical database ingestion. No full movie was downloaded. No new backup
restore or clean-host rebuild was performed.

# Personal Jellyfin settings — 2026-10-22

Scope: Film-introspect and Meta Egg private staging on CT114. Homelab policy
applies credential ownership to every staged project. No production service,
provider key, user account, media mount, DNS or authentication mode changed.

## Delivered behavior

Film-introspect accepts a server URL and API key/access token in Settings,
validates before saving, and stores AES-256-GCM ciphertext per app user in its
SQLite data generation. Saved keys are never returned. Replacement failure
preserves the working credential; disconnect retains notes. Personal-token
ownership is resolved through Jellyfin, while server API keys keep their broader
permissions. A server's name selects the Jellyfin flow, exact media versions and
optional device following. Any screen retains manual alignment and external
subtitle discovery. Timeline identity includes the selected server.

OpenSubtitles stays service-wide: the existing scoped value from PVE `/root/.env`
is supplied only to Meta Egg. Settings reports configuration, not the key or
hosting details. Meta Egg handles personal Jellyfin credentials per request
without persisting them or sharing a global provider cache.

## Verification

- Meta Egg staging `d14144535284b12231d37bcc4cb95abd6c9a958c`: 62 unit/contract
  tests, typecheck, lint, boundaries, build and two compiled loopback smoke tests
  passed. The installed container's staging deployment was accepted healthy.
- Film-introspect final candidate `195150720c319ead89ba9bc7b12f18d48b0159c5`:
  24 tests, typecheck/build and isolated catalog, discovery and Jellyfin workflow
  checks passed. Tests cover owner-bound encryption, distinct user/server/cut
  timelines, secret-free responses, invalid connection rejection, failed
  replacement preservation, source isolation, disconnect, and existing notes.
  Remote staging HEAD matches the installed revision; the deployer accepted
  both containers healthy and the final HTTPS Settings walkthrough passed.
- Browser review covered Settings and named-server subtitle selection at 1280
  and 390 px using an explicitly labeled synthetic fixture. Mobile heading
  clipping was corrected. A connection-discovery error/retry state was added
  after the independent interface review. Browser retry restored the saved
  fixture server; the reviewer scored that fix resolved with disposition ship.
  The design documentation pass confirmed an ordinary extension of the existing
  interface; no new design system was introduced. Its stale connection-guide
  index entry was corrected in the final documentation-only commit.
- Live HTTPS Settings reports OpenSubtitles configured and Jellyfin unconfigured.
  At Eternity's Gate (2018) returns six available subtitle releases; its saved
  YTS English transcript opens and the existing 1:17 note remains after upgrade.
  This does not prove a fresh provider download or remaining quota.

## Limits and rollback

No Jellyfin credential was supplied or extracted from production. Live Jellyfin
validation, real device following and perceptual sync await a key entered in
Settings. Fixture success is not live integration acceptance. Staging still uses
one shared Local viewer; separate account isolation requires authentication to
be enabled. No user acceptance or promotion to main occurred.

The deployer validated Compose, retained previous images/environments and copied
independent data generations before cutover. The credentials migration adds a
table; older binaries can ignore it. Preserve current notes on rollback instead
of restoring old data indiscriminately. Restoring encrypted keys requires the
matching Film-introspect auth secret; rotation requires reconnecting or an
explicit re-encryption migration. No PBS backup or restore rehearsal was run.
CT114's homelab archive remains `c86e422e80cb1461c0127737927479dd4e1b931f` because
this task needs no homelab runtime changes; homelab changes are policy/runbook
and evidence only.

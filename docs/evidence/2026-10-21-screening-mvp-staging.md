# Screening MVP staging — 2026-10-21

Focused work on PVE `afa`, CT114 and CT110, with local browser checks on the
operator Mac on October 21 (Europe/Amsterdam). The intended workflow is movie
lookup in Film-introspect → choose the available cut/subtitle → follow the film
clock → hold a timestamp while writing → save and catch up to the current
subtitle. [User workflow](../../USER_DOC.md#take-notes-during-a-screening) and
[deployment contract](../../hosts/staging/README.md#meta-egg-screening-api).

The private preview is deployed, but real-library acceptance is **incomplete**.
Meta Egg has no Jellyfin credentials yet. A working process and the synthetic
local note test do not establish movie lookup, matching subtitles or clock
synchronization against the user's actual screening.

## Revisions and deployment

| Component | Observed revision / state |
|---|---|
| Homelab staging declarations | `53f00428066c9334a82c947f21b9c85ef3bc64e5`, branch `codex/screening-mvp-staging` |
| CT114 archive during application verification | `53f00428066c9334a82c947f21b9c85ef3bc64e5` |
| Restricted-account helper | `92b30e31c5ad84cf690de2f54a838d19510ef6c9`, published; not invoked against Jellyfin |
| Meta Egg | Installed and verified staging `ab831792295a7e69edf9c1c49e8f8e9929ab84d7` |
| Film-introspect | Installed and verified staging `df260de9b5a58a1f50a20404e763d8e9d8b9f53a` |

App candidates remain on their `staging` branches. No `main` promotion or user
acceptance is claimed. The isolated PVE checkout used for the initial sync is
`/root/dothomelab-screening-mvp53`; PVE's existing `/root/dothomelab` checkout
at `2801876c` was left in place. Existing FF, Stillroom, Blog and lifecycle
registrations are retained in the new CT114 archive. The final archive sync uses
the complete committed evidence release on the same homelab branch; the table
records the earlier archive marker observed during application verification.

## Access and data boundary

- [Film-introspect](https://film-introspect.staging.rafael.media) remains the user
  entry point on CT114 port 8080. Its server calls Meta Egg; Jellyfin credentials
  are not supplied to the browser or Film-introspect runtime.
- [Meta Egg](https://meta-egg.staging.rafael.media) binds CT114
  `192.168.0.114:8085`. Its `SCREENING_ONLY=true` deployment is stateless and has
  no data/media mounts. Only root/health and read-only screening API routes are
  intended for this preview; unrelated mutation endpoints are disabled.
- The Meta Egg repository is private. Its dedicated GitHub deploy key
  (ID `167234708`) is read-only, retained under canonical staging appdata at
  `meta-egg/git`, and uses pinned GitHub host keys. It is not mounted in the app.
- The committed route reconciler configured the exact Meta Egg DNS/private NPM
  route using the existing staging certificate and LAN/Tailscale restriction.
  Existing routes were retained. A fresh NPM SQLite backup passed integrity
  verification at
  `/srv/appdata/docker/infra-nginx-proxy-manager/database.sqlite.pre-meta-egg-20261021`.
  No public application DNS or router change was requested.
- Only `STAGING_META_EGG_JELLYFIN_URL`, `STAGING_META_EGG_JELLYFIN_API_KEY` and
  `STAGING_META_EGG_JELLYFIN_USER_ID` are rendered to Meta Egg. Its prospective
  recovery password remains host-only. Empty credentials remain an unavailable
  connection; the real-library path does not silently become demo acceptance.
- The original live Film-introspect note count was **0**. Existing legacy
  direct-Jellyfin records remain separate and unmerged; this is not a completed
  migration of historical data. The existing SQLite release-generation and
  rollback mechanism remains in use.

## Checks and their limits

- Registry validation, nine staging deploy tests, three scoped-environment tests,
  the retirement guard test and repository documentation checks passed locally.
- Six no-network account-initializer tests passed: movie-only restrictions,
  saved ownership/identity, recovery after a lost create response, token reuse,
  scoped atomic environment updates, changed-server rejection and secret-safe
  redirect/error handling. These tests used fixtures; no live account was made.
- Film-introspect reported 15 passing application tests, typecheck/build/format
  checks, and a delayed 16-second upstream-response smoke check. These are local
  application checks.
- Final `deploy.py --verify` passed for all five registered apps. Meta Egg and
  Film-introspect ran the exact source commits in the table; all six containers
  were healthy, the branch timer remained active, and FF/Stillroom/Blog retained
  their earlier commits.
- Meta Egg and Film-introspect health endpoints returned 200 over trusted HTTPS.
  Film-introspect's real search reached Meta Egg and returned an explicit
  connection-unavailable message (Film HTTP 502 for Meta Egg HTTP 503). This
  verifies the service link and failure message, not real movie/subtitle access.
  No administrator credential or fallback demo was used to make search pass.
- A local browser fixture held a note at **1:55**, allowed the independent clock
  to advance to **2:15**, saved the note with **1:55**, and caught the subtitle
  view up to the advancing clock. That fixture was local only and was not
  deployed to staging. It proves the tested note interaction against synthetic
  data, not timing accuracy for a real movie or Jellyfin client.

## Required follow-up and rollback limits

Automatic approval review blocked access to the existing Jellyfin administrator
credential for dedicated-account provisioning. Explicit user approval remains
pending. No credential was extracted for this step and no production-wide key
was injected into staging. The concrete next action is to use that credential
once on PVE, through an owner-only token file, to provision hidden non-admin
`meta-egg-staging` with the maintained initializer. Its policy grants the movie
libraries and readable media/subtitles while disabling administration, deletion,
downloads, management, remote control, sharing, live TV and transcoding. Only the
resulting restricted user token belongs in the staging runtime.

After authorization/configuration, exercise an actual movie and available cut,
load a matching text subtitle track, align the manual clock or a visible Jellyfin
session, save a note while the film continues, and confirm both its retained
timestamp and return to the live subtitle. Image-only subtitle tracks, unavailable
cuts and sessions not visible to the restricted account must be reported as
integration gaps. Manual alignment is required when the screening's player
cannot provide its clock. This real-media check and Rafael's preview acceptance
remain outstanding; neither a successful build nor the synthetic test replaces them.

Prior source bundles, images, guest archives and Film-introspect data generations
were retained; no volume or rollback cleanup was performed. Meta Egg is stateless.
A Film-introspect code revert should use current data; restoring a previous
SQLite generation can discard notes created since that release. Restore only the
owned NPM route if later configuration has changed, because restoring the whole
NPM database could discard unrelated updates. Preserve the dedicated credentials
and ownership record for retry; the account can be disabled to withdraw access.
No new PBS job, clean-host restore, shared-media recovery test or external-network
denial probe was run.

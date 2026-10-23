# Blog picnic sky and private audio — 2026-10-23

## Scope and result

Rafael requested a reclining picnic character at the lower right, falling stars
with moving reflections/comet tails and lake splashes, a scene-only star cursor,
thicker constellation connections, and a persistent Currently enjoying player.
The application candidate is `0907f6a4a1f36b062d57c1e8dba5e3c34ca3fb70` on both
`rafael-alani/blog` branches `codex/picnic-sky` and `staging`.
[Private review](https://blog.staging.rafael.media) runs that exact commit.
Main promotion remains subject to Rafael's acceptance.

## Audio and ownership

No Vincent/Don McLean filename was found under `/vault/shared/media/music`.
The authorized test track is **Freedom Overspill — Steve Winwood**, from the
Back in the High Life album. The player identifies the actual track and labels
it as a preview; Vincent remains pending. The verified copy has SHA-256
`f60cdd679714175ba72b04c2fa20d9d05e5cca01a0b5adb0105dee49d51719c9`.

`hosts/staging/blog/stage-listening.py` copies that single selected MP3 into
`/srv/appdata/docker/staging/blog/listening/f60cdd679714` and writes `track.json`.
The container mounts only that directory read-only at
`/usr/share/nginx/html/listening`. No canonical-library mount, credentials,
production-file mutation, audio in Git, or public exposure was introduced.
The deployment contract is on `codex/blog-picnic-infra`, initially `9ce3e07`;
`3b676a5` adds a retained integrity/idempotence/no-overwrite regression check.
The [staging runbook](../../hosts/staging/README.md#blog-picnic-music-preview)
owns the ongoing procedure.

## Verification

On the operator Mac, Node 26.9.0: application type checking, all 37 unit tests,
production build, and 24 default Chromium cases passed. Three analytics cases
were skipped. An initial five-worker suite had one navigation timeout; the
focused rerun and full two-worker suite passed. Captures show the moving comet
and reflection, splash/ripples, picnic placement, and desktop/phone player.
The design scan found no matches. The homelab helper test and docs checker pass.

On PVE/CT114, the normal staging runner validated Compose quietly, built the
candidate before cutover, retained the previous release, and accepted a healthy
container. Read-only `deploy.py --app blog --verify` and the container commit
label confirmed `0907f6a4a1f36b062d57c1e8dba5e3c34ca3fb70`.
The blog has no SQLite database; the verifier's generic integrity message does
not indicate a new database integration.

Two opt-in HTTPS browser cases passed against the actual private deployment:
play/pause, real MP3 duration and advancing time, keyboard seek, mute, playback
continuity across scene navigation, one persistent Canvas, and 390 × 844 phone
layout without horizontal overflow. The app browser independently displayed
both the picnic scene and the real 5:37 song controls. These checks are in
`blog/tests/e2e/picnic-live.spec.ts`, enabled with `BLOG_PREVIEW_URL`.

## Rollback and limits

The previous accepted blog revision `ccba873e4e287c69258811ac4fdebd68edc16a23`
is retained under release `1792791274759970530-ccba873e4e28-e4a2020bce5c`.
Earlier release definitions without the listening mount also remain retained.
Restore the intended release/image/Compose together or push an application
revert to staging. Preserve the immutable selected-audio directory for any
release still using it; removing it requires a separate retention decision.

Guest repository archives were preserved before synchronization, including
`/opt/dothomelab.rollback-before-picnic-20261023`. No rollback rehearsal, new PBS
job, clean-host restore, physical phone or non-Chromium verification occurred.
The original music library remains outside appdata PBS; the small staging copy
uses the existing scheduled appdata policy. This does not establish a library
backup. The primary local dothomelab checkout's unrelated changes were preserved.

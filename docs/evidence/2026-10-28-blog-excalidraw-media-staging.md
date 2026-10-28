# Excalidraw image and PDF crop preview — 2026-10-28

The [diagnosed missing media](2026-10-28-blog-excalidraw-embedded-media-research.md)
is implemented and deployed on private staging. Blog
`432388fc87298dd0eadf985d879d8ccd113bce66` is published on `origin/staging`.
Production and `origin/main` remain at
`80238c963cf99d860bbd5ccb3da6a17002370101`; this task did not authorize a
production code release. The earlier menu fix `5035ebe` was already on staging
when this candidate was published and remains included.

Review:

- [Probabilistic AI and Reasoning](https://blog.staging.rafael.media/technical-write-ups/ai/probabilistic-ai-and-reasoning)
- [Deep Reinforcement Learning](https://blog.staging.rafael.media/technical-write-ups/ai/deep-reinforcement-learning)

## Behavior and publication boundary

The exporter retains the Embedded Files entries used by visible drawing images
and follows their source attachments even without a clickable link. PDF fragments,
source overrides and native crop metadata survive. Those dependencies join
normal cache invalidation and draft/published selection. Missing image sources
fail before replacing a complete export.

The blog builds pixels with pinned PDF.js 6.4.299 and native canvas 1.0.10.
It distinguishes a source PDF rectangle from the element's navigation link;
native crops use their stored raster dimensions and become independently keyed
derivatives with the exported native crop cleared. Position, size, layering,
rotation and PDF click targets remain authored values. PDF derivatives are
lossless WebP; separate hashed raster assets keep pixels out of collection JSON.
The full PDF is retained publicly only when also explicitly linked or embedded.
Existing self-contained image data remains supported. SVG stays inline for
the viewer's existing normalization. Invalid media fails the build.

The exporter normally feeds staging and production together. To keep this review
private, homelab implementation `f745317a1c687d05bf11c434e1692550f58afeb8`
adds an isolated review export and staging-only input selection, documented in
the [native runbook](../../hosts/blog/README.md#review-exporter-changes-privately).
CT110's active exporter was not replaced or restarted. Its installed source
SHA-256 remains `6928f7c876a74ebedc43202837de00674067f4643e99837f07892546f835dba6`.
The production editorial pointer and installed release remained unchanged at
the final check.

Staging uses immutable review snapshot
`16848a8b01b6090a4cb13ed3c15b3f0dc63cc36d885bec67cfed8ab4b6772533`, with
13 preview entries. Staging content is deliberately fixed to this snapshot
until a new review export is selected or normal live input is restored.
Production content publication continues normally. The native staging release
is `1793180987488928755-432388fc8729`.

## Verification

- Application: typecheck has zero errors/warnings; 102 unit tests and static
  build pass. Nine media tests exercise decoded pixels, page selection, native
  crops, four page rotations, nonzero page boxes, malformed input, full-PDF
  publication selection, deterministic reuse and source-byte invalidation.
- Exporter: 31 tests pass, including an image without a navigation link,
  retained PDF fragments, deleted-image exclusion, image-only changes and
  draft/published boundaries. The staging-input isolation test and shell syntax
  pass. Documentation links and whitespace checks pass.
- Chromium and WebKit each pass both map-image cases locally and on the private
  deployed site. The checks observe the real asset images reaching canvas
  `drawImage`, rather than merely checking an HTTP response or element count.
- Live output contains all 1 AI-map and 140 DeepRL image payload references,
  with every referenced asset present. Their JSON is 894,974 and 975,450 bytes.
  A first implementation inlined 52.37 MB for DeepRL; the delivered version
  externalizes the images, with approximately 17.62 MB of lossless PDF images
  measured locally. No reduction in decoded image memory is claimed.
- Manual in-app browser inspection confirms the restored central image and the
  exact `DeepRL_lecture01.pdf#page=4&rect=61,21,401,231` crop. The latter is a
  1360×840 image. Local screenshots are retained in the blog checkout at
  `.impeccable/review/excalidraw-fixed-staging.png` and
  `.impeccable/review/excalidraw-pdf-crop-staging.png`.
- Pulse guest/Docker-agent coverage passes. Homarr's six staging tiles have no
  drift. Native server health, five staging HTTP/TLS probes, seven scrapes,
  five alert rules, Grafana datasource/fleet checks and a fresh sanitized
  staging 404 in Loki pass. Native blog processes have guest and HTTP coverage,
  not individual Docker-process metrics.

The cold server build took 116 seconds, including dependency installation and
57.7 seconds of initial content generation. Subsequent unchanged local builds
reuse the map cache; PDF derivative keys also include source bytes, page/crop,
compiler implementation and dependency lockfile.

## Retention, rollback and limits

Retain under the blog infrastructure owner's responsibility until review is
accepted or cancelled:

- CT110 `/var/lib/dothomelab-blog-publisher-review` and
  `/srv/appdata/docker/staging/blog/review-editorial`, containing the selected
  snapshot and its source cache (about 919 MB). These are isolated from live
  output. Remove only after clearing the staging review marker and verifying
  normal publication or rollback.
- CT114 `/srv/appdata/docker/staging/blog/review-input.json`, the active selection.
  Current/previous native sites are the candidate above and
  `1793180903634451913-5035ebec01e2`. The native builder removed superseded
  generated copies, retaining these two releases. Guest archive sync retains
  `/opt/dothomelab.previous` and dated previous archives for rollback.
- Local browser screenshots as review evidence; native and local image caches
  as disposable build acceleration. No temporary service/container was created.
  The 26 disposable exporter fixture directories from this test run were removed.

The native cache totals are staging 3.3 GB and production 3.5 GB. Docker build
cache is staging 21.02 GB and production 9.7 GB; these shared caches and all
images/volumes are retained. This native release did not build Docker images.
No local worktree was created. Both canonical local checkouts retain their
published integration/review revisions; unrelated documentation and artwork
remain outside these commits. PVE's prior clean branch
`codex/blog-production-activation` remains at `d881ef99` for recovery; the
canonical PVE checkout now follows `codex/stillroom-settings`.

Cancel by selecting a compatible prior staging application revision and using
`build.py --environment staging --live-input`, or temporarily serve the retained
previous static release under the native rollback procedure. Production rollout
requires acceptance/promotion and an explicit production deployment request;
then install the accepted exporter and resume staging live input. An application
code revert alone does not clear the review-input selection.

Five unavailable-note warnings are identical between the live
and review exports. They are pre-existing source-note gaps, not missing images.
No physical-phone performance, arbitrary installed Obsidian-plugin behavior,
live rollback or clean-host recovery is claimed. No new backup was needed for
this stateless build change; the canonical vault was read only.

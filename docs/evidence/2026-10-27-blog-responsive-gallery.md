# Responsive blog galleries — 2026-10-27

Rafael requested a general gallery fix and production deployment. The application
release is `71caea006993fd43cc55cfc66ae3181267f38a65`, verified on both remote
`staging` and `main` and retained in `/Users/rafael/Repos/blog` on `staging`.
No homelab runtime source, authoring content, publication status or secrets changed.

## Cause and change

The real private Photography page reproduced four portraits in one row at a
390px viewport: a 358px gallery with photographs only 77.5px wide. React Photo
Album correctly measured the width. The application's 180px mobile row-height
target and absent row-count constraint allowed the crowded result.

The existing library now shows one uncropped photograph per row below 640px of
gallery width, at most two below 1024px and at most four above that. Desktop rows
target 280px height; sparse galleries are centered and capped at 480px row height.
The package's SSR wrapper supplies responsive static HTML instead of a fixed
960px fallback. Original files, ordering, lazy loading, captions and the existing
Yet Another React Lightbox remain. No dependency was added.

## Verification

- The new portrait regression failed before the fix: expected one photo per
  phone row, observed four. Afterward all 30 gallery cases passed across Chromium,
  Firefox and WebKit, using 320–1440px widths and return-to-phone resizing.
- Cases cover mixed proportions, four portraits, one portrait and empty input,
  with and without JavaScript; they check density, image proportions, sparse
  height, links, captions, next-photo navigation, dismissal and focus restoration.
- Type checking, all 93 unit tests, the production build, content preparation,
  diff whitespace and the focused design detector passed. Astro reported nine
  existing hints; the build retained its existing large-bundle warning.
- Live staging passed Chromium and WebKit at 320, 390, 768 and 1440px, with and
  without JavaScript. Its four authored photo occurrences become full-width
  phone rows; lightbox opening, next, close and focus restoration passed with
  no page errors. Phone/desktop fixture captures and the real phone capture are
  retained under the application's ignored `.impeccable/review/` directory.
- Production Chromium passed 390/1440px reading with and without JavaScript,
  with no page errors. Home, About, feed, sitemap, robots and tracker script
  returned 200. Photography remains a private draft: its public route returned
  404 and production contains zero generated gallery JPG files. No public
  real-photo gallery interaction is claimed.

## Releases and monitoring

| Environment | Activated (Europe/Amsterdam) | Native release | Content digest |
| --- | --- | --- | --- |
| Staging | 2026-10-27 19:59:26 CET | `1793127556799030357-71caea006993` | `c13e1d8b6a188f82257fb8efa1b83196cb5f6051e7cc1153cce86224ddd15003` |
| Production | 2026-10-27 20:01:51 CET | `1793127700616605260-71caea006993` | `462d2138363929e6ffacd5e99e8b138898f7a58d48c6736da5ebae33cbfec2bd` |

Staging used its existing `deploy.py --app blog`; production used the existing
`release.py --check` and `--activate` for this code-only update of the already
activated site. The installed release/build helpers matched the inspected source
checksums. Production fetched `origin/main` and used its existing published-only
editorial input. Native activation took 48.1s on staging and 52.3s on production.

Umami, Grafana, Prometheus and Loki dependencies were reachable. Pulse verified
guest and Docker-agent coverage for CT114/115. The native web units remained
active; all ten staging/production HTTP probes passed. Homarr's staging board
check reported six apps and no changes; the private Production board retained
its Blog tile pointing at `https://rafael.ink`. The shared verifier passed Umami
identity, Grafana dashboards/datasources, fleet freshness, staging scrapes/rules
and sanitized log ingestion. Native process resource metrics and external alert
delivery remain outside those checks.
Fresh production-origin requests also reached Loki. A PVE-originated Python HTTPS
probe received 403 at the public edge; desktop Chromium HTTPS and the established
production HTTPS probes passed. The log check therefore used the native origin,
without changing the public edge or claiming a new external-WAN test.

## Retention and limits

The previous code is `583faca110af790e9b282fc0db0a882d5c654324`. Retained rollback
sites are `/var/lib/dothomelab-blog/site/1793124989445440746-583faca110af` in CT114
and `/var/lib/dothomelab-blog/site/1793125151039718391-583faca110af` in CT115, with
matching `previous.json`. Both content digests remained unchanged. Follow the
[native rollback procedure](../../hosts/blog/README.md#install-and-recover) to
pause publication and restore the matching site pointer and metadata. Rollback
was not executed; no durable-data migration or extra backup was needed.

The native builder removed its obsolete complete outputs and code extraction
copies, retaining current/previous complete sites. No temporary containers or
worktrees were created. Existing Docker images and build caches were retained:
preflight cache usage was 37.55 GB on staging and 9.7 GB on production, with 75 GiB
and 29 GiB available in their guest roots. These are pre-existing Docker caches;
the native gallery release does not use them or authorize pruning retained images.

Two pre-existing failed production outputs, `1793119559634545325-ee48d3e6d4b1`
and `1793123246957199227-ee48d3e6d4b1` beneath `/var/lib/dothomelab-blog/site`,
were verified to contain only empty directories, no symlinks or files, and no
current/previous reference. Scoped `rmdir` removed them. Both guests now retain
exactly their current and previous complete site directories; no failed-build
diagnostic from this task remains.

The operator's unrelated untracked `artwork/scene/picnic2.svg`, the homelab Krita
evidence draft and its index edit remain untouched. Physical-phone gestures,
memory limits, external-WAN access and a deliberate rollback were not tested.

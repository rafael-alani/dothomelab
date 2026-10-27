# Astro migration and Obsidian photo galleries

Work performed on **2026-10-27**, Europe/Amsterdam. Rafael requested the Astro
migration, original photo files, Obsidian gallery blocks, click-only descriptions,
the map toolbar layout, Templater files and production deployment in this task.

## Delivered behavior

Blog candidate `2f0ec42770fd465d7ff94bd29af7a75ee1a5a428` uses Astro 7.4.2 static
output, its experimental incremental-build cache and persistent React islands.
The scene and its canvas survive client navigation. The existing nginx, Docker,
published-content and separate analytics contracts remain in use. Maps use a
content-addressed compilation cache; cache removal still permits a full rebuild.

React Photo Album lays out responsive original photographs. Yet Another React
Lightbox provides zoom, a mostly viewport-sized image, blurred translucent
background, bottom descriptions, Escape/backdrop/X dismissal and focus return.
Descriptions appear only after opening the photograph. Obsidian galleries use
`kind: gallery` and ordered blocks containing `---`, a `[[photo link]]`, optional
plain-text description and closing `---`. An optional link alias supplies alt
text independently of the description.

Photos, covers and ordinary article images are copied byte-for-byte, preserving
EXIF orientation, metadata and GIF animation. Browser handling of the original
orientation metadata is unchanged. TIFF display is rejected with an actionable
error; it can still be a download. Excalidraw assets remain unchanged too; the
user's optional map-only WebP conversion was not needed. Original SVG responses
use a sandbox CSP to keep active content inert when opened directly.

The first map toolbar row uses `justify-content: space-between` for Fit map,
Go to Starting note, Read notes and Full screen; the note picker stays below.
The fullscreen close icon and the menu remain independently clickable.

## Authoring installation

Installed `Blog gallery.md` and `Blog photo.md` in the vault's existing
`3. Resources/Templates` folder; refreshed the maintained authoring guide and
templates. Both new files match their repository versions by checksum.
Existing files/settings were retained before replacement under:

`/Users/rafael/Obsidian/obsidian-cloud-retrieval/.blog-publisher-backups/20261027T125048314721`

Restore individual files from that backup only after comparing subsequent
author edits. No publication status or authored gallery was created or changed.
Both new templates also reached CT110's synced vault with matching checksums.

## Verification

- macOS: typecheck (zero errors/warnings), 87 unit tests and static build pass.
- 78 applicable Chromium cases pass across the suite and focused reruns. The
  first full run exposed immediate-reload scroll loss; saving Astro's current
  history position before unload passed three consecutive final runs. A browser
  screenshot failure passed on its isolated rerun. Seven opt-in/audio cases were
  skipped locally and are not counted as passes.
- Six WebKit map/gallery cases pass across the final runs. Safari's click-focus
  difference required explicitly focusing the original link before opening the
  lightbox. Desktop/phone overlays and 320–1440px map layouts were inspected.
- Complete disposable authoring acceptance passes: drafts, publishing, moves,
  aliases, stable IDs, static routes, redirects, live content/artwork/palette
  refresh and recovery from an invalid SVG role. Changing only an attachment
  also changes its URL in warm-rendered Markdown.
- An unchanged warm build restored all 19 dynamic pages and reused all nine
  map compilations. No promise is made that all deployment work is incremental:
  Docker still assembles a complete static release.
- Publisher: 21 tests pass, including exact original bytes/EXIF, ordered gallery
  captions, publication selection and retaining the prior snapshot on an invalid
  export. Four vault-installer, seven editorial-import and eleven production
  tests pass. Homelab documentation checks pass.
- Parallel standards/spec reviews identified stale eager-Markdown rendering,
  direct SVG execution and TIFF display gaps; the implementation addresses all
  three. The UI detector returned no findings.

The npm production dependency audit retains three advisories (Vite, Zod, fflate);
no Node runtime or development server is shipped in the static nginx image.
An unrelated dependency upgrade was not bundled into this migration.

## Release and rollback observations

Publisher/platform helpers were installed from homelab
`989e052d7ec40159f08b565c53f948b3040d950a` on CT110/114/115. The production helper
archives on CT110/114 carry the same marker. The previous publisher image is
retained as `dothomelab/blog-publisher:pre-astro-20261027`.

The exporter retained preview content revision
`05ee8b28ab9deab0f8ecabfb47dedf1842c7f1d9a27c1cf9e2595ab80afa3a0c`: ten wrappers,
nine published. Existing content contains no authored gallery; interaction
acceptance uses isolated mixed-ratio gallery fixtures. Three previously missing
map-note targets remain an existing source-content gap. No substitute notes
were invented.

Live release acceptance is recorded below. Prior releases and
content generations are retained. No backup restore or deliberate live rollback
was exercised, and no physical-phone or external-WAN test is claimed.

Staging accepted `2f0ec42770fd465d7ff94bd29af7a75ee1a5a428` as release
`1793103019770245696-2f0ec42770fd-0d2ad13e2a76`; content and runtime configuration
match the prior preview. The deployment verifier passes. Live Chromium checks
pass for all nine course maps/standalone indexes and the responsive toolbar.
The first analytics case confirms exactly eight pageviews across navigation,
history, reload and standalone notes, two requested button events, no query/hash
payloads and zero DNT/blocked collections. The second build reused all nine map
compilations; its build command took 25 seconds, with static image packaging
remaining separate. nginx serves the original SVG response with the sandbox CSP
and retains staging's `noindex, nofollow` policy.

Staging readership acceptance also confirms note visibility, focus, time,
completed sessions and note-open collection. Its initial five-second URL
assertion timed out while waiting for standalone navigation; the navigation was
observed completing, and the unchanged test passed with a 30-second live
assertion allowance (24.5 seconds for the whole test). The note HTML itself
returned HTTP 200 in 32ms. Both remote application branches were then verified
at the exact accepted `2f0ec42` revision before production activation.

Production preparation uses published-only content digest
`160f93479f63659232b8a7ed48abfc55ab5fe6201c89b3e6bcb07ee4640a7d79`, retaining
the nine published wrappers. Umami, Grafana, Prometheus and Loki preflight checks
pass. The production build generates 19 pages; the private song wrapper and its
topic present in staging are excluded. The application build command took
46.3 seconds on the first production Astro build.

## Production activation and acceptance

The manual activation completed at approximately **12:34 UTC / 13:34 CET**.
Production is healthy at `https://rafael.ink`, release
`1793103901320555867-2f0ec42770fd`, code
`2f0ec42770fd465d7ff94bd29af7a75ee1a5a428`, content digest above and platform
`989e052d7ec40159f08b565c53f948b3040d950a`. nginx configuration validation,
container health, apex routing/TLS, feed, sitemap and telemetry checks pass.
The production manifest has exactly nine entries and zero drafts; the container
has zero mounts. HTML contains the Astro output and original SVGs receive the
same sandbox CSP verified on staging.

Four live Chromium acceptance cases pass against the public URL: every course
and standalone index, responsive controls at 320–1440px, real route/history/DNT
analytics and measured map readership. The first analytics case records eight
expected pageviews and two button events; DNT and blocked collection remain zero.
The second confirms note visibility, focus, time, completed sessions and note-open
requests. Live assertions use the documented 30-second allowance.

The prior production release remains
`1793096369094373515-1de2b14aadbf` in `previous.json`, with its image, source and
published content retained. The route reconciler retained its focused rollback at
`/srv/appdata/docker/infra-nginx-proxy-manager/production-route-before-1793104439099032252`.
No application data was migrated or removed, and no rollback was exercised.

All five current production probes pass (Home, About, article, feed and origin).
A unique 404 request reaches production Loki with exactly the seven allowlisted
fields and its query removed. Read-only Umami SQL from 12:34 UTC confirms stored
production events: 22 pageviews, one note-open, three note-focus events, and 13
each of note-visible, note-time and completed note-session events. This window
also includes the UI acceptance run, so it is not an isolated test count.

The canonical blog checkout and both remote application branches retain
`2f0ec42`. No worktree was created. Disposable failed authoring-test copies and
their background servers were removed; unrelated artwork and the existing Krita
documentation draft remain untouched. Application code and homelab runtime
changes are committed and published; the retained previous release provides the
normal manual rollback path described in the production runbook.

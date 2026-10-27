# Course-map opening and production release

Work performed on **2026-10-27**, Europe/Amsterdam. Rafael explicitly requested
publication to `rafael.ink` in the same task as the nine-map refinement.

## Application and authoring changes

Blog candidate `1de2b14aadbf2fa9571a7e2dc498f4c1376f6e82` retains optional
`starting-note` configuration. It first fits the drawing, holds for 350ms, then
zooms to the configured note in 800ms. GSAP owns the transition; reduced motion,
paused motion and skipped navigation jump directly. Map input and resize cancel
pending or active travel. Automatic opening does not emit a selection event.

The first toolbar row contains Fit map, Go to Starting note, Read notes and
Full screen. Find a note and its dropdown occupy the second row. Full screen
combines the groups when they fit; narrow layouts wrap button text and reserve
room above for the fixed menu. Safari retains a native dropdown at 44px height.

MDL retains `01. What is ML learning`. The other eight wrappers use Rafael's
exact full paths for DM&E, PAIR, PMI, SDM, DRL, AIP, Computer Vision and 3D Visual
Computing. Every configured path exists and resolves to a drawing card in local
generated collections. Git fallback articles carry the same settings.

Only the nine course wrappers were marked published. The unrelated song wrapper
remains a draft. Verified original vault wrappers and before/after checksums are
retained under
`/Users/rafael/Obsidian/obsidian-cloud-retrieval/.blog-publisher-backups/course-map-release-20261027T094000Z/`.
Restore only an individual original after comparing subsequent author edits;
retain its current contents before copying the backup over it.

## Local verification

Typecheck, all 87 unit tests, content preparation and the static build pass on
macOS. Ten focused Chromium cases and ten WebKit cases pass across final runs:
all nine courses, animated opening, reduced motion, saved skip preference,
interruption, 320–1440px toolbars, DOM preservation and no-JavaScript notes.
The Safari run found and verified the native-dropdown sizing fix. One WebKit
right-drag case failed once and passed on rerun. Desktop and phone screenshots
were inspected; the mechanical UI detector returned no findings.

No physical-phone performance benchmark, backup restore or deliberate live
rollback was performed. The three previously unavailable original map-note
targets remain a known source-content gap; no replacement notes were invented.

## Release observations

The first publisher attempt after authoring synchronization failed because a
dependency changed during export. Its integrity guard retained the prior good
snapshot. The normal timer retried after synchronization became idle with zero
pending items and zero errors. All nine requested status/starting-note changes
were verified in the live vault.

Production dependencies Umami, Grafana, Prometheus and Loki were healthy before
release. The initial production scaffold source check passed. Concurrent shared
observability work advanced the clean PVE and local checkouts; the release repair
was committed on top of that work without changing its services or data.

The successful publisher snapshot is
`05ee8b28ab9deab0f8ecabfb47dedf1842c7f1d9a27c1cf9e2595ab80afa3a0c`: ten
wrappers total, exactly nine published. The original three unavailable targets
remain reported. The exporter completed at 10:52:45 CET.

At 11:04:45 CET, staging accepted code `1de2b14`, configuration `0d2ad13e2a76`
and that exact content snapshot. The static-tree cutover validated nginx and
reloaded the existing healthy container. The standard deployment verifier passed.
Initial live browser checks passed opening, reduced motion, saved skip preference,
DOM continuity and standalone reading. Two 30-second test timeouts during the
concurrent packaging run were rerun with a 90-second allowance against the
completed snapshot.

All three final live staging checks passed: every course and standalone index,
Fit map/manual-selection interruption, and responsive controls. `origin/main` and
`origin/staging` were then verified at the same full `1de2b14` revision before
running the manual production activation command.

The first production preparation retained published-only digest
`f47b39d703b155c150d2d4254872b4036cd89451049cf3543c90cb9484744793`, derived
from the exact previewed snapshot. Its manifest contains only the nine course
wrappers and zero draft wrappers. Its build stopped at URL-history validation
before changing the running production release.

## Publication-history repair

The published-input filter retained article identities but omitted navigation
folder identities. Four renamed folders therefore retained their previous Git
addresses in the production build context. This reproduced locally with the exact
failed published content: `npm run content:generate` rejected stale history.
Comparing prepared history isolated only those four folder records.

Homelab `ea51aad7463e8f66ad28d45a84c26c09ee22b86c` retains history identities
from normalized `_index.md` files in the published tree, as well as published
articles. Draft and absent identities remain excluded. The regression exercises
both filtering and materialization with a renamed folder, draft and retired
private identities; it failed before the fix. All 11 production and seven
editorial tests pass. The original content reproduction now generates nine
public entries without needing to bypass production history validation.

That committed remote revision was fast-forwarded on PVE and installed as the
CT115 source archive and CT110 production helper archive. Prior archives remain;
the previous CT110 helper resolved to the retained shared-observability release
`d3615844929f6d65316515e43c2086ca86999788`. The production source guard passed.
The failed application candidate and previous healthy release remain retained.

## Production activation and acceptance

The rebuilt image passed nginx validation and became healthy at approximately
11:25 CET. Current production release is `1793096369094373515-1de2b14aadbf`,
code `1de2b14aadbf2fa9571a7e2dc498f4c1376f6e82`, published-only content
`160f93479f63659232b8a7ed48abfc55ab5fe6201c89b3e6bcb07ee4640a7d79`, and build
platform `ea51aad`. The content derives from the exact staging snapshot above;
its manifest has nine published courses and no draft. The application container
has no mounts, so it cannot access the private staging listening library.

The activation runner's immediate Alloy readiness request raced its restart.
The collector subsequently passed readiness; the remaining route, TLS, feed,
sitemap, telemetry and monitoring-target steps were completed successfully.
The existing apex route/certificate were retained, with focused route rollback
at `/srv/appdata/docker/infra-nginx-proxy-manager/production-route-before-1793096749821699225`.
The article probe initially rejected the old URL's 301, correctly exposing its
stale target. Homelab `ebc39f9e41a0d282f8d19bc2c0a9c4347e3f27d5` updates that
target to the canonical article and adds bounded collector readiness retries.
All 11 production tests and shell syntax pass. This source revision was installed
on CT115 and as CT110's production helper; its target update needs no blog restart.

All ten live Chromium cases pass against `https://rafael.ink`: nine course
starting-note selections, standalone indexes, animated overview-to-note opening,
return control, reduced motion/skip settings, interaction cancellation, responsive
controls at 320/390/768/1440px, DOM preservation, equations/images, and reading
without JavaScript. The published MDL view was also inspected in the app browser.

The previous production release remains `1793046895893988368-8e2fcec638e4`,
recorded in `previous.json` with its code/content/platform revisions. Images,
source bundles, failed candidate and helper archives remain retained. No deliberate
production rollback or recovery restore was performed. An independent web-fetch
tool could not access the public URL; the browser and TLS checks here ran from the
operator/homelab network, so independent WAN availability is not established.

Both real production analytics browser cases pass: eight expected navigation
pageviews and the requested button events, zero DNT/blocked collections, no
query/fragment payloads, plus note visibility, elapsed time, completed sessions,
focus and opening a standalone note. Read-only production-site SQL for
10:27–10:29 UTC confirms stored events including one note-open, three completed
sessions and ten time records. This window overlaps the final UI checks and is
not an isolated per-test count.

All five current production probes pass (Home, About, article, feed and origin).
The retired article target briefly remained as an old Prometheus series after
file discovery switched to the canonical URL; it is not a current target.
A unique production 404 reached Loki with exactly the seven allowlisted fields
and its query string removed. Alert delivery and independent WAN monitoring
remain unconfigured, as recorded by the shared observability acceptance.

The canonical local blog checkout and both remote application branches retain
`1de2b14`. No task worktree was created. Unrelated local artwork and pre-existing
documentation drafts were preserved. Follow the [production recovery procedure](../../hosts/production/README.md#recovery-and-rollback)
for any deliberate rollback; retained material is not a claim that rollback was tested.

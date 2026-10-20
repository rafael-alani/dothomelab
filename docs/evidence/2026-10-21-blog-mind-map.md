# Blog Obsidian mind map preview

Verified on 2026-10-21, Europe/Amsterdam, from the operator Mac through PVE
`192.168.0.250` and `pct exec 114`. This is a focused staging release, not a
fleet readiness or recovery audit.

## Accepted release

- Preview: https://blog.staging.rafael.media/work-and-nerdy/ai-technical-write-ups/machine-and-deep-learning
- Blog `staging`: `b01adb220183a3115acb17e204f5a03df80e8c34`, also published on
  `codex/obsidian-mind-map`. No `main` promotion was performed.
- CT114 homelab implementation / `DEPLOYED_COMMIT`:
  `d82e63cfe3d6f24d21f3cfd5311d40effe4b4113` on `codex/blog-staging`.
- Accepted configuration: `f668cdb41a3e`; release:
  `1792536234672041965-b01adb220183-f668cdb41a3e`.

The application now owns its Dockerfile, nginx configuration, port 8080 and
health check. Homelab Compose supplies the private origin, robots policy,
CT114 port 8084 and runtime restrictions. The runtime remains static nginx,
unprivileged, read-only except `/tmp`, without application data volumes,
production integrations, or injected secrets.

The export contains 450 unchanged source files. Its original drawing has 403
elements and 151 embedded note cards, backed by 171 static note pages. The blog
uses the same Excalidraw engine as export plugin 2.27.3 plus established Markdown,
wiki-link, callout and KaTeX packages. Its research report and source workflow
live in the blog repository; this repository owns deployment only.

## Verification

- Blog typecheck, 20 unit tests, production static build and seven Chromium
  browser tests passed locally. Tests cover map note selection, equations/images,
  fullscreen/Escape, a 390-pixel layout, no-JavaScript reading and existing blog
  navigation/one-Canvas behavior. Desktop/mobile screenshots were inspected.
- A fresh isolated lockfile install passed. The staging image built successfully
  with Node 24 and `npm ci`; nginx configuration validation runs as UID 101.
- The runner validated Compose quietly and accepted a healthy container with
  source `b01adb2` and configuration `f668cdb41a3e`.
- Trusted private HTTPS returned 200 for the article, collection and static note;
  canonical URL matched the private origin, and `X-Robots-Tag` was
  `noindex, nofollow`. A missing path returned HTTP 404.
- Live Chromium exercised full-map overview and note focus with no uncaught
  page errors. A separate JavaScript-disabled page rendered the selected note
  and five equations. The deployed collection resolved all 151 card targets.
- Blog, Stillroom, Form & Field and both Film-introspect containers were healthy
  after deployment. No production service was redeployed.

## Rollback observed and retained

The first candidate using the application Dockerfile failed health because
the staging runner's restrictive checkout umask produced a mode-0600 nginx
configuration. A disposable run of that image confirmed UID 101 could not read
it. The runner automatically restored the previous healthy release. The fix
uses `COPY --chmod=644` and validates nginx as the runtime UID during image build.
The corrected release then passed health and HTTPS checks.

`previous.json` retains release
`1792536103218491458-31405e0e1a12-4d673542836b`, source
`31405e0e1a124165121dd8f072168f699bf6b76f`, using the former inline image definition.
Failed candidate sources/images and earlier releases remain retained. Before
guest sync, the existing older archive was moved to
`/opt/dothomelab.previous-before-mind-map-d82e63c`; the immediately preceding
archive remains `/opt/dothomelab.previous`. No rollback history was deleted.

## Limits

Rafael's content acceptance is pending. No production promotion, new PBS run,
clean-host rebuild or backup restore was performed. Obsidian editing, arbitrary
vault plugins, and exact installed-theme parity are not reproduced. Safari,
Firefox, physical touch devices and a full accessibility audit remain untested.
Package/source availability is still required for rebuilding the image.

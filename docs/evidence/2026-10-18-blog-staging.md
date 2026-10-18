# Blog staging — 2026-10-18

Observed on PVE `afa`, CT114 and CT110, with browser acceptance from the operator
Mac on October 18 (Europe/Amsterdam). [Runbook](../../hosts/staging/README.md#blog--the-night-archive).

## Release and access

- URL: https://blog.staging.rafael.media; CT114 `192.168.0.114:8084`.
- Source: `rafael-alani/blog`, `staging`, `dfb3fcd1e4e980a644704a412a3face692be141f`.
  The user requested private visibility; GitHub was made private before the
  first push. Its dedicated CT114 deploy key was verified read-only.
- Homelab implementation: `3ed1844bdec48afba7a45f452ce5662c19242c9a`, retrievable
  from `codex/blog-staging`. Subsequent evidence-only commits retain this code.
- The static nginx container has no application data mounts or runtime secrets.
  Release bundles and the fetch key live in canonical staging appdata. No new
  `.env.example` setting is needed: its scoped runtime environment is empty.
- Private NPM route: LAN/Tailscale allowed, default deny, forced TLS. Pi-hole
  resolves the exact hostname to `192.168.0.110`; the existing wildcard TLS
  certificate validates. No public application DNS or router change was made.

## Checks

- Typecheck, 15 unit tests, production build and all five Playwright tests passed
  on the Mac. Tests cover direct nested loads, client/history navigation,
  no-JavaScript content, reduced motion, and WebGL failure fallback.
- CT114 built the committed source using `npm ci` and Node 24. Linux prerendering
  needs `NODE_OPTIONS=--dns-result-order=ipv4first`. Nginx configuration validation
  runs during image build and passed again in the running unprivileged container.
- The staging runner validated Compose, accepted the healthy blog container,
  and verified Film-introspect, FF, Stillroom and Blog at their accepted commits.
- Trusted HTTPS returned 200 for home and a nested gallery route; its `.data`
  payload returned 200; an unknown route returned 404. Responses include
  `X-Robots-Tag: noindex, nofollow` and the staging canonical origin.
- The in-app browser loaded the home page and completed About client navigation.
- The staging timer is active. Homarr reconciliation reports no remaining changes
  and five total entries (four Compose apps and the existing Symphony project).
- Nine staging deployment tests and repository documentation checks passed.

## Rollback and limits

Prior guest archives were moved to named `before-blog` directories before the
normal sync helper ran; no retained archives/images/data were pruned. Initial
failed build candidates remain. NPM rollback is
`/srv/appdata/docker/infra-nginx-proxy-manager/database.sqlite.pre-blog-20261018`
(verified SQLite integrity); Pi-hole rollback is
`/srv/appdata/docker/pihole/etc-pihole/pihole.toml.pre-blog-20261018`.
Restore only the affected route/record if other configuration has changed since.
A whole-database restore could discard later unrelated changes.

This first blog deployment has no prior accepted app release. To withdraw it,
retire its registration and owned route using the staging lifecycle procedure,
then stop its container while retaining source and release state. Future source
reverts can deploy normally because the blog is stateless. Routine scheduled
appdata backup covers its release inputs; no new PBS job, clean-host restore,
or external-network denial probe was run. Base images, npm packages and the
registered private deploy key remain rebuild prerequisites.

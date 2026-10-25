# Project production

CT115 `production` is an unprivileged Debian 12 Docker guest at `192.168.0.115`:
4 shared CPUs, 4 GiB RAM, 512 MiB swap, 64 GiB thin root quota on the NVMe
`local-zfs` storage. Its only data mount is `/srv/appdata/docker/production`,
backed by SSD `rpool/appdata/docker`. Quotas do not reserve SSD capacity; keep
60–90 GiB host headroom and serialize builds. Pulse observes this guest.

The scaffold starts the guest/Docker base, with no website, collectors, deployment
timer or public route change. Production appdata joins scheduled encrypted PBS
and the freeze list; no on-demand backup is necessary for a new empty guest.
No production secrets, media, staging appdata or remote Docker API are mounted.

## Release contract

`apps.json` registers the blog from `rafael-alani/blog`, exclusively `origin/main`,
at **https://rafael.ink** (the apex). The remote branch is currently absent; the
old local `main` also lacks the Docker contract. An accepted staging revision
must be explicitly promoted in a later task before production can build. The
release helper fails closed on missing main/access and never falls back to staging.

Agents deploy to production only when the active prompt explicitly requests it.
A main push, successful build, accepted preview or scaffolding request is not
permission. No timer, CI deploy or WUD image update starts these releases.
Every container has `wud.watch=false`. New applications need a portable Docker
contract, scoped production secrets/data, dependency checks and recovery design;
the initial release helper supports only the stateless blog.

The app-owned Dockerfile builds a static artifact. Deployment sets the apex
origin, `CONTENT_PREVIEW=0`, robots indexing and a separate Umami website ID.
`prepare-content.py` verifies the immutable export, copies only its published
subtree, and filters draft identities out of history/manifest. Production retains
that content digest with the main code SHA, source bundle, Compose and image.
The private staging listening/music mount is deliberately absent.

## Scaffold installation

From a clean committed PVE checkout:

```sh
./bootstrap.sh --prod-only --dry-run
hosts/production/install.sh
```

This installs CT115 plus immutable helper archives on CT110/112, registers a
separate production Umami website/Grafana dashboard, and updates Prometheus
with initially empty production discovery files. Existing telemetry remains.
`initialize-repo-key.py --app blog --environment production` creates a dedicated
key in canonical appdata. Register only its `.pub` file as a read-only GitHub
deploy key; private material stays on PVE and CT115. GitHub host keys come from
its authenticated HTTPS metadata endpoint; strict SSH checking stays enabled.

The required existing dependencies are CT112 Umami, Grafana, Prometheus and Loki;
CT110 NPM/apex TLS and the existing DNS/router route complete publication.
Before enrollment/release check their health and identity. Missing services,
credentials or permissions must be reported to Rafael; no substitute or demo
integration may pass acceptance. Shared administrative credentials stay on CT112.

## Activation

After Rafael accepts and explicitly authorizes promotion of an application
revision to `origin/main`, the final command on PVE is:

```sh
cd /root/dothomelab
hosts/production/activate.sh blog --publish-rafael-ink
```

The command is itself the publication boundary; do not run it during scaffolding.
It checks services and the existing apex route/certificate, freezes published
content, fetches/builds main without a listener, then checks main has not moved.
It validates Compose quietly, starts the origin, checks HTTP/container health,
starts scoped Alloy/Blackbox collectors, and only then replaces the apex route.
Existing public DNS, certificate and router forwarding are reused unchanged.
Only `/telemetry/script.js` and `/telemetry/api/send` reach public Umami collection;
its login/API/dashboard and Grafana remain private. No subdomain is required.

A failure before route publication leaves the placeholder/prior route intact.
Origin health failure restores the previous static image. A failed NPM render
restores the focused prior route fields and renders them again. Failures after
successful publication require inspection; a new release may already be public.
The command reports errors and stops instead of claiming a completed rollout.

## Monitoring and acceptance

Umami website `88d95afd-ff71-4f64-93ea-e57310dd952b` belongs only to `rafael.ink`.
Staging retains its own ID and private origin. Grafana UID `blog-production`
uses production-only Prometheus jobs and Loki selectors. Both metrics and logs
carry `project="blog", environment="production"`; staging uses `staging`.
Shared service names or databases are not sufficient environment separation.

Prometheus files in `/srv/appdata/docker/production-monitoring` have no targets
until activation. They then discover CT115 collectors and home/about/article/feed
HTTPS plus direct-origin probes. Production rules are separate from staging.
Alloy forwards only sanitized blog access JSON and uses its own cursor/appdata.
It never ships raw nginx errors, query strings, tokens, IPs or user agents.

No alert receiver or external uptime observer is configured. Report these gaps;
Grafana rule states are not delivered notifications or proof of WAN reachability.
After activation verify real navigation and fresh **production** Umami events,
query fresh **production** Loki records, check all five `probe_success` series,
and inspect the public site from an external connection. Browser acceptance,
private-music absence, draft exclusion and actual recovery are separate from
container health. The initial scaffold does not claim those live results.

## Recovery and rollback

Retain `production/blog/{prepared,current,previous,pending}.json`, `releases/`,
editorial inputs and the Git key. Images/build caches in the guest are replaceable;
source bundles and content permit rebuilding an accepted version without choosing
a new main head, though base images/package registries remain external prerequisites.
The runner keeps failed releases and never prunes source/images/data.

On an interrupted activation, inspect `pending.json` before any retry. Its previous
and candidate releases identify which image to stop/restart; verify the actual
container commit label and health before repairing the current pointer. Keep all
journal/release material until recovery is verified. A stateless code rollback
cannot rewind analytics and must never restore the shared Umami database.

Each publication saves an integrity-checked NPM database and a focused original
route row under `infra-nginx-proxy-manager/production-route-before-<time>/`.
Restore only that route's changed fields and re-render it; restoring the entire
database risks unrelated later edits. Keep current and prior images, source
archives and rollback rows. No clean-guest restore or public cutover has yet
been tested. Full bootstrap creates the guest but does not activate a new main
release; explicit production authorization remains necessary after recovery.

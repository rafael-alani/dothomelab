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
at **https://rafael.ink** (the apex). An accepted staging revision must be
explicitly promoted to remote `main` before production can build. The
release helper fails closed on missing main/access and never falls back to staging.

Application code follows the explicit main-only release workflow. Blog content
uses the [native static pipeline](../blog/README.md): `published` is immediately
eligible for public deployment and `draft` removes it there. There is no per-edit
approval, code fetch, CI gate, Docker build or deployment polling delay.

Native Node builds static output and native nginx serves it. `CONTENT_PREVIEW=0`,
the apex origin and a separate Umami website ID are deployment configuration.
Only the published tree and its filtered history/manifest enter CT115. Complete
output trees preserve deletion and unpublishing; private listening media is absent.
Other applications retain their declared deployment contracts.

## Scaffold installation

From a clean committed PVE checkout:

```sh
./bootstrap.sh --prod-only --dry-run
hosts/production/install.sh
```

This installs CT115 plus immutable helper archives on CT110/112/114, registers a
separate production Umami website/Grafana dashboard, and updates Prometheus
with initially empty production discovery files. Existing telemetry remains. Staging Blackbox receives corrected canonical-URL
checks; staging applications and Alloy are preserved.
`initialize-repo-key.py --app blog --environment production` creates a dedicated
key in canonical appdata. Register only its `.pub` file as a read-only GitHub
deploy key; private material stays on PVE and CT115. GitHub host keys come from
its authenticated HTTPS metadata endpoint; strict SSH checking stays enabled.

The required existing dependencies are CT110 Umami, Grafana, Prometheus and Loki;
CT110 NPM/apex TLS and the existing DNS/router route complete publication.
Before enrollment/release check their health and identity. Missing services,
credentials or permissions must be reported to Rafael; no substitute or demo
integration may pass acceptance. Shared administrative credentials stay on CT110.

## Activation

After an accepted application revision exists on `origin/main` and Rafael
explicitly requests production publication, the final command on PVE is:

```sh
cd /root/dothomelab
hosts/production/activate.sh blog --publish-rafael-ink
```

This command installs a requested `origin/main` code release and configures the
existing public route and scoped telemetry. It also enables automatic content
publication. Routine content edits require no command. Existing public DNS,
certificate and router forwarding are reused. Only the tracker script and send
endpoint reach public Umami; administration and Grafana stay private.

## Monitoring and acceptance

The private [Homarr Production board](https://rafael.media/boards/Production)
links to the public blog. `hosts/infra/homarr/reconcile-production.sql` owns this
board and is included by the normal managed-tile reconciler; `--production-only`
applies just that board with a fresh SQLite backup. It preserves home-board
defaults and user layout edits. Shared Grafana/Umami remain on the existing
managed boards; adding a tile never activates a production release.

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

The [scaffold and first activation evidence](../../docs/evidence/2026-10-25-production-scaffold.md)
records installed revisions, observed checks and rollout limits. The October 26
activation published blog `8e2fcec` through Cloudflare, with verified production
browser analytics, sanitized logs and separate passing endpoint probes.

## Recovery and rollback

Retain canonical editorial inputs, `current.json`, `previous.json`, the Git deploy
key and scoped observability appdata. Native build dependencies/caches and static
releases are replaceable guest-root state. The [native runbook](../blog/README.md#install-and-recover)
owns rebuilding and pointer rollback. A restored activated site resumes content
publication from its retained code revision; a new scaffold requires initial
activation. Analytics is independent and must not be restored to roll back HTML.
The previous Docker release remains a migration rollback artifact until native
recovery has been exercised. Publicly downloaded copies cannot be recalled by
switching an article back to draft.

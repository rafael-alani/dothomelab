# Pulse availability and dashboard coverage — 2026-10-27

## Environment and method

Read-only checks used SSH to PVE `afa` and `pct exec` into the managed LXCs.
PVE and the canonical local checkout were at
`68cba604cac0f75b4dcf062dfaabaacbf4dfcedc` on
`codex/blog-production-activation`; CT110 carried that same `DEPLOYED_COMMIT`.
Credentials stayed on PVE and were loaded with the repository dotenv parser.

## Availability

Both `https://pulse.rafael.media/` and `http://192.168.0.110:7655/` returned
HTTP 200 from the operator machine. The in-app browser rendered the Pulse login
form. An authenticated HTTPS API session successfully read the live resource
inventory. The focused Pulse verifier passed direct/HTTPS health, image/update
policy and canonical appdata ownership checks. Pulse was healthy and had been
running for approximately 30 hours when first inspected.

NPM route 52 was enabled and pointed to `http://192.168.0.110:7655`, permitting
only `192.168.0.0/24` and `100.64.0.0/10` with a final `deny all`.
The reported outage was not reproduced from this network. A client error and
connection context are still needed to distinguish an intermittent failure,
browser issue, or access outside the permitted network. No runtime restart,
deployment, credential change, or access-policy change was made.

## Pulse coverage

`python3 hosts/infra/pulse/configure-monitoring.py --verify` passed on PVE.
A separate authenticated HTTPS comparison matched names from each guest's
`docker ps` against Pulse's paginated online application resources:

| Guest | Running containers | Present online in Pulse |
|---|---:|---:|
| CT102 Servarr | 21 | 21 |
| CT110 Infra | 13 | 13 |
| CT112 Apps | 47 | 47 |
| CT114 Staging | 8 | 8 |
| CT115 Production | 3 | 3 |
| Total | 92 | 92 |

All six LXCs, including PBS, and VMs 101/104 were online in Pulse. This proves
guest and declared Docker coverage, including database/worker containers. It
does not establish process-level monitoring inside VM101/HAOS or end-to-end
availability of every application. Pulse resource presence is not a synthetic
HTTP/browser uptime check.

## Homarr and agent instructions

The live Homarr SQLite integrity check returned `ok`. The managed Staging board
contained Blog, Ff, Film Introspect, Meta Egg, Stillroom and Immich Removal;
`hosts/staging/sync-homarr.py --check` returned `changed: false, apps: 6`.

Homarr is not a complete service catalog. Its app table and actual board tiles
contained no Grafana, Umami, or `https://rafael.ink` entry. Historical tiles such
as Readarr and Paperless-GPT remain, so tile presence does not prove a running
service. This check did not reconcile or remove dashboard entries.

Before this change, the Pulse runbook required new Docker hosts to be enrolled,
and staging had automatic Homarr reconciliation, but `AGENTS.md` had no explicit
joint enrollment completion rule. It now routes service additions, moves,
renames and retirements to the operations procedure, requiring verified Pulse
coverage, appropriate Homarr tiles and explicit gaps. The Pulse runbook's stale
five-guest wording was also corrected to include production.

## Validation and limits

This change is documentation only; the scheduled appdata backup last completed
successfully at 02:17:54 CET on October 27. No on-demand backup was warranted.
Documentation links and whitespace are checked with `scripts/check-docs.py`
and `git diff --check`. Runtime archives retain their existing deployed revisions.
No restore, destructive rebuild, external-network access test, or authenticated
browser dashboard journey was performed. Reverting the documentation commit
restores the prior instructions without changing runtime state.

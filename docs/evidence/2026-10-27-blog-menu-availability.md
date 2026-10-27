# Blog submenu availability — 2026-10-27

Rafael requested availability labels for every submenu list and production
deployment. Blog commit `80238c963cf99d860bbd5ccb3da6a17002370101` is published
to `origin/staging` and `origin/main`, and installed on CT114/115 after Rafael
explicitly accepted the preview. Empty submenu rows now show **Soon 🙏**
at the right; rows with included content have no label. Existing static markup,
link behavior, styling and publication filtering remain intact.

## Verification

- Local typecheck, all 93 unit tests, production static build, content preparation,
  whitespace check and the scoped design detector passed. The build retains its
  existing large-chunk warning and Astro reports nine existing hints.
- Updated the existing empty-topic browser regression, including its stale
  expected order, to match current descending folder priorities. Chromium passed
  both empty rows and navigation through the unmarked populated topic.
- Local generated HTML passed across seven area lists: 29 labeled empty submenus
  and one unmarked populated submenu. The actual staging export differs: every
  row in its six area lists passed, with 23 empty and four populated submenus.
- The live private Creativity page visibly shows five labels and no label on
  Photography. Its content remains draft-only. Production publication status
  was not changed. The browser capture is retained at
  `/Users/rafael/Repos/blog/.impeccable/review/menu-availability-staging.png`.
- Production's six area lists passed: 26 empty submenus are labeled and the
  populated AI submenu is unmarked. The public browser confirms both states and
  hamburger navigation to Technical Write-ups. Its capture is retained at
  `/Users/rafael/Repos/blog/.impeccable/review/menu-availability-production.png`.
  The output contains nine published articles plus the About folder page, no
  draft entries and no Photography route. Seven origin HTTP routes pass.
- Native staging service/HTTP verification passed. Production dependencies
  Umami, Grafana, Prometheus and Loki are reachable. All ten environment probes
  pass; shared dashboards, datasources, fleet freshness, alert-rule evaluation
  and sanitized staging request-log ingestion pass. Pulse verified CT114/115
  guest/agent coverage; Homarr staging reported six apps with no drift and the
  private Production board retains its Blog link to `https://rafael.ink`.
  Post-activation checks also passed all ten probes and fresh production menu
  request ingestion into Loki with only the allowed sanitized fields.

## Deployment

Staging release `1793141179683879256-80238c963cf9` activated at
**2026-10-27 23:46:30 CET**, using the unchanged preview content digest
`c13e1d8b6a188f82257fb8efa1b83196cb5f6051e7cc1153cce86224ddd15003`.
The native build took 60.33 seconds. The installed build/release helper hashes
match the inspected homelab source; this release uses no Compose deployment.

Rafael explicitly accepted preview commit `80238c9` and requested production
deployment, resolving the earlier approval-review block. The exact accepted
commit was pushed to `main` and verified remotely before running on PVE:

```sh
pct exec 115 -- python3 /opt/dothomelab/hosts/production/release.py --check
pct exec 115 -- python3 /opt/dothomelab/hosts/production/release.py --activate
```

Production release `1793141463509660323-80238c963cf9` activated at
**2026-10-27 23:51:16 CET**, with the same code revision and unchanged published
content digest `462d2138363929e6ffacd5e99e8b138898f7a58d48c6736da5ebae33cbfec2bd`.
The native build took 45.043 seconds; the web unit remains active. The installed
revision, public menus, published-only output and monitoring checks passed.
No new backup, data migration, native rollback exercise, physical-phone check or
external-WAN check was performed. Native process resource metrics and alert
notification delivery remain outside the verified coverage.

## Retention

The native builder removed the superseded staging generated site
`1793124989445440746-583faca110af` and temporary code extraction. Staging retains
the new current site and `1793127556799030357-71caea006993` with matching
`previous.json` for the [native rollback procedure](../../hosts/blog/README.md#install-and-recover).
The release helper owns these generated outputs; the older site expires after
another successful activation. Production likewise removed the superseded
`1793125151039718391-583faca110af` generated output and code extraction, retaining
the new current site and `1793127700616605260-71caea006993` with matching
`previous.json`. No task-created diagnostic or temporary runtime remains.
Git history, editorial inputs and analytics are retained independently.

No temporary containers or worktrees were created. Preflight Docker build caches
were 21.02 GB on staging and 9.7 GB on production; guest filesystems had 82 GB and
29 GB available. They are pre-existing caches owned by the respective deployment
hosts, retained for ordinary Docker builds and not used by this native release;
future cleanup must use the lock-aware runtime cleanup procedure. Docker images,
volumes and durable data were not pruned.

The canonical blog checkout remains on `staging` at the delivered revision.
The unrelated `artwork/scene/picnic2.svg` and pre-existing homelab documentation
drafts are untouched. No duplicate checkout requires consolidation.

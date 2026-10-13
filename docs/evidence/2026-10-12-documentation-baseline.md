# Documentation baseline — 2026-10-12

Purpose: establish a bounded, read-only live baseline for the documentation
pilot. This was not a deployment, repair, backup execution, or restoration.
Client timezone: Europe/Amsterdam. Baseline Git HEAD:
`c2661ddd1d2ca2db757f911c05d3606934b2ccdb`. Documentation edits followed locally.

## Method

SSH to PVE with normal host-key verification; enter LXCs only through
`pct exec`. Read `pveversion`, `pct list`, `qm list`, pool health, canonical
dataset mountpoints, CT112 mount configuration, active/all Docker names and
statuses, `DEPLOYED_COMMIT`, selected systemd result fields, and timer state.
No production environment values, authentication material, full Docker inspect,
or application records were collected.

NPM's SQLite database was opened with `mode=ro` inside CT110. Only domains,
upstream scheme/address/port, enabled flag, access-list ID, and a boolean for
inline `deny all;` were returned. This was a configuration inspection, not an
external request/ACL test. Five unauthenticated DNS/HTTPS probes were made from
PVE, with bounded timeouts, normal TLS validation, and discarded response bodies.

## Results

PVE reports `pve-manager/9.1.2/9d436f37a0ac4172`, kernel `6.17.4-1-pve`.
CT102, CT110, CT112, CT113, CT114, VM101, and VM104 were running. `rpool` and
`vault` were ONLINE. Canonical mountpoints were `/srv/appdata/docker`,
`/vault/shared`, and `/vault/pbs_datastore`.

| Guest | Running Docker containers | Guest archive revision |
|---|---:|---|
| CT102 | 21 | `a4f1374011546c7899a6a43ace5c1a93b6100edb` |
| CT110 | 12 | `ee1c217cc56c011eede9cf728acb2b1938d5218d` |
| CT112 | 44 | `c2661ddd1d2ca2db757f911c05d3606934b2ccdb` |
| CT114 | 2 | `ee1c217cc56c011eede9cf728acb2b1938d5218d` |

No active container reported an unhealthy status. Some containers have no
Docker health check, so this does not assert fleet application health. Retained
stopped restore-test containers remain on Apps, including historical nonzero
exits. Those were not rerun or cleaned up.

Infra's extra container was `contentflow-contentflow-1`, healthy, project
`contentflow`; no corresponding Compose declaration exists in this checkout.
Apps includes running healthy `droppedneedle`, and has no `paperless-gpt`
container. Thus the 44 Apps count cannot validate desired membership. Staging
had only `staging-film-introspect-api-1` and `staging-film-introspect-web-1`,
both healthy.

CT112 declared `mp0` shared read-only `/data`, `mp1` canonical appdata, and narrow
`mp2`–`mp6` downloads/music/slskd/podcasts/Storyteller binds. `mp7`, `mp8`, and
`mp9` carried the Aurral flow, Grimmory ebook, and Audiobookshelf audiobook
appdata bridge paths. This checks LXC configuration, not file-level permissions
or every application's effective mounts.

The appdata backup service reported `Result=success`, `ExecMainStatus=0`, with
completion **2026-10-12 02:25:08 CEST**. Its next scheduled timer invocation was
October 13. WUD's handoff service reported `Result=exit-code`,
`ExecMainStatus=1`, completion **2026-10-12 02:26:31 CEST**. No attempt was made
to establish the failed candidate or cause. Proton's host timer was `disabled`.

## Access observations

| Hostname | Pi-hole answer | HTTPS root response from PVE |
|---|---|---:|
| `rafael.media` | `192.168.0.110` | 200 |
| `aurral.rafael.media` | `192.168.0.110` | 200 |
| `pinepods.rafael.media` | `192.168.0.110` | 200 |
| `zotero.rafael.media` | `192.168.0.110` | 200 |
| `film-introspect.staging.rafael.media` | `192.168.0.110` | 200 |

Zotero's root 200 is not a PROPFIND, attachment write/read test, or native-client
sync. The other root responses similarly establish only reachability with TLS.

NPM showed the managed private service routes enabled with inline `deny all;`
and the expected backends. DroppedNeedle's route was disabled. The older
`film-introspect-staging.rafael.media` alias and the nested staging origin both
existed. An additional enabled `symphony-check.staging.rafael.media` route
pointed to CT114 port 8081 without a running declared app in this inventory.

Several older routes had access-list ID 0 and no inline `deny all;`, including
Homarr, the Arrs, qBittorrent, Pi-hole, NPM administration, PVE, Portainer,
Immich, Jellyfin/Seerr/Jellystat, Mealie, and Cockpit. Existing public Jellyfin,
Wizarr invitations, and HA routes also lack that inline private policy. These
observations do not establish internet reachability or authorize changing ACLs.
Old Obsidian/OpenWebUI proxy entries remain and were not validated as services.

## Scope limits

No guest/container was stopped or restarted; no deployed archive was changed;
no credentials were read out, reset, or supplied; no new backup, scrub, restore,
authenticated UI journey, full fleet verifier, public ingress test, or client
device acceptance ran. The differing revisions, failed WUD result, extra live
service, and retained routes are follow-up findings rather than repaired state.

## Documentation validation — October 13

The pilot's local review checked all documentation roots with
`python3 scripts/check-docs.py`, ran `git diff --check`, and passed
`bash provision/verify-media-contract.sh --repository`. The link check also
passed isolated positive/negative smoke cases for encoded paths, duplicate
heading anchors, fenced examples, missing files/anchors, and unindexed evidence.
These checks establish navigation and the existing media declaration contract,
not user-workflow acceptance.

The former AGENTS authorization boundaries were retained verbatim. Detailed
network/storage rules moved to architecture, service update/data constraints
to the linked policy reference, and earlier readiness to dated status/history.
Source review corrected two runbook contradictions: Aurral's cold-boot flow
mount uses explicit CT112 `mp7`, and BookOrbit discovers Shelfarr imports through
its own watcher/scan while Shelfarr's one active integration slot remains with
Audiobookshelf. No production configuration changed.

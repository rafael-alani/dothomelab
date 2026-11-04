# Public blog restored through Cloudflare Tunnel — November 4, 2026

Public `https://rafael.ink` is restored. Independent HTTPS probes from the
Netherlands and Germany returned **200** at 16:28 CET, after the
[confirmed provider-CGNAT outage](2026-11-04-public-blog-ingress-options.md).
Rafael explicitly authorized implementation and supplied the connector token
through the hidden PVE prompt. No router change was needed.

## Delivered configuration

Infrastructure release **`9234544beeb3fad6469baf76dd217e864d60c1e0`** is published
on `origin/codex/public-blog-tunnel` and installed in the isolated PVE/CT110
archive `/opt/dothomelab-blog-tunnel/releases/<commit>`, with matching
`DEPLOYED_COMMIT` and `current` symlinks. The owning
[runbook](../../hosts/infra/blog-tunnel/README.md) declares bootstrap, verification,
secret ownership, manual updates and rollback.

- Cloudflare account `1278626322bb50d822fe9f48aabf4cc4` contains the remotely
  managed tunnel `dothomelab-public-blog`, UUID
  `28987c47-3311-4503-b688-d6f080468d95`.
- CT110 runs `cloudflare-blog-tunnel`, official cloudflared `2026.10.7`, pinned
  to digest `sha256:4955524aeaa379e154023d5a027c250f7b35041a2e7e950cf13f144bc9b9c5ba`.
  Docker readiness passes; Cloudflare shows Healthy, one Linux replica and four
  Amsterdam edge connections. The container has no published ports, appdata
  mounts or Docker socket, and its root filesystem is read-only.
- The connector-applied configuration was read back from its configuration log:
  **only `rafael.ink`** routes to `https://192.168.0.110:443`; both Host and TLS
  server name are `rafael.ink`, with certificate verification enabled. The
  catch-all is `http_status:404`. NPM still forwards to the existing native
  production blog on CT115. Private staging is outside the tunnel.
- The apex is now a proxied CNAME to
  `28987c47-3311-4503-b688-d6f080468d95.cfargotunnel.com`, TTL Auto. The guarded
  DNS API replacement preserved the record identity, comment and tags. The
  dashboard first saved the route but could not create DNS because the A record
  already existed; the operator helper performed the replacement safely.
- Both PVE dotenv and the running DDNS container now manage only
  `pictures.rafael.ink,stream.rafael.ink,join-stream.rafael.ink`. DDNS keeps its
  existing image bytes (`sha256:2fb2dcbde91b97e124f3e1b73bd6238a504e745fcd8b97db9182c55d0f571b38`),
  the `favonia/cloudflare-ddns:latest` tracking reference, and WUD labels.
  Cloudflared itself is manually updated (`wud.watch=false`).
- Blog application code, publishing, private previews, data ownership, other
  routes, PVE's active Git branch and the shared guest source archives were
  preserved. Bootstrap now declares the connector and its verifier.

## Verification

- [Independent Globalping results](https://api.globalping.io/v1/measurements/26kHH0ybjFk8TcQOJ00021RVw):
  DELUXHOST Amsterdam and Hetzner Falkenstein both returned HTTPS 200 from the
  Cloudflare addresses `104.21.36.237` and `172.67.200.235`, respectively. Total
  response times were 211 ms and 198 ms. Both responses were dynamic, not stale
  cached pages. The external result link may expire; these observations are retained.
- Direct requests through both public Cloudflare IPs returned 200. The home page,
  `/about`, `/feed.xml`, `/favicon.svg` and `/telemetry/script.js` pass. Chrome
  navigation renders the home page and About text. The public-IP checks explicitly
  bypass the local DNS override; the Chrome check alone would not prove WAN access.
- The private `blog.staging.rafael.media` still returns 200 through
  `192.168.0.110`. The exact two-rule tunnel configuration proves no private
  hostname was enrolled. This task did not republish draft content.
- Pulse verifies PVE and all five Docker agents, including the new running
  connector. Ten existing staging/production blog probes and fourteen related
  scrapes pass. These probes use local routing; independent WAN checks above
  provide the external evidence. No persistent external monitor was added.
- Production Umami recorded the real browser visits to `/` and `/about` at
  15:27 UTC under the existing production website ID. Homarr's existing private
  Production board keeps the `https://rafael.ink` tile, direct origin ping and
  three layouts. The background connector needs no separate tile.
- Eight focused helper tests, shell syntax, quiet Compose validation and docs
  checks pass. Tests cover token identity, scoped dotenv edits, stale inherited
  environments, exact DDNS removal, address ambiguity, metadata preservation,
  DNS drift and refusal to change the DDNS image during a domain edit.

The first live DDNS check caught an inherited old `DOMAINS` value overriding the
new dotenv file. A fresh invocation corrected the runtime; the delivered helper
now updates the subprocess environment atomically with the file, verifies the
running DDNS list after recreation and checks it again before DNS cutover.
The final recreation restored the original registry image reference while proving
that its image ID still matched the previously running bytes.

## Credentials, rollback and retained artifacts

The Windows and Docker installation commands contain the same connector token;
the hidden prompt extracts it and never executes the pasted command. It is saved
only in PVE `/root/.env` and injected into the owning connector. An earlier
native-terminal restriction and rejected encrypted tool-output handoff were
resolved by Rafael's hidden-prompt entry. No token or ciphertext entered task
output. The ephemeral transfer key was removed and browser-memory copies cleared.

Retain, under the infrastructure operator's ownership:

- `/srv/appdata/docker/cloudflare-blog-tunnel/ingress-before-tunnel-20261104`:
  protected pre-change environment and exact DNS/domain metadata. Files are
  mode 0600 inside the restricted rollback directory. Retain until acceptance
  and explicit removal authorization. The directory is within appdata backup
  coverage; this change did not trigger or prove a fresh backup/restore.
- Current PVE/CT110 source archive `9234544...` and previous deployed archive
  `176bacf...`; PVE also retains setup archives `26bd10c...` and `ed00143...`.
  These contain Git source, not secrets. Retain current/previous for operational
  recovery; the initial setup references may be removed after acceptance.
- Local recovery branch `recovery/pre-blog-tunnel-20261104`, commit
  `23bd1008ab967720d6b182f9d4e01e41b7c79140`, preserves pre-existing dirty docs
  and three unrelated untracked reports. Recover a file with
  `git show recovery/pre-blog-tunnel-20261104:<path>` and review before restoring;
  do not reset over newer work. Retain until that unrelated work is resolved.

The canonical local checkout retains the delivered review branch and untouched
unrelated documentation. No new worktree was created. Temporary environment and
transport files were removed by the deployment helpers; no diagnostic container
remains. The unused diagnostic cloudflared `2026.10.3` image was removed after
checking that no container used it. CT110/114/115 build caches measured about
245 kB / 21.07 GB / 9.7 GB before activation; no app builds or cache pruning ran.

`manage.sh rollback-dns` restores the old A record and original DDNS list while
preserving unrelated dotenv changes. **That restores configuration, not Internet
reachability while CGNAT remains.** Live rollback and clean rebuild were not
exercised. Recovery requires the retained Cloudflare tunnel/ingress/CNAME and token;
a connector token cannot recreate a deleted Cloudflare control-plane object.
The other three public service names still depend on inbound routing and were
not migrated in this blog-only restoration.

# Public blog tunnel preparation — November 4, 2026

Rafael authorized proceeding after signing into Cloudflare in Chrome. This follows
the [confirmed CGNAT diagnosis](2026-11-04-public-blog-ingress-options.md).
The public site is **not restored yet**: credential entry is the remaining gate
before connector startup, remote ingress configuration and DNS cutover.

## Prepared state

- Cloudflare account `1278626322bb50d822fe9f48aabf4cc4` now contains the remote
  tunnel `dothomelab-public-blog`, UUID `28987c47-3311-4503-b688-d6f080468d95`.
  It has no connected connector or published hostname yet.
- Branch `codex/public-blog-tunnel` contains the scoped Compose, ingress
  declaration, guarded operator helpers, bootstrap integration and
  [runbook](../../hosts/infra/blog-tunnel/README.md). Initial release `26bd10c`
  and hidden-prompt improvement `ed00143d9117920cad71820d2eb127e4643f43ee` are
  published. PVE's current prepared archive is the latter, under
  `/opt/dothomelab-blog-tunnel/releases/`, with matching `DEPLOYED_COMMIT`.
- Official `cloudflare/cloudflared:2026.10.7` is downloaded on CT110 and pinned
  by manifest digest in Compose. No cloudflared container has been started.
- The intended route is only `rafael.ink`, through trusted HTTPS to the existing
  NPM host at `192.168.0.110:443`, with SNI and Host both `rafael.ink`. Unmatched
  hostnames return 404. Private staging and other public services are excluded.
- No router, firewall, DNS, DDNS domain list, existing container, application
  code, data ownership or publishing setting has changed. The current A record
  remains behind the provider's CGNAT and public ingress is still unavailable.

## Credential handoff

Native terminal UI access was denied. Automatic approval review also rejected a
public-key-encrypted connector-token handoff through tool output because even
credential-derived ciphertext would enter the transcript. No ciphertext was
emitted. The ephemeral PVE private key was removed, and the browser-memory token
was cleared. The browser clipboard was restored after the original copy.

Rafael was asked to run:

```bash
ssh -t root@192.168.0.250 'bash /opt/dothomelab-blog-tunnel/current/hosts/infra/blog-tunnel/manage.sh store-token'
```

Paste the Cloudflare token or complete copied installation command at the hidden
prompt. The helper validates the token's account/tunnel identity, saves only the
token to PVE `/root/.env` with mode 0600, and never executes the pasted command.
Do not paste credentials into chat. At the last check the token key was absent.

Once it exists, fetch the branch, deploy the tested commit, configure the declared
remote ingress, remove the apex from DDNS with `prepare-dns`, then run
`switch-dns`. The helper requires connector readiness and checks for DNS drift.
Keep the existing Cloudflare setup tab for the handoff. Restoration still needs
independent public HTTP/browser checks and post-start Pulse enrollment validation.

## Checks and limits

- Six focused unit tests pass: token account/tunnel scope, preservation of
  unrelated dotenv values, duplicate/unsafe-value rejection, exact DDNS domain
  removal, ambiguous address-record rejection, metadata preservation and refusal
  to cut over after DNS drift or while DDNS still owns the apex.
- Shell syntax, documentation links and whitespace checks pass. CT110 Compose
  validation passes with a non-secret placeholder; real-token validation and
  connector startup remain pending.
- Pulse verifies PVE and all five Docker agents, including existing containers.
  This is baseline coverage, not verification of the unstarted connector.
- Homarr's existing private Production board contains the `https://rafael.ink`
  tile, direct origin ping `http://192.168.0.115:8084`, and all three layouts.
  No new tile is needed for a connector with no administration UI.
- Existing CT110/114/115 running inventories contain no task-created diagnostic
  containers. Their build caches measure approximately 245 kB / 21.07 GB /
  9.7 GB respectively. No build cache, application image, volume or release
  generation was pruned; the tunnel creates no application build cache.
- This is not a completed clean rebuild or tested live rollback. Configuration
  rollback will restore the old A record/DDNS list; it cannot remove CGNAT.

## Retained work and cleanup

The canonical local checkout stays on `codex/public-blog-tunnel`. Existing local
documentation edits and three unrelated untracked reports remain untouched.
Recovery branch `recovery/pre-blog-tunnel-20261104`, commit
`23bd1008ab967720d6b182f9d4e01e41b7c79140`, preserves them. To recover a specific
file, use `git show recovery/pre-blog-tunnel-20261104:<path>` and review before
restoring it; do not reset over newer work. This is an operator-owned recovery
ref to retain until that pre-existing documentation work is resolved.

The unused diagnostic `cloudflare/cloudflared:2026.10.3` image was removed after
confirming that no container referenced it; pinned `2026.10.7` remains.

No new worktree was created. PVE's `/root/dothomelab` branch and existing guest
`/opt/dothomelab` archives were preserved. The two new immutable PVE source
archives belong to this tunnel task and remain as setup/recovery references until
activation is verified. No credential rollback snapshot exists until the token
helper runs; it will then retain the protected pre-change environment in the
canonical appdata directory documented by the runbook.

# Syncthing private GUI rollout

## Scope and preflight

This change publishes the existing CT110 Syncthing GUI at
`https://syncthing.rafael.media` without changing its
`127.0.0.1:8384` listener or exposing it publicly. Read-only inspection on
2026-07-25 found:

- PVE 9.1.2, all ZFS pools, CT110, Syncthing, Pi-hole, and NPM healthy;
- Syncthing listening only at `127.0.0.1:8384`, with no GUI username or
  password configured;
- no NPM row for `syncthing.rafael.media`;
- the hostname already resolving locally through Pi-hole's existing
  `rafael.media` wildcard, but no exact local record;
- the daily appdata service with result `success` and the timer active;
- about 485 GiB free in `rpool/appdata/docker`.

This routine configuration change did not start an on-demand PBS backup.
Before mutation, byte-matched or SQLite-integrity-checked focused rollback
copies were retained under stamp `20260725T183420Z`:

```text
/root/.env.pre-syncthing-gui-20260725T183420Z
/srv/appdata/docker/syncthing/config/config.xml.pre-syncthing-gui-20260725T183420Z
/srv/appdata/docker/pihole/etc-pihole/pihole.toml.pre-syncthing-gui-20260725T183420Z
/srv/appdata/docker/infra-nginx-proxy-manager/database.sqlite.pre-syncthing-gui-20260725T183420Z
```

The environment and NPM copies are root-owned mode `0600`. The Syncthing and
Pi-hole copies preserve their original ownership and modes.

## Reproducible implementation

Commit `55013870bc0c4291b7ca1fc1af7781fdaefa6303` added:

- `SYNCTHING_GUI_USERNAME` and `SYNCTHING_GUI_PASSWORD` as required recovery
  variables, plus a one-time initializer that creates missing values in
  `/root/.env` without printing them;
- Syncthing REST configuration that sets static GUI authentication, requires a
  strong source password, keeps insecure admin access disabled, and verifies
  that Syncthing stored a bcrypt hash rather than plaintext;
- an exact managed Pi-hole record for
  `syncthing.rafael.media -> 192.168.0.110`;
- a managed NPM route to `http://127.0.0.1:8384` with the existing wildcard
  certificate, forced HTTPS, HTTP/2, WebSockets, LAN/Tailscale allow rules, and
  a final `deny all`;
- bootstrap ordering and focused verification for DNS, authentication,
  loopback binding, TLS, route policy, and application health.

Syncthing is still the only process listening on CT110 loopback port 8384.
NPM can reach that listener because it uses host networking. No new router
forward, Cloudflare DDNS name, public NPM policy, or non-loopback Syncthing bind
was added.

## Live evidence

The commit was fast-forwarded to PVE and synced to CT110. The live result is:

- Pi-hole returns exactly `192.168.0.110` and retains a dedicated exact
  `dns.hosts` record in addition to the pre-existing wildcard;
- NPM proxy-host ID 54 uses `http`, `127.0.0.1`, port 8384, certificate ID 11,
  forced TLS, WebSockets, and the exact LAN/Tailscale/deny policy;
- NPM SQLite integrity is `ok` with 54 proxy hosts and six certificates, and
  `nginx -t` passes;
- HTTPS returns 200 with certificate verification result 0 through both
  `192.168.0.110` and Infra's Tailscale address;
- a request originating from Pi-hole's Docker subnet, which is outside the two
  allow ranges, returns HTTP 403;
- public DNS-over-HTTPS sees the pre-existing wildcard answer, but the
  Cloudflare DDNS domain set excludes `syncthing.rafael.media`;
- an unauthenticated protected Syncthing REST request returns 403;
- the recovery username matches the configured user and the recovery password
  verifies against Syncthing's stored bcrypt hash, without either value being
  displayed;
- the full Infra verifier and focused Syncthing verifier pass. The three Proton
  generations remain pending, as before this task.

## Homarr, Pulse, and WUD integration

Commits `c1b2361d15386f27ec476f36690eb5abbaa21ab3` and
`c58888efc9496d9db4af5f57559cbd4199e6e178` add the Syncthing instance to the
three management surfaces:

- Homarr has deterministic Syncthing tiles on the `dashboard`, `Admin`, and
  `default` boards, all linking to `https://syncthing.rafael.media`. Tile ping
  is disabled because Homarr's bridge network must not bypass the
  LAN/Tailscale NPM allowlist to reach the loopback-only GUI.
- Pulse continues to discover Syncthing through CT110's command-disabled
  Docker agent, and its verifier now explicitly requires
  `infra/syncthing` to be online even if the container is absent from the
  current `docker ps` inventory.
- Syncthing remains enrolled in WUD's `docker.backupgated` trigger. The
  sequential runner now checks `http://127.0.0.1:8384/rest/noauth/health`
  after replacing the container.

The first live Homarr reconciliation exposed a pre-existing idempotency defect:
fourteen dashboard tiles already lived in a non-first section, so the old SQL
inserted duplicate placements into the first section and rejected the result
at `133` rows instead of `119`. Homarr remained healthy. The failed state was
retained, the verified pre-change SQLite copy was restored, and the
reconciler was changed to reuse an existing section per item and layout. The
exact corrected SQL was applied twice to a copy of the rollback database; both
passes retained SQLite integrity, one Syncthing app, three tiles, `119`
managed layout rows, and zero per-board layout mismatches.

Final live verification showed:

- Homarr healthy with 17 managed apps, 51 managed items, 119 layout rows, the
  exact private Syncthing URL, and `pingEnabled=false` on all three tiles;
- Pulse inventory converged with `infra/syncthing` online;
- WUD discovered `infra/syncthing` under `docker.backupgated`, with all 39
  currently watched containers associated with that trigger and no eligible
  update;
- the focused Syncthing verifier and full Infra verifier passed.

Focused Homarr rollback evidence is retained root-only:

```text
/srv/appdata/docker/homarr/db.sqlite.pre-syncthing-homarr-20260725T185603Z
/srv/appdata/docker/homarr/db.sqlite.failed-syncthing-homarr-20260725T185603Z
```

## Rollback boundary

Keep all four focused copies until a later verified recovery or an explicitly
authorized cleanup. If this route must be rolled back, first retain the failed
state, then restore only the exact NPM/Pi-hole/Syncthing files above while
their owning service is stopped, reload DNS/Nginx, and verify the restored
SQLite/config integrity before resuming service. Restore the environment copy
only when intentionally rolling back the generated GUI credentials as well.

Do not delete the Syncthing appdata directory, Obsidian vault, version store,
NPM certificate directory, or unrelated Pi-hole/NPM rows. This rollout did not
perform a destructive clean-host rebuild, a full appdata restore, device
pairing, Proton authentication, or Proton restore testing.

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

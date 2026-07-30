# cross-seed download repair evidence — 2026-07-30

## Result

cross-seed searches and injects complete private-tracker matches again.
BTSchool and RailgunPT remain authenticated and searchable in Prowlarr, while
a private compatibility proxy now completes their required NexusPHP download
confirmation. HDClone remains on its direct Prowlarr Torznab endpoint.

A controlled webhook for an already complete qBittorrent movie found an exact
BTSchool match and injected it:

```text
source hash prefix:   bf0303aa
matched hash prefix:  7d0a4cfb
match:                MATCH
result:               injected
recheck remaining:    0 B
qBittorrent progress: 1
qBittorrent state:    stalledUP
category:              cross-seed-link
save path:             /data/torrents/cross-seed-links/BTSchool
```

The temporary `stoppedUP` state observed immediately after injection was the
mandatory hash-check window. Ninety seconds later cross-seed logged the
zero-byte resume, and the subsequent qBittorrent API check returned
`stalledUP`: complete, resumed, and waiting to upload.

## Root cause

Both trackers returned HTTP 200 HTML from their protected `download.php`
links. The page contained a POST confirmation with the torrent ID,
`type=firsttime`, `hidenotice=1`, and the site's localized submit value.
Submitting that exact form to the original URL returned a valid private
torrent in a redirect response body.

Prowlarr's Cardigann `download.before` path performs the confirmation request
but does not use its response body as the downloaded torrent. It then repeats
the original GET, receives the HTML notice again, and reports
`Invalid torrent file`. Therefore changing credentials, cookies, cross-seed
matching, or qBittorrent could not fix the failure.

## Implemented recovery contract

The `cross-seed` Compose project now includes
`cross-seed-prowlarr-proxy`. It is reachable only inside Gluetun's Docker
network namespace on port 9697; it has no CT102 host port or NPM route. The
proxy uses read-only Prowlarr state to:

1. authenticate the same Torznab request and proxy the Prowlarr search;
2. rewrite only the selected indexer's protected Prowlarr download URLs;
3. decrypt a protected link in memory with Prowlarr's existing
   `downloadprotectionkey`;
4. require the configured HTTPS host, port, exact `download.php` path, and one
   numeric torrent ID;
5. GET the tracker URL with Prowlarr's current session cookies;
6. accept and POST only the exact confirmation form; and
7. return only a bounded, structurally valid bencoded torrent containing an
   info dictionary and announce field.

No credential, cookie, protected URL, form data, API key, tracker passkey, or
announce URL is logged or persisted by the proxy. It runs as UID/GID
`1000:1000` from a digest-pinned Python 3.13 Alpine image with a read-only root
filesystem, a 16 MiB temporary filesystem, all capabilities dropped, and
`no-new-privileges`. WUD is disabled for this manually reviewed support image.

Two deterministic custom Cardigann identities are derived at deployment from
Prowlarr's installed BTSchool and RailgunPT definitions. The reconciler fails
closed if their download selector, identity, or unexpected native download
block changes. Existing numeric indexer IDs are migrated in place through
Prowlarr's force-save API without a tracker login. Bootstrap performs this
definition reconciliation before rendering cross-seed's Torznab endpoints.

## Rollback and verification

Before the repair, an online Prowlarr SQLite backup, `config.xml`, bundled
definitions, and checksums were retained at:

```text
/docker/prowlarr/Backups/codex-manual/2026-07-30T071348Z-cross-seed-download-notice
```

The SQLite backup passed `quick_check`. Three pre-change cross-seed config
copies were retained below `/docker/cross-seed/backups/codex-manual`. The
scheduled appdata backup service had a successful result before this task; no
on-demand PBS job was justified because the live mutation was limited to
reproducible definitions, configuration, and a stateless support container.

Focused acceptance included:

- successful BTSchool and RailgunPT Prowlarr login/search tests;
- deterministic custom-definition activation and configured-ID checks;
- a known-vector AES-256-CBC decryption check in the live proxy image;
- direct proxy retrieval of a 164,622-byte validated BTSchool torrent;
- the exact complete-torrent injection, recheck, zero-byte resume, and live
  qBittorrent state shown above;
- Compose rendering, container health/security/mount policy, private
  connectivity, strict cross-seed configuration, and deployed-commit checks.

Rollback stops only the `cross-seed` Compose project. Retain canonical
`/docker/cross-seed`, the Prowlarr rollback directory, and
`/vault/shared/torrents/cross-seed-links`; the hardlink tree is durable shared
data, not disposable cache.

Official references:

- <https://www.cross-seed.org/docs/basics/options>
- <https://www.cross-seed.org/docs/reference/api>
- <https://github.com/Jackett/Jackett/wiki/Definition-format>

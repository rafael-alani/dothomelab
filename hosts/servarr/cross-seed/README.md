# cross-seed

cross-seed v6 runs as its own Compose project on CT102. It searches the
existing qBittorrent catalogue against only BTSchool, RailgunPT, and HDClone
through their individual Prowlarr Torznab endpoints, then injects verified
matches back into the existing qBittorrent client.

## Safety and matching policy

- `matchMode: "strict"` requires exact filenames.
- `skipRecheck: false` forces qBittorrent to hash-check every injection.
- `autoResumeMaxDownload: 0` leaves any torrent needing data paused.
- `action: "inject"` and `linkType: "hardlink"` create tracker-specific trees
  below `/data/torrents/cross-seed-links`.
- `linkCategory: "cross-seed-link"` prevents the Arr import queues from
  treating injected copies as new downloads.
- One search is issued at most every 60 seconds. Each daily batch is limited
  to 50 search queries per indexer, and RSS polling runs hourly.
- Single-episode searches and synthesized season packs are disabled. Exact
  non-video torrent matches remain eligible.

The service uses qBittorrent client discovery rather than mounting its
`BT_backup` directory. Both containers see `/data` at the same path, which is
required for hardlink injection. The daemon API is reachable only on the
private `servarr-hello_default` network; no CT102 port or NPM route is
published.

## NexusPHP download compatibility

BTSchool and RailgunPT return an HTML confirmation form from `download.php`
before returning the private torrent. Prowlarr can search and authenticate
these trackers, but its Cardigann pre-download action discards the form POST
body and repeats the original GET. That made cross-seed receive Prowlarr's
`Invalid torrent file` response even though both indexer tests passed.

The `cross-seed-prowlarr-proxy` support container is a stateless compatibility
boundary for only those two indexer IDs. It shares Gluetun's network namespace
and publishes no host port. It:

- proxies their Torznab searches and rewrites only Prowlarr download links;
- reads Prowlarr's config, database, and tracker session through a read-only
  appdata mount;
- decrypts Prowlarr's protected download URL in memory, then requires the
  configured HTTPS tracker host, exact `download.php` path, and one numeric ID;
- accepts only the exact first-download confirmation form and returns only a
  size-bounded, structurally valid torrent dictionary;
- never logs the protected URL, cookies, API key, form values, or announce URL.

The Python base is pinned by digest, manually updated, runs as `1000:1000`
with a read-only root filesystem, no capabilities, and
`no-new-privileges`. The custom Prowlarr definitions have deterministic IDs so
upstream definition refreshes cannot replace this narrow compatibility path.
`configure-prowlarr-cross-seed-definitions.sh` derives them from the installed
bundled definitions, fails closed on relevant upstream drift, activates them,
and migrates the existing indexer rows without a login request.

Run the proxy's network-free parser and allowlist tests with:

```bash
python3 /opt/dothomelab/hosts/servarr/cross-seed/test_prowlarr_download_proxy.py
```

## Credentials and reconciliation

Production tracker credentials remain only in Proxmox `/root/.env` and
Prowlarr's protected appdata. `configure.py` creates or reconciles the three
Cardigann indexers with freeleech-only disabled and unlimited seed ratio/time:

| Indexer | Prowlarr priority | Credential variables |
|---|---:|---|
| BTSchool | 1 | `BTSCHOOL_USERNAME`, `BTSCHOOL_PASSWORD` |
| RailgunPT | 2 | `RAILGUN_PT_USERNAME`, `RAILGUN_PT_PASSWORD` |
| HDClone | 3 | `HDCLONE_TOP_USERNAME`, `HDCLONE_TOP_PASSWORD` |

Optional `RAILGUN_PT_2FA_CODE` and `HDCLONE_TOP_2FA_CODE` values are accepted
when those accounts have site 2FA enabled. cross-seed's mode-0600 `config.js`
contains only the Prowlarr API key and the three numeric Torznab endpoints; it
never contains tracker usernames or passwords.

Prowlarr still tests an enabled indexer on initial creation even with
`forceSave`. The reconciler therefore creates all three indexers disabled.
No tracker request is made during this step, and `deploy.sh` creates but does
not start the cross-seed container.

Complete each CAPTCHA/login test manually in the Prowlarr UI, save all three
indexers enabled, and then run:

```bash
pct push 102 /root/.env /run/dothomelab.env --perms 0600
pct exec 102 -- env DOTHOMELAB_ENV=/run/dothomelab.env \
  /opt/dothomelab/hosts/servarr/cross-seed/approve.sh --manual-tests-passed
pct exec 102 -- rm -f /run/dothomelab.env
```

The approval command verifies locally that the tested resources are enabled
with the expected accounts. It then uses Prowlarr's force-save path, without a
tracker request, to normalize their names, priorities, freeleech setting, and
unlimited seeding policy. It writes a mode-0600 marker in canonical appdata
and starts the prepared project. Future appdata restores retain that marker
and can start the service without repeating initial account setup. The
separate `configure.py --test` mode exists for an explicitly requested,
single-shot Prowlarr test, but bootstrap and approval never invoke it.

## Persistence and recovery

Application configuration, logs, the generated API key, the manual approval
marker, and cross-seed's SQLite state live under `/docker/cross-seed`, backed
by canonical appdata and the normal encrypted appdata job. The hardlink tree is under
`/vault/shared/torrents/cross-seed-links`, outside appdata PBS. It is not a
disposable cache: if another hardlink is later removed, a link in this tree
may be the remaining reference to those bytes.

Rollback stops only this Compose project:

```bash
docker compose -f /opt/dothomelab/hosts/servarr/cross-seed/compose.yaml down
```

Retain both `/docker/cross-seed` and the shared link tree. Do not delete links
while the corresponding qBittorrent torrents remain loaded.
Stopping the project also stops the stateless compatibility proxy; it does not
alter Prowlarr's tracker sessions or remove its custom definition files.

Official references:

- <https://www.cross-seed.org/docs/basics/getting-started>
- <https://www.cross-seed.org/docs/tutorials/injection>
- <https://www.cross-seed.org/docs/tutorials/linking>
- <https://www.cross-seed.org/docs/basics/options>

# Listenarr addition evidence — 2026-07-28

## Outcome

Listenarr is deployed and healthy on CT102 as the homelab's sole audiobook
acquisition and organization service. Its authenticated private interface is
`https://listenarr.rafael.media`. Shelfarr remains the sole ebook organizer and
now sees canonical audiobooks read-only.

The deployment is reproducible from Git: bootstrap creates the recovery
secrets, prepares appdata and download paths, validates the Compose model,
starts Listenarr, reconciles its supported API state, configures the dedicated
qBittorrent category, and verifies the service, route, dashboard, storage,
backup, and update contracts.

## Upstream and version decision

Upstream did not publish a stable release at implementation time. The
repository therefore pins Canary 1.2.2 at the reviewed image digest:

```text
ghcr.io/listenarrs/listenarr:canary-1.2.2@sha256:7aa44d67b649cd401507b763733f93e90ea4f12e2001e2bc67e31199366bb3a9
```

`wud.watch=false` excludes it from automated replacement. A future update is a
manual compatibility task requiring release-note and database-migration
review, current rollback, and focused search, client, and import verification.

## Preflight, data risk, and rollback

Before deployment:

- the PVE appdata backup timer was active and its latest completed unit result
  was successful;
- CT102 ran 19 containers in six Compose projects;
- canonical audiobooks were owned by mapped application UID/GID `1000:1000`
  with mode `0750`;
- Listenarr appdata and its dedicated qBittorrent path did not exist;
- the media contract and existing Shelfarr, Prowlarr, qBittorrent, NZBGet,
  Pi-hole, NPM, and Homarr state were inspected read-only.

The following focused ZFS rollback snapshots were created and retained:

```text
rpool/appdata/docker@pre-listenarr-20260728T204805Z
vault/shared@pre-listenarr-20260728T204805Z
```

The shared-data snapshot was compared after acceptance. Its only differences
were directory-metadata changes in Shelfarr's existing staging tree:

```text
/vault/shared/media/audiobooks/.shelfarr-staging
/vault/shared/media/audiobooks/.shelfarr-staging/direct-downloads
/vault/shared/media/audiobooks/.shelfarr-staging/direct-downloads/84e0fc74cf91
```

There were no canonical non-staging file changes and no audiobook file
changes. The snapshots are rollback assets, not backups against loss of the
`vault` pool, and require a separately reviewed restore before use.

## Ownership and storage

The implemented ownership contract is:

- Listenarr alone acquires and organizes canonical audiobooks.
- Shelfarr alone organizes canonical ebooks and has read-only audiobook
  visibility for inventory and rollback compatibility.
- Audiobookshelf remains the review-gated canonical audiobook metadata and
  cover writer.
- Grimmory sees audiobooks read-only and remains the canonical EPUB metadata
  writer.

Listenarr publishes to `/vault/shared/media/audiobooks` through its
`/audiobooks` root. qBittorrent uses the dedicated completed path
`/data/torrents/completed/listenarr`; NZBGet uses the existing `Books`
category. Import preserves seeding through hardlink or copy. Listenarr
metadata and cover embedding are disabled so it cannot compete with
Audiobookshelf.

Application state, data-protection keys, and online SQLite recovery copies are
under `/srv/appdata/docker/listenarr`. Canonical audiobook files remain under
`/vault/shared` and are outside the encrypted appdata PBS job.

## Authentication and integration

Authentication was rendered before the first listener started. The generated
administrator password and API key are present only in the mode-0600 production
`/root/.env`; no production secret is stored in Git or in this evidence.

The live supported configuration reconciles:

- one canonical `/audiobooks` root using `{Author}/{Title}`;
- one M4B-first quality profile;
- the existing qBittorrent and NZBGet download clients with exact container
  paths;
- qBittorrent category `listenarr`;
- NZBGet category `Books`;
- 19 Prowlarr indexers;
- five audiobook-category (`3030`) indexers enabled for automatic/RSS search;
- generic category `3000` book sources retained for interactive searches only.

The Listenarr API does not expose persisted client download paths. The
reconciler therefore verifies those exact fields through read-only SQLite
queries after using the supported API for configuration.

## Private route and dashboard

Pi-hole resolves `listenarr.rafael.media` to NPM at `192.168.0.110`. NPM proxy
host 64 terminates the real certificate, forwards to CT102 port 4545 with
WebSockets, and allows only LAN/Tailscale ranges before `deny all`.

The HTTPS UI and bootstrap endpoint return HTTP 200 with certificate
validation. Unauthenticated access to protected configuration returns HTTP
401. Homarr contains one deterministic Listenarr app, three board items, and
eight layout placements. NPM and Homarr SQLite integrity checks pass.

## Recovery and update protection

The PVE pre-backup hook invokes Listenarr's online SQLite backup before the
normal appdata snapshot. It retains latest and previous copies with hashes and
requires `PRAGMA integrity_check=ok`. The live database and current recovery
copy both passed integrity verification.

The application remains excluded from WUD. Its exact digest, startup
configuration, canonical mounts, authentication, API settings, client paths,
indexer policy, qBittorrent category, Shelfarr read-only audiobook mount, and
recovery copy are checked by the focused verifier.

## Acceptance evidence

The completed live acceptance established:

- CT102 has 20 healthy containers in seven Compose projects;
- the complete homelab has 75 running containers in 37 Compose projects;
- Listenarr is healthy on the exact pinned image with zero current restarts;
- one root folder, one quality profile, two download clients, 19 indexers, and
  one administrator exist;
- five category-3030 indexers are automatic and no generic category-3000
  indexer is automatic;
- a non-downloading `Alice in Wonderland Lewis Carroll` metadata query returned
  47 results with the expected title among the leading matches;
- a category-3030 indexer search returned 9 release results and 49 metadata
  results;
- DNS, real-certificate HTTPS, authentication, NPM, Homarr, qBittorrent,
  online SQLite backup, Shelfarr isolation, and the full live media contract
  pass;
- no temporary production environment copy remained on PVE, CT102, or CT110;
- no audiobook was grabbed merely to satisfy deployment acceptance.

## First-boot observation

On the first boot, two upstream background workers raced to insert the same
singleton application-settings row after successful migrations. Three
error-level log lines recorded the resulting unique-constraint conflict. The
database remained integral, supported configuration completed, and the service
was healthy.

Listenarr was restarted once after reconciliation. The settings persisted,
the complete configuration check passed, and there have been zero error-level
lines since that clean restart. This is retained as an upstream first-boot
observation rather than treated as hidden or unresolved data corruption.

## Rollback

Rollback is intentionally scoped:

1. Stop only the Listenarr Compose project.
2. Revert the Git declaration and resync CT102/CT110.
3. Restore Listenarr appdata or the broad snapshots only after inspecting the
   exact target and confirming that no newer unrelated application or media
   state would be lost.
4. Restore Shelfarr's prior audiobook write permission only if explicitly
   choosing to return audiobook organization ownership to Shelfarr.

The retained snapshots and previous Git commits provide rollback inputs. They
are not authorized for deletion by this rollout.

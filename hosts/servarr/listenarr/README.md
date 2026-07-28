# Listenarr

Listenarr is the only audiobook acquisition and file-organization service. It
provides audiobook-first Amazon, Audible, and Open Library discovery, sends
downloads to the existing qBittorrent and NZBGet instances through Gluetun,
and publishes imports to `/vault/shared/media/audiobooks`.

The deployment pins upstream Canary 1.2.2 at an exact OCI digest because
Listenarr does not currently publish a stable release. It is deliberately
excluded from WUD and must be updated manually after release-note review, an
appdata snapshot or current PBS backup, and focused client/import verification.

`render-config.py` enables authentication before the first listener starts.
`configure.py` reconciles the administrator, canonical `/audiobooks` root,
quality profile, dedicated qBittorrent category, shared NZBGet Books category,
and Prowlarr indexers. Only category 3030 indexers are enabled for automatic
search; generic book sources remain interactive-only.

Listenarr organizes files but does not embed tags or cover art.
Audiobookshelf remains the review-gated canonical audiobook metadata writer.
Shelfarr retains read-only audiobook visibility for inventory and rollback,
while its canonical write scope is ebooks only.

The SQLite database and data-protection keys persist below
`/srv/appdata/docker/listenarr`. `backup-database.sh` creates integrity-checked
latest and previous SQLite recovery copies before each appdata snapshot.
Canonical audiobook files are on `/vault/shared` and are not included in the
appdata PBS backup.

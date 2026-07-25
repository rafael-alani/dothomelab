# DroppedNeedle

The `droppedneedle` project runs the upstream
`droppedneedle/droppedneedle:latest` image on Apps port 8688. Nginx Proxy
Manager publishes `https://droppedneedle.rafael.media` only to the LAN and
Tailscale. The application requires its own administrator account during the
first-run wizard.

Configuration, SQLite databases, cover-art/cache data, plugins, and manual
imports persist below `/srv/appdata/docker/droppedneedle`. The existing music
library is mounted read-write at `/music`; slskd completed downloads are
mounted at `/slskd-downloads/complete`. The paths use the same `vault/shared`
filesystem. They remain separate narrow container mounts, so DroppedNeedle may
use its documented copy-and-remove fallback instead of an atomic rename and
can briefly require space for both copies. This is intentional: mounting all
of `/vault/shared/media` read-write would expose unrelated photos and video.

After first login:

1. configure `/music` as the library and run a scan;
2. configure `http://slskd:5030` as the download client;
3. enter the `SLSKD_API_KEY` value from the production `/root/.env`;
4. confirm the download mount is writable, then test a permitted download and
   completed import.

The upstream `latest` image is the documented production channel. Its startup
path makes upgrade backups of the SQLite/settings state and validates a
working copy before background workers start. DroppedNeedle is therefore
enrolled in backup-gated WUD, with the PVE appdata snapshot completing first
and a direct `/health` check required after replacement. Music and completed
downloads remain outside PBS appdata backup and need separate protection.

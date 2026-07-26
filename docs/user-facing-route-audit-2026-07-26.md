# User-facing route and Homarr audit — 2026-07-26

## Scope

The audit compared live Docker containers in CT102, CT110, and CT112 with
live Homarr applications and Nginx Proxy Manager rows. Databases, caches,
agents, workers, API-only companion services, duplicate public aliases, and
the deliberately retired DroppedNeedle route were excluded.

## Cleanuparr change

Cleanuparr 2.10.0 was healthy at `192.168.0.102:11011`, but had neither an NPM
row nor a Homarr application. The repository now declares:

- exact Pi-hole DNS for `cleanuparr.rafael.media` to Infra;
- an NPM TLS route to CT102 port 11011, restricted to LAN and Tailscale;
- one managed Homarr application and a tile on each of `dashboard`, `Admin`,
  and `default`;
- a direct Homarr health ping to `/health`, while the UI retains its native
  username/password authentication.

The route is private and is not added to the router or public DDNS set.

## Other findings

| Application | Live state | Homarr | NPM | Finding |
|---|---|---|---|---|
| NZBGet | Authenticated UI returns HTTP 401 at CT102 port 6789 | Missing | Missing | Genuine user-facing omission; safe candidate for a separate private route/tile change. |
| Proxmox Backup Server | UI listens on CT113 `192.168.0.159:8007` | Missing | Present but targets stale `192.168.0.113:8007` | Existing route is broken and should be corrected with a focused PBS route/tile change. |
| WUD | HTML UI is healthy on CT110 loopback port 3001 | Missing | Missing | Intentional: WUD has no native authentication and its policy forbids direct LAN exposure. Add only with an authenticated proxy design. |

Zotero WebDAV, Obsidian/CouchDB, Bar Assistant API/search, FlareSolverr,
Soularr, Shelfarr Libation, the Storyteller reconciler, music-metadata, Docker
agents, and application databases/caches are service endpoints or supporting
components rather than dashboard applications. Public Immich, Jellyfin, and
Wizarr aliases map to applications that already have private Homarr entries.


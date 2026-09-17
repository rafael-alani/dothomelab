# ImmichFrame repair — 2026-09-17

The v1.0.38.0 container was restarting with SQLite error 14 because its
previously empty config bind was guest-root-owned, mode 0755. The image runs
as UID 1000. Changing only the directory owner stopped the crash, but exposed
a second problem: this release no longer reads account configuration from
`ImmichServerUrl` and `ApiKey` environment variables. The root UI returned
HTTP 200 even with no configured accounts.

The [upstream release](https://github.com/immichFrame/ImmichFrame/releases/tag/v1.0.38.0)
introduces SQLite-backed admin configuration. The repair makes preparation
create the config directory as guest 1000:1000, mode 0700. A Compose entrypoint
provides the existing scoped key through a private runtime file and seeds the
upstream-supported JSON import. The imported database references that file;
future starts recreate it from the recovery environment without overwriting
persisted settings. No new production secret is required. Admin editing stays
disabled and the existing private NPM route is retained.

## Verification

- PVE pools healthy; scheduled appdata backup service reported success at
  02:11:38 CEST. No on-demand backup or restore test was performed.
- Inspected CT112 mounts, host/guest numeric ownership, directory contents and
  runtime UID before permission changes. Config was empty before recovery;
  the newly initialized database contained zero settings rows before import.
- Shell syntax checks and `git diff --check` passed; production Compose
  validation passed before replacing only ImmichFrame.
- Upstream imported one account, connected to Immich v3.0.3, and passed SQLite
  `quick_check`, scoped API-key validation and canonical-storage verification.
- Slideshow API returned 25 assets; an asset request returned a non-empty
  image. Both checks passed again after restart with the persisted database.
- Container running with zero automatic restarts; DNS resolves the private
  hostname to `192.168.0.110`; certificate-validated HTTPS returned 200.
- The image remained
  `sha256:26d2c50bd05d5472c8fe4e535ea3312ae78689c07c5cfde524b41536a727dc0b`.

## Recovery and rollback

Restore the entire config directory and `/root/.env`, then run normal
bootstrap preparation and Compose deployment. Retain SQLite/WAL state; do not
delete it to force another import. The old Git archive is retained as
`/opt/dothomelab.previous` during deployment, and no old image was pruned.
Reverting this patch alone recreates the v1.0.38 failure; any application
downgrade requires a reviewed compatible image and retained config rollback.
The legacy JSON import is deprecated upstream; review its replacement before
adopting a release that removes it. Browser/device rendering and a destructive
clean-host rebuild were not tested in this repair.

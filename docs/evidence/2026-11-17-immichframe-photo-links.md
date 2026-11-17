# ImmichFrame photo links — 2026-11-17

CT112 runs ImmichFrame v1.0.40.0, recreated at 02:21 CET on November 17.
Its browser bundle hard-coded `https://my.immich.app/photos/` for both the
photo link and QR code. This was reproduced through fresh HTTP responses and
the HTTPS browser Info panel. Saved SQLite account settings only specify the
internal API URL; there was no persistent link override in the deployed Git
revision `d3d917b`. A prior manual fix could not be established from this evidence.

## Repair and checks

Published and deployed `31f129ecfce3e8cebc787b04ec52c2a21b974f1f` on
`codex/immichframe-photo-links`. The entrypoint reapplies the exact photo URL
prefix replacement at every startup, including WUD container replacements.
It regenerates gzip and removes the old Brotli bundle sibling. Unknown future
bundle layouts stop startup for review instead of silently restoring bad links.
See the [service runbook](../../hosts/apps/immichframe/README.md).

- The exact reported asset URL assertion failed before deployment and passed
  afterward against the JavaScript served over private HTTPS.
- Local tests cover replacement, compressed siblings, repeated startup and
  changed upstream layout. Shell syntax, diff whitespace and documentation
  checks passed. A disposable network-isolated container using the production
  image passed two patch invocations without appdata or credentials mounted.
- Production Compose validation passed before recreating only ImmichFrame,
  using `--pull never`. Image remained
  `sha256:09925f5bca2cfb7e5e491cd2bc65706a8f36e8672f1b75c28a50e9800018802c`.
- `verify.sh` passed against direct HTTP and private HTTPS: correct link prefix
  for identity/gzip/Brotli negotiation, SQLite integrity, credential scope,
  canonical storage, WUD policy, 25 slideshow assets and non-empty image delivery.
- A fresh browser origin displayed an actual `pictures.rafael.ink/photos/…`
  link. An already-open HTTPS tab retained the old immutable JavaScript after
  ordinary reload; existing clients need a hard refresh/cache refresh once.
- Guest `DEPLOYED_COMMIT` matched the repair; container running with zero
  automatic restarts. Scheduled appdata backup succeeded at 02:18:51 CET.

## Limits and rollback

No image upgrade, photo modification, SQLite edit, credential change, database
migration, new backup or restore test was performed. Authenticated destination
photo viewing, external-network access and phone QR scanning were not tested.
The link and QR component share the verified URL builder.

The preceding guest archive is retained at `/opt/dothomelab.previous`; its
older predecessor was preserved at
`/opt/dothomelab.previous-before-immichframe-20261117`. Roll back by restoring
the preceding service Compose/entrypoint and recreating ImmichFrame with the
retained image after quiet Compose validation. That restores the upstream
redirect behavior; no durable-data rollback is required for this change.

[Back to evidence index](README.md)

# Mealie

Mealie serves the existing recipe collection on CT112 port 9925 through the
private `https://mealie.rafael.media` route. Canonical state, including its SQLite
database and uploaded recipe files, is `/srv/appdata/docker/mealie`, mounted at
`/app/data`. Signups remain disabled. Current image baseline and resource limits
live in `compose.yaml`.

Stable image updates use the backup-gated WUD path. `verify.sh` requires a healthy
container, the managed project/update association, an API version matching the
running stable image tag, SQLite integrity, and nonempty recipe/user tables.
It must not hardcode an older release after WUD updates the image. The November 5
check was corrected from a stale 3.21.0 assertion while the healthy service ran
3.30.0; no recipe data or runtime settings needed changing.

Recovery uses canonical appdata and a compatible image version. A newer schema
must not be blindly opened with an older retained image; use the matching backup
and release for rollback. Container health and recipe counts do not replace
browser acceptance of importing, editing or cooking a recipe.

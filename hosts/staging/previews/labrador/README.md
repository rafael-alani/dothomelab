# Labrador previews

This recipe consumes each selected Skill Circuits snapshot's existing
`end_to_end/compose.yml`, `docker/Dockerfile` and
`docker/labracore/Dockerfile`. It does not add infrastructure commits to feature
branches. LabraCore and Skill Circuits retain the upstream combined application
image. The generated override isolates MySQL storage, assigns one private web
port, disables optional Jaeger, sets resource limits and keeps source mounts
read-only. The source Compose file is the first `-f` input; the generated
`compose.override.yaml` is second. Compose 2.24.4 or newer is required for
`!override` port replacement.

## Build inputs

The runner supplies `BRANCHLINE_SOURCE`, `BRANCHLINE_PREVIEW_DIR`,
`BRANCHLINE_PREVIEW_ID`, `BRANCHLINE_SHA`, `BRANCHLINE_PORT` and the unique
`COMPOSE_PROJECT_NAME`. Configure `LABRADOR_ARTIFACTS` as the absolute retained
dependency-bundle directory and `LABRADOR_BIND_IP` as the staging LAN address.
`LABRADOR_APP_MEMORY` and `LABRADOR_APP_CPUS` default to `2g` and `2`.
`LABRADOR_JAVA_IMAGE` and `LABRADOR_NODE_IMAGE` select the Java 21 and Node 24
builder images; deployment should pin their verified registry digests.

`prepare.py` verifies every dependency and LabraCore source hash against the
bundle's `manifest.json`. It compiles the exact Java sources with Java 21 and
packages the current resources and frontend. It never reuses old application
classes. Private dependency JARs are prepared offline; compilation and Vite
execution have no network. npm installation permits only locked public npm
registry artifacts and disables lifecycle scripts. Project Gradle scripts and
GitLab are never invoked. The existing Core Dockerfile's remote clone is
replaced only in the generated build context with the locally compiled artifact.

The bundle belongs at
`/srv/appdata/docker/staging/branchline-artifacts/labrador/artifacts` on CT114.
It contains `dependencies/core`, `dependencies/skills`, `core-source` and a
hash manifest. Core source excludes application configuration; configuration
comes from the selected Skill Circuits recipe. Retain the bundle as a recovery
input, outside Git. A new dependency or Core revision requires a new reviewed
manifest and runner recipe revision; an incompatible source fails compilation.
The selected `build.gradle.kts` must match the bundle's accepted build-contract
hashes, so dependency changes cannot silently compile against an older bundle.
`build-provenance.json` records the actual application revisions, recipe,
dependency manifest and source Compose hash for each environment.

## Data and lifecycle

The existing E2E SQL scripts initialize the two MySQL schemas and fixture
identities. The existing `e2e` login behaviour uses fixture accounts; previews
must remain private. No production data or integrations are supplied. The
application seeds Core once, recorded in the environment's `seed-state`
directory. Restart retains both that marker and the MySQL directory. An explicit
reset must treat both together; stopping a preview never deletes either.

**Preview MySQL uses `lower_case_table_names=1` from its first initialization.**
Historical Skill Circuits migrations mix uppercase and lowercase table names;
the final stack fails on a default case-sensitive Linux MySQL instance when
creating an index on `BOOKMARK_LIST`. The explicit preview setting preserves
the selected application commit and permits those historical snapshots to run.
It does not establish migration compatibility with a case-sensitive production
database. Never apply this setting to an already initialized data directory;
retain the old environment and allocate a fresh one.

MySQL runs as UID/GID 999 with dropped capabilities. Preparation changes only
the newly allocated environment's MySQL directory ownership. A clean build
uses bounded disposable containers; cancellation stops the named builders.
The application runtime and database are managed by the preview runner, not
started by preparation. Validate the merged Compose quietly before every start.

## Verification

Run `python3 hosts/staging/previews/labrador/test_prepare.py`. Actual acceptance
also requires a Docker build, merged-policy validation, real MySQL migrations,
fixture login and UI checks, and a restart with unchanged database records.
Local Java compilation alone does not establish those runtime behaviours.

# Labrador preview administrator fixture

On 2026-11-23 Rafael authorized adding an admin fixture to the preview recipe
and the existing `285-01-track-navigation` preview. Its E2E seed lacked `admin1`;
the teacher account existed. This was a dataset difference from development.

## Change and identities

The [recipe](../../hosts/staging/previews/labrador/README.md#data-and-lifecycle)
copies the original Core SQL seed into each new preview, appending an idempotent
`admin1` ADMIN fixture. It does not overwrite an existing username. Application
branches and the pinned Core/dependency bundle are unchanged.

- Homelab code: `df21c435abb3676e8ecd07bd08d593b7c501252f`, review branch
  `codex/labrador-preview-admin`.
- Installed recipe: `768fcf4b1ea5f2a3539e571f7f409889ad82a086df78a20e873dbf66f4d63f7b`;
  `/opt/branchline-recipes/<revision>/DEPLOYED_COMMIT` records the source commit.
- Existing preview: `331080b1be-dacfac77`, application commit
  `331080b1be2ef7fc59cd0407dfe0f26183f21187`,
  [private HTTPS URL](https://bl-12004.staging.rafael.media).

Only this existing preview received the additive SQL. Older previews retain
their original accounts. Newly requested previews use the new recipe.

## Checks

- Seven recipe tests, five cleanup tests, documentation links and whitespace
  checks passed. The seed-copy check preserves the original source and fixtures.
- Actual MySQL transaction rehearsal: person/concrete-person counts were 6/6,
  7/7 after one application, still 7/7 after the second, and 6/6 after rollback.
  The committed addition produced 7/7. A digest comparison confirmed all original
  account fields were unchanged; the new account has role 5, enabled, without 2FA.
- Real HTTPS sessions with CSRF login: both `admin1` and `cseteacher1` redirected
  successfully to the application. Admin authorization was true only for admin1;
  switching to ADMIN persisted and the assigned-track lookup returned HTTP 200
  with an empty list. Teacher login retained EDITOR mode.
- The teacher's direct request to the admin-only lookup was denied with
  `AuthorizationDeniedException`, but surfaced as HTTP 500 rather than 403.
  No application exception handling was changed.
- Existing and newly generated merged Compose configurations passed quiet
  validation. The runner was idle before changing only its default recipe path
  and revision. Restart retained all 31 preview records with identical identities
  and statuses, all 32 running container IDs, and the existing capacity settings.
  The gateway and application/database containers were not restarted.

No new full preview build, browser-rendering journey, database restore, or
production migration was exercised. The actual SQL and generated Compose were
tested, but these checks do not replace fresh full-build acceptance.

## Retained rollback and evidence

CT114 retains the previous immutable recipe and protected configuration at
`/srv/appdata/docker/staging/branchline/runner.before-admin-fixture-20261123.json`.
Restoring that configuration and restarting the idle runner restores the prior
default recipe; it does not remove the new account. Keep the backup until this
recipe is accepted. The protected `admin-fixture-20261123.json` beside it records
the transaction and HTTPS acceptance results and is retained as task evidence.

The existing database was neither reset nor reseeded. Reversing the committed
account addition would require checking references created by subsequent use;
no destructive rollback or database backup claim is made here.

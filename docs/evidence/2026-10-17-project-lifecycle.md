# Coordinated project lifecycle — 2026-10-17

The operator Mac now has `symphony-project plan`, `apply` and `status`, backed by
Symphony's `agentctl project` implementation. The owning workflow and detailed
rollout record are in the Symphony repository's `docs/project-lifecycle.md` and
`docs/evidence/project-lifecycle-20261017.md`.

PVE and CT110/114 use dothomelab revision `2801876` for staging retirement guards,
including Compose polling, environment initialization, route creation and the
separate Homarr board. Guest `DEPLOYED_COMMIT` files match. That revision also
preserves the already-deployed Proton changes at `2e3cea1`; the Proton paths and
`.env.example` were compared byte-for-byte. Existing production containers were
not redeployed.

Symphony adapters/worker and the PVE/guest helpers use `b940e66`; Mac controller
and the independent bridge include `530bdba`. The bridge retains its existing
docs-only mode. Its ordinary scheduled cycle exported 23 projects, retaining
its two pre-existing generated-document conflicts. A running Symphony lease was
not interrupted for the later operator-only changes.

A live read-only Film-introspect plan covered the Mac, VM, staging appdata/cache,
two NPM routes and GitHub. No retirement/deletion was applied and GitHub remained
unarchived. Film's two containers stayed healthy with their existing uptime;
HTTPS returned 200; Homarr's check reported one app and no pending changes.
Local checks: 7 deployment, 8 Homarr, 1 staging-retirement test; docs and shell
checks. Symphony's full suite passed 497 tests with one skip.

Guest source rollback remains at `/opt/dothomelab.pre-lifecycle-c79b009` and
`/opt/dothomelab.pre-lifecycle-2801876`; existing older archives remain too.
CT114's prior runtime is at `/opt/symphony-staging/lifecycle-rollback-b940e66`.
No database/volume deletion, real project quarantine, GitHub deletion, new PBS
backup or restore test was performed. The process retains recovery copies and
history explicitly; it does not claim universal erasure.

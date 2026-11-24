# Branchline staging and previews

Branchline at **https://branchline.staging.rafael.media** reviews and edits the
imported Git graph and requests previews on CT114. The
[SSH development VM](../../codex-dev/README.md) edits isolated checkouts and
submits committed changes through Branchline's authenticated HTTPS API. Neither
workflow depends on Symphony. This runbook describes the implementation;
[status](../../../docs/status.md) owns dated live acceptance and remaining gaps.

## Boundaries and retained inputs

The web container listens on `192.168.0.114:8086`. It mounts its stable Git
workspace and `/run/branchline-preview/runner.sock`, without a Docker socket,
PVE credentials or production environment. The separately managed native runner
executes a reviewed recipe and validates the merged Compose configuration before
starting containers. Only trusted developers may submit buildable source; this
is not an execution service for arbitrary untrusted repositories.

The [Labrador recipe](../previews/labrador/README.md) uses the selected snapshot's
existing `end_to_end/compose.yml` and Dockerfiles, followed by a generated
override for private ports, storage and resource limits. LabraCore and Skill
Circuits remain in the upstream combined application image, with a separate
MySQL container; optional Jaeger is disabled. Feature branches need no deployment
commits. Dependency and LabraCore source inputs are pinned outside those branches.

| Material on CT114 | Purpose |
|---|---|
| `/srv/appdata/docker/staging/branchline/workspace` | Stable `repository.git`, graph, propagation/recovery state; mounted as web `/data` |
| `/srv/appdata/docker/staging/branchline/workspace/plans` and `selections` | Versioned plans, manual edits, saved graph selections and execution results |
| `/srv/appdata/docker/staging/branchline/preview-state` | Queue, exact SHAs, limits and lifecycle records |
| `/srv/appdata/docker/staging/previews/<id>` | Source snapshot, generated Compose, logs, MySQL and seed state for one preview |
| `/srv/appdata/docker/staging/branchline/preview-recovery` | Protected, verified archives of explicitly stopped previews; not active databases |
| `/srv/appdata/docker/staging/branchline-artifacts/labrador/artifacts` | Retained dependency/source bundle and hash manifest |
| `/srv/appdata/docker/staging/branchline/runner.json` | Operator-owned runner, recipe and capacity configuration |
| `/opt/branchline-runner/releases/<commit>` | Replaceable native runner, pinned to accepted web release |
| `/opt/branchline-recipes/<revision>` | Replaceable immutable preparation code, identified with the artifact manifest |

The private gateway on `192.168.0.114:8087` accepts only
`bl-<allocated-port>.staging.rafael.media` and checks the runner's current
environment state before forwarding HTTP or WebSocket traffic. NPM supplies
private TLS and LAN/Tailscale access control; Pi-hole resolves the staging
wildcard locally. No public application record or router change is required.
Preview applications use their own fixture login, not the Branchline token.

## Install or release the paired services

Use a committed, reviewed homelab revision and the accepted Branchline `staging`
source. Restore or import the Git workspace and the verified Labrador artifact
bundle first. Follow the recipe runbook for the bundle contract; an empty
workspace or a missing manifest cannot build a working preview.

On PVE, the scoped initializer generates `STAGING_BRANCHLINE_ACCESS_TOKEN` if
absent and renders only its Branchline runtime value. It never supplies this
token to preview builds. Use the operator's protected credential workflow to
give the user browser access; never print it or put it in a URL or command
argument. The [VM client configurator](../../codex-dev/README.md#connect-to-branchline)
installs the accepted CLI and scoped token in the SSH workspace without logging
the credential; rerun it after accepting a paired release.

```bash
hosts/staging/initialize-env.py --app branchline
scripts/sync-guest-repo.sh 114
pct exec 114 -- /opt/dothomelab/hosts/staging/deploy.py --app branchline
pct exec 114 -- python3 /opt/dothomelab/hosts/staging/branchline/install-runner.py
pct exec 114 -- /opt/dothomelab/hosts/staging/deploy.py --app branchline --verify
```

Branchline is marked `manual: true` in `apps.json`: the two-minute poller skips
releases, while `--verify` still checks it. Run both deployment steps together.
The deployer validates Compose quietly and records the accepted web commit;
`install-runner.py` verifies that commit, installs the matching native runner
and immutable recipe, retains the previous runner configuration, and restarts
the runner and gateway units. Its pinned Node installer requires access to the
Node distribution. Runner replacement can interrupt builds; finish or cancel
active builds first. Running preview data is retained during reconciliation.

Full or staging-only bootstrap performs this pair when `workspace/graph.json`
exists; the required artifact manifest must also have been restored. Without
the workspace it leaves Branchline awaiting its recovery inputs. Bootstrap
also reconciles the ordinary Branchline route and the private preview wildcard.
For an isolated route update, run the focused installer from the intended
committed checkout on PVE:

```bash
hosts/staging/branchline/install-routes.sh
```

It exports only the routing helpers and Branchline route registry into
`/opt/dothomelab-branchline-routes/<commit>` on CT110, keeps the shared
`/opt/dothomelab` archive unchanged, and takes an integrity-checked NPM SQLite
rollback copy before reconciling the private routes. The isolated directory's
`DEPLOYED_COMMIT` identifies the installed helper revision. Retain that backup;
restoring the entire NPM database later must account for subsequent route changes.

Do not infer runner compatibility from a healthy web page. Verify the web commit
in `current.json`, the runner's `/opt/branchline-runner/current/DEPLOYED_COMMIT`,
the installed recipe revision, both systemd units, a real preview and its URL.
The [development guide](../../../docs/development.md) lists isolated tests.

## Planning and MCP

The web release also serves authenticated `/mcp` (stateless Streamable HTTP).
It requires the workspace bearer token on every request; the existing private
TLS route and access policy remain in force. The stdio MCP client uses the same
API and a private token file. Planning creates records alongside the graph,
without Git refs until implementation publishes a checkpoint or result.

Install the matching [VM worker and MCP runtime](../../codex-dev/README.md#branchline-planning-and-implementation-sessions)
after the paired web/preview release. The worker claims submitted tasks over HTTPS,
so Branchline receives no SSH credentials. One session implements each node,
waiting for prerequisite commits, with a separate execution concurrency limit.
Checkpoints become previewable graph nodes while dependents remain queued.
The runner reloads graph additions without replacing existing environments.

Preserve plan/selection directories and result refs with the Git workspace. A
runtime rollback does not rewind those records. A previous release can still
read ordinary graph nodes, but it cannot display or operate the new planning
records. Keep the compatible web, worker and MCP pair for task recovery.

## Preview controls and capacity

The [user workflow](../../../USER_DOC.md#preview-and-edit-a-branch-graph) covers
selection and the SSH round trip. Each request captures an exact branch SHA;
a moved branch requires a graph refresh before previewing. Existing environments
do not change silently. Each branch owns one active preview, including while
stopping; repeated requests reuse it regardless of commit or recipe changes.
A changed branch or recipe marks it outdated. **Restart preview** completes Stop
before requesting the current commit and recipe, with the same data reset as Stop.
The list shows one current record per branch; older records/logs remain accessible
by ID. At runner startup, legacy duplicate runtimes are retired while moving
their data to explicit `preview-state/retained/<id>` recovery storage and skipping
the operator cleanup helper. Failed retirement stays
visible and blocks new work for that branch until Stop succeeds.

The configured defaults and operator bounds are **one concurrent build and eleven
running previews**, with CT114's memory ceiling at 32 GiB. The current installation
was observed with a separately raised bound and limit of sixteen; this release
preserves it. Users can lower limits
in **Previews** or with the CLI.
Lowering them does not terminate existing previews. Builds may finish and wait
for a runtime slot; stop a running preview to release a slot. All graph nodes
can be queued, but they are not all made live unless the running limit allows it.
The UI uses the visible range; CLI `preview --all` uses the full imported catalog.

For a larger host, review real memory, CPU, disk and port headroom, then adjust
`bounds` in protected `runner.json`, restart the runner and raise active limits
through the UI/CLI. The installer preserves existing bounds. Also review the
guest's ceilings, recipe service limits, aggregate memory policy and allocated
port range (`12000`–`12899`); changing a UI number does not provision capacity.
The current runner serves one repository and queue on one host. Increase active
limits in steps and wait for readiness while checking host memory and SSD space;
releasing multiple slots starts those waiting environments concurrently. The
32 GiB ceiling is not a reservation or a guarantee under simultaneous heavy use:
eleven preview service limits alone total 30.25 GiB, before builds and other apps.

## Failure, stop and recovery

Closing the browser, disconnecting SSH or signing out does not stop previews.
The shared server persists graph/Git state, queue, exact commits, URLs and limits
in the stable paths above. Reconnecting with the same token shows the same
running previews. A web-service restart invalidates browser sessions, so sign
in again with that token; it does not reset preview data. Runner restarts retain
ready environments, and Docker restart policies bring running previews back
after guest/host restart. This is distinct from a tested clean-host restore.

Use **Previews** for bounded logs, URLs and Stop/Cancel. Cleanup is a core runner
invariant for explicit Stop, cancellation, failed builds/starts and interruptions.
The runner removes the exact project's containers, labelled builders, networks
and reviewed disposable anonymous volumes. It journals volume identities before
container removal and refuses foreign consumers or unreviewed/named volumes.
New previews mount the inherited Gradle cache as bounded tmpfs, so it creates no
anonymous Docker volume. No daemon-wide prune is used.

The pinned Labrador cleanup helper then creates and byte-verifies a cold recovery
archive before deleting the exact preview directory, including MySQL, seed state,
source and build outputs. Only that environment's `branchline-skills:<id>` /
`branchline-labracore:<id>` tags are removed. The runner independently verifies
resource and directory absence before declaring a terminal result or releasing
the branch, port and capacity slot. Batch cleanup is serialized after marking all
targets, preventing queued siblings from starting during Stop all.

Shared images and build cache are retained separately; layers can limit immediate
SSD space reclaimed. Starting the branch again creates a fresh database and
environment. Bounded runner logs now live in `preview-state/logs/<id>.log`, outside
the active workspace. Historical directory-local logs remain in their archives.

Protected archives and checksum receipts live under
`/srv/appdata/docker/staging/branchline/preview-recovery/<id>.tar.gz` / `.json`,
outside active previews. They contain the stopped database/seed pair, source,
Compose/env, provenance and logs, excluding rebuildable build directories and
MySQL's ephemeral socket link. Keep them private: they contain scoped credentials.
The preview operator owns these rollback inputs until their removal is separately
authorized. They remain in scheduled appdata backup scope; live acceptance must
establish cold restore separately from the helper's byte checks.

To recover a stopped preview, verify the archive against its JSON checksum
receipt, then extract it with numeric owners into a new, private recovery
directory. Start an isolated MySQL container using the exact pinned image from
the archived Compose override and `--lower-case-table-names=1`; mount only the
restored `mysql` directory, expose no ports, and keep its seed marker alongside
it. Query it using the archived scoped credential without printing that value.
Compare application table counts and the seed marker with any retained
pre-stop evidence before deciding how to reintroduce the data. Do not extract
over a running preview or replace the whole runner queue. This restores data;
it does not automatically reactivate the stopped Branchline record.

A failed cleanup remains unhealthy with `cleanupPending`, retains its runtime
slot and blocks another run for that branch. Retry after resolving the error;
a successful HTTP health check cannot clear this state. Runner restart resumes
pending cleanup, reconciles legacy failed/interrupted records through the same
verified archive path, and keeps already-ready previews running. Cleanup uses
Docker ownership, not generated Compose files, so it also handles partial builds.
Protected historical diagnostics outside lifecycle records are not swept.

The stable Git workspace and preview state are outside app release data
generations. A web rollback does not rewind submitted branches or databases.
Restore the compatible web/runner/recipe pair deliberately, preserve current
state and resolve any outstanding partial propagation through Branchline before
submitting further SSH work. Review changes to persisted formats before a code
downgrade; do not blindly replace `current.json` or queue files.

All retained paths above under staging appdata are within the appdata backup
scope. Backup inclusion alone does not prove MySQL consistency or a successful
restore. Keep the artifact bundle, workspace, queue and each database/seed pair
together as recovery inputs, whether live or archived. The dated acceptance
linked from [status](../../../docs/status.md) identifies tested recovery paths;
clean-host recovery remains unverified. Explicit Stop deletes live preview data;
removing its retained recovery archive is a separate operator action.
Historical preview migrations require the recipe's initial
`lower_case_table_names=1`; never apply it to an already initialized MySQL directory.

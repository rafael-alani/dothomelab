# Reusable staging deployment research — 2026-10-04

## Recommendation

For this Git-rebuilt, private homelab, prefer GitHub-hosted CI for tests and
image builds, a shared reusable workflow for all repositories, GHCR for
commit-addressed images, and an outbound-only deployment service in CT114.
Keep NPM, Pi-hole, scoped secrets, and canonical appdata under dothomelab.
This recommendation is an architecture proposal, not a claim that those CI
components are installed. The current two-minute Git/source-build deployer
continues to operate until an explicit migration is implemented and verified.

The present deployer is a working pilot, but it still needs a reviewed Compose
definition, scoped secret renderer, and data policy per app. It deploys branch
heads without requiring GitHub CI success. It is not yet a general platform
for arbitrary database engines or private repositories. Expanding bespoke
platform code indefinitely would create avoidable maintenance.

## What the GitHub setting does

Create **Settings → Environments → staging**, then choose **Selected branches
and tags** and add a branch rule named `staging`. In an Actions workflow,
`on.push.branches: [staging]` triggers the work and a deployment job referencing
`environment: staging` uses those restrictions. These are distinct controls:
an environment does not create a server or independently watch/deploy a branch.
Environment restrictions apply to jobs using it, not to the current external
Git poller. No environment setting can silently make that poller CI-gated.

This public test repository supports environment branch restrictions. GitHub
documents paid-plan requirements for those features in private repositories;
verify the account plan before relying on them there.
[GitHub environment setup](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments),
[branch restrictions](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).

## Runners and external deployment services

A self-hosted Actions runner runs on your own Linux machine, VM, or container
while using GitHub's runner software. It is selected with `runs-on` labels;
GitHub need not host the compute. GitHub also supports independent deployment
systems through its Deployments API, which records the commit, environment,
state, logs, and live URL. An independent deployer need not register as an
Actions runner. Report success only after the live application health checks.
[Self-hosted runners](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners),
[external deployments API](https://docs.github.com/en/rest/deployments/deployments).

Personal repository runners belong to individual repositories. The documented
cross-repository runner sharing model is organization-level; a personal
account does not give one repository runner automatic access to all of its
other repositories. A reusable workflow does not remove that distinction.
Persistent runners also retain state between jobs. For public repositories,
GitHub recommends avoiding self-hosted runners because untrusted pull requests
can compromise them. Do not place a general PR build runner alongside durable
staging appdata or give it PVE/production credentials.
[Runner scope and security](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners),
[reusable workflow runner context](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations).

## Options for many repositories

| Approach | Strength | Cost or limitation here |
| --- | --- | --- |
| Shared Actions build + private pull deployment | Versioned process, build logs in GitHub, lower local CPU/cache use, no inbound webhook | Requires CI artifact/manifest handoff and deployment status integration |
| Self-hosted Actions runner | Direct job execution and LAN access | Shared personal-repository registration is awkward; persistent public-repo runner is a poor isolation boundary |
| Coolify | Repository/branch selection, Compose, GitHub App integration, deployment UI | Adds controller state and recovery work; standard webhook flow needs reachable ingress |
| Dokploy | Git branches, Compose/Stack, deployment UI and API | Adds another controller/proxy and state; API/webhook networking and recovery still need integration |
| Current Git poller | Small, private, already verified with SQLite rollback | Local builds, no CI gate or GitHub deployment UI, bespoke enrollment |

Coolify is the preferred dashboard alternative, not an obligatory part of the
recommended workflow. It supports GitHub App selection of repositories and
branches, and API creation with `git_repository` and `git_branch`. GitHub App
webhooks must be reachable from GitHub: installing it privately does not make
push events arrive automatically. GitHub Actions can instead build images and
trigger Coolify after tests. Its Compose deployment can consume those images.
Preserve app definitions in Git/API reconciliation, not only UI clicks.
[GitHub App setup](https://coolify.io/docs/applications/sources/github/app),
[application creation API](https://coolify.io/docs/api/endpoints/applications/create-public-application),
[Actions integration](https://coolify.io/docs/applications/sources/github/actions).

Dokploy documents automatic deployment on matching branches for applications
and Compose, plus webhook/API triggers. Its Compose mode is distinct from
Swarm Stack mode. It is a viable alternative, but adds no clear benefit for
this single staging guest over the above choices.
[Dokploy auto-deploy](https://docs.dokploy.com/docs/core/auto-deploy),
[Compose modes](https://docs.dokploy.com/docs/core/docker-compose).

## Proposed reusable contract

1. Each app keeps its Dockerfiles, lockfiles, tests, health endpoint and a small
   staging workflow. The workflow calls one versioned `workflow_call` workflow
   by immutable commit SHA. The shared job uses the caller's source and token.
   App-specific tests remain explicit; a generic platform cannot infer them.
2. A push to `staging` runs tests, then builds all images for the same commit.
   For film-introspect that is API + web. Publish only after success, with
   source labels and digests. A release manifest records both image digests,
   commit, Compose/config revision, and required checks as one deployable unit.
3. Use `GITHUB_TOKEN` with scoped `contents: read` and `packages: write` for
   publishing. Pin external Actions by reviewed SHA. Never send homelab
   runtime secrets to image builds. Public repository visibility does not make
   its GHCR packages public automatically; private pulls need a recoverable
   read credential. Exact image digests make redeployment deterministic.
4. CT114 polls authenticated release/deployment metadata over outbound HTTPS.
   It validates repository, branch, successful checks, and exact manifest
   before pulling. The release publication job should use the staging
   environment with `deployment: false`, applying environment restrictions
   without falsely recording a live deployment when only images were built.
   The separate deployment record remains pending until CT114 confirms it.
   Use a narrowly scoped GitHub App/token for status reporting and private
   sources, with recovery secrets retained outside Git.
5. Serialize local cutovers, preserve data and prior image digests, validate
   Compose and health, then report the live URL. Cancel superseded builds, but
   do not cancel an in-progress database cutover. Keep per-app database
   adapters: switching image tags cannot undo a schema migration.
6. An idempotent enrollment command should create/reconcile the environment,
   exact branch policy, workflow caller, app manifest, scoped secrets, private
   DNS/proxy route and monitoring. Re-running it must not duplicate resources
   or overwrite app data. Git plus canonical appdata must remain sufficient
   for bootstrap; external GitHub grants and registry availability must be
   documented prerequisites.

Reusable workflows accept typed inputs; environment secrets must be handled
inside the called job rather than passed as an environment through
`workflow_call`. A job that invokes another workflow cannot also contain its
own ordinary steps. Keep caller files small, but do not present an example
`uses:` path as runnable until its shared workflow exists.
[Reusable workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows),
[GHCR authentication and digests](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry),
[deployment concurrency](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments).

## Resource and domain evidence

Live pre-change readings on 2026-10-04:

| Resource | Host evidence | Requested staging allocation |
| --- | --- | --- |
| CPU | i7-9700, 8 physical cores; load 0.67/0.93/1.08 | 6 schedulable cores, shared with other guests |
| RAM | 62 GiB physical, 44 GiB used, 18 GiB available, no host swap | 16 GiB ceiling; total declared guest limits become 82 GiB |
| SSD | rpool 928 GiB, 492 GiB allocated, 436 GiB raw free; ZFS dataset availability 407 GiB | 500 GiB root refquota, zero reservation |
| Existing staging use | Root 2.11 GiB; guest RAM 264 MiB; app containers about 65 MiB | Capacity for additional apps, not currently consumed |

This is acceptable for light development with shared limits, not enough
physical capacity to guarantee all configured maxima simultaneously. With
60–90 GiB pool headroom, today's aggregate growth budget is roughly 317–347
GiB across **all** SSD consumers, including production, snapshots and staging
appdata. The appdata bind is outside CT114's root quota. `df` may show less
than 500 GiB when the pool's available space is the tighter limit. Raising
quota neither allocates 500 GiB nor extends the physical SSD. No swap file is
created merely by declaring LXC swap allowance.

Use `film-introspect.staging.rafael.media` and future `app.staging.rafael.media`.
The old `*.rafael.media` certificate cannot cover these nested names. A new
`*.staging.rafael.media` DNS-01 certificate is required, while app DNS records
and the NPM source ACL remain private. Issuance uses temporary public TXT
records without making the application reachable publicly. Certificate and
renewal state remain in canonical NPM appdata.
[Wildcard coverage](https://developers.cloudflare.com/ssl/edge-certificates/advanced-certificate-manager/),
[Let's Encrypt DNS-01](https://letsencrypt.org/docs/challenge-types/).

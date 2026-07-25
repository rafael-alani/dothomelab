# Media pipeline phase 1 evidence

Date: 2026-07-25

Scope: storage, ownership, recovery, and integration foundation only. Shelfarr,
BookOrbit, Storyteller, PinePods, Aurral, Soularr, and Navidrome were not
deployed.

## Read-only preflight

Observed between 19:52 and 19:57 CEST:

- PVE 9.1.2 reported all pools healthy.
- `rpool/appdata/docker` was mounted read-write at `/srv/appdata/docker` with
  524,481,744,896 bytes available. `vault/shared` was mounted read-write at
  `/vault/shared` with 21,839,384,630,272 bytes available.
- CT102 and CT112 were running and unprivileged with the default mapping:
  host `101000:101000` appeared as guest `1000:1000`. Existing media
  directories used host owner `101000`, group `100996`, and mode `0755`.
  Existing Audiobookshelf appdata used `101000:101000` and mode `0750`.
- ACL access/default xattrs were absent on the inspected canonical roots and
  existing media/appdata directories; both ZFS mounts had `posixacl` enabled.
- CT102 retained `/vault/shared` at read-write `/data` and appdata at
  read-write `/docker`. UID/GID 1000 could read and write the inspected media
  and appdata paths.
- CT112 retained read-only `/data`, read-write appdata, and the existing narrow
  read-write `/downloads`, `/music`, `/slskd-downloads`, and `/podcasts`
  mounts. Both root and UID/GID 1000 were denied writes through `/data`.
- No new pipeline `mp` slot existed or was allocated. The CT configs matched
  the mount declarations in `provision/inventory.env`.
- CT102 had 13/13 containers running in one Compose project. CT112 had 30
  running containers, 35 total including five stopped restore-test
  containers, and 16 running Compose projects. Both guests reported
  `DEPLOYED_COMMIT=fc062471cd29627bed7aceabe48d7e57d79ace50`.
- The pre-change lifecycle digests were:
  - CT102:
    `d14f480fecbe826ae97d32dd6035aee39ae5b23b9c93f82e85060bde07850546`
  - CT112:
    `1b4abe3a44853a48ec08473270ffc7febf9889ad9e2bc275a3dadfafb69b1e3d`
- The appdata timer was active/waiting. Its 2026-07-25 scheduled run reported
  `Result=success`, `ExecMainStatus=0`, and completed at 09:41 CEST.
  `OnSuccess=dothomelab-wud-update.service` remained the only update handoff.
  The WUD service also reported success and completed at 09:50 CEST. No WUD
  timer existed.

No media filenames, production environment values, or credentials were read
into this document.

## Implemented contract

`provision/inventory.env` now declares every fixed host path from the master
plan, their expected ownership/mode, and read-only free-space floors of 1 TiB
for shared storage and 64 GiB for appdata.

`provision/prepare-media-contract.sh` is additive and idempotent. It leaves
existing directories untouched and uses targeted `install -d` only for an
exact missing path. The live apply created 14 missing directories: seven under
the declared shared-media contract and seven future appdata directories.
Existing books, comics, mangas, audiobooks, podcasts, music, and Audiobookshelf
paths were retained without metadata changes. No recursive permission command
was used.

`provision/verify-media-contract.sh` provides three reusable modes:

- `--repository` checks fixed declarations and the shared book-key result;
- `--host` additionally checks exact physical directories, dataset source,
  owner/group/mode, and capacity without write probes;
- `--live` additionally checks the CT102/CT112 mount sources/modes and
  UID/GID-1000 read/write boundary through `pct exec`.

Bootstrap runs the additive preparation only after appdata recovery, so the
reserved empty directories cannot make `--appdata-source` or
`--restore-latest` appear non-empty. The normal end-to-end
`provision/verify.sh` now invokes the live media verifier.

## Shared book key

`docs/media-data-contract.md` defines one result contract without inventing a
Shelfarr template:

```text
ebooks/<book-key>/Book.epub
audiobooks/<book-key>/Book.m4b
audiobooks/<book-key>/audio/01 - Chapter.mp3
```

Parts 2 and 3 must derive the actual syntax from the then-current official
Shelfarr release and prove that the ebook and audiobook relative keys are
byte-identical for one intended pair.

## Environment scaffold

Only currently documented mandatory values were reserved in `.env.example`:

- BookOrbit app URL, PostgreSQL password, JWT secret, and one-time setup token,
  as required by the
  [official installation guide](https://bookorbit.app/installation);
- Storyteller authentication secret, as required by the
  [official self-hosting guide](https://storyteller-platform.dev/docs/installation/self-hosting/);
- PinePods PostgreSQL password, as required by the
  [official Compose quick start](https://github.com/madeofpendletonwool/PinePods#quick-start-).

Shelfarr currently generates its Rails master key into persistent appdata.
Aurral and Navidrome use onboarding, while Soularr uses a config file and
existing scoped integration keys. No speculative variables or generated
values were committed. Later service phases must add idempotent initializers
for values they actually deploy.

## Recovery boundary

The encrypted appdata job covers future database/configuration/queue/progress
and small manifest state under `/srv/appdata/docker` after the applications
are deployed.

It does not cover `/vault/shared`. Canonical books, audiobooks, podcast
episodes, music, Aurral flow files, and large Storyteller inbox/library assets
remain outside PBS appdata protection. Later phases must classify and protect
those data classes explicitly.

## Verification

Completed before the implementation commit:

- `bash -n` passed for the entrypoint, bootstrap, inventory, main verifier,
  media preparer, and media verifier.
- `git diff --check` passed. Local `shellcheck` was unavailable.
- `./provision/verify-media-contract.sh --repository` passed locally.
- The PVE media preparer dry-run listed exactly the 14 missing paths, and the
  apply created exactly those paths. Its host verifier passed both capacity
  floors and all exact metadata checks.
- The full live verifier passed without creating probe files. It proved CT102
  UID/GID 1000 read/write access, CT112 broad read-only access, continued
  read/write access through the existing narrow music/podcast binds, and
  read/write access to future appdata through the existing appdata mounts.
- `bootstrap.sh --dry-run` was run against production state. It stopped before
  mutations because the pre-existing production environment lacks
  `PAPERLESS_GPT_OPENAI_API_KEY`; no value was invented or written. The same
  dry-run then completed successfully with a mode-0600 temporary environment
  copy containing an explicit non-production placeholder. It showed every new
  directory as `KEEP` and printed no real environment values.
- No on-demand backup was started.

Implementation commit:
`cf8cfb3ab66befc9f2b43d959f07fe9b8e245809` (`Establish media pipeline
storage contract`).

The 20:08 CEST post-change check reproduced both pre-change lifecycle digests
and both Compose-project digests byte-for-byte:

- CT102 lifecycle
  `d14f480fecbe826ae97d32dd6035aee39ae5b23b9c93f82e85060bde07850546`,
  project
  `5556243bd33da9ac1534d7019da2e94403d491b49d14d556f8f721d6b6452503`;
- CT112 lifecycle
  `1b4abe3a44853a48ec08473270ffc7febf9889ad9e2bc275a3dadfafb69b1e3d`,
  projects
  `615aae2673adf6a30bc0059af1a868bad6890791fb0e62db9c3b9ad9e961811f`.

Counts also remained CT102 13/13 containers and one project, CT112 30 running
of 35 total and 16 projects. Therefore no existing Compose project or
container was created, removed, replaced, restarted, stopped, or started by
this phase.

The post-change CT configs were byte-for-byte identical for every `mp` and
`unprivileged` line. The backup timer still showed its 02:03 scheduled trigger,
09:41 successful completion, and next scheduled run; it was not triggered on
demand. `OnSuccess=dothomelab-wud-update.service`, empty `OnFailure`, the
successful 09:50 WUD completion, and the absence of any WUD timer were also
unchanged.

The staged implementation diff passed `git diff --cached --check`, contained
no added LXC `mp` declaration, and matched no high-risk private-key/token
pattern. Final upstream push, guest repository synchronization, deployed
commit IDs, and clean worktree status are necessarily verified after this
evidence-only commit is created and are included in the phase handoff.

## Rollback and remaining prerequisites

Rollback is `git revert` of the phase commits. Existing services and mounts do
not need a runtime rollback because none were changed. The empty reserved
directories are harmless recovery scaffolding and may remain; deleting them is
optional future cleanup that must first prove each exact directory is empty.

Parts 2-6 still need to validate current upstream container paths, images,
secrets, databases, health checks, WUD gates, proxy/Homarr integration, logical
dumps, representative workflows, and restore behavior before deploying their
applications. The unrelated missing Paperless-GPT credential and currently
inactive repository-declared Apps projects remain outside phase 1.

# Operations

Run host commands on `root@192.168.0.250` and enter LXCs with `pct exec`.
Follow [AGENTS](../AGENTS.md) and the [affected service runbook](reference/service-policies.md)
for authorization, data risk, and special upgrade requirements.

## Inspect before changing

Use the affected guest/service rather than inspecting the fleet for every edit:

```bash
# On PVE; read-only
pct list
zpool status -x
pct config 112
pct exec 112 -- docker ps --format 'table {{.Names}}\t{{.Status}}'
pct exec 112 -- cat /opt/dothomelab/DEPLOYED_COMMIT
systemctl show dothomelab-appdata-backup.service \
  -p Result -p ExecMainStatus -p InactiveEnterTimestamp
systemctl show dothomelab-wud-update.service \
  -p Result -p ExecMainStatus -p InactiveEnterTimestamp
```

For mount/permission issues inspect `findmnt`, `stat`, `namei`, and all consumers.
For access failures check client DNS/routing, NPM policy/upstream, then direct
service health. Read bounded logs privately; do not dump environments, raw
Docker inspection, or expanded Compose into task output. See
[user troubleshooting](../USER_DOC.md#troubleshooting) and the
[proxy runbook](../hosts/infra/proxy/README.md).

## Deploy a production change

An agent needs an explicit production deployment request in the active prompt.
For generated applications on CT115, use the [production runbook](../hosts/production/README.md)
and its gated activation command. A main-branch push alone never deploys.
The generic shared-environment helper rejects CT114/115.

1. Establish affected data, downtime, rollback, and acceptance checks. Routine
   changes use scheduled backup evidence; schema/data mutations need focused
   rollback. Apply the [development checks](development.md).
2. Commit the intended change and check out that revision on PVE. Guest sync
   exports `HEAD`, not local edits. It moves an existing
   `/opt/dothomelab.previous` to a dated retained path before replacing it. CT110
   sync/deploy rejects candidates that remove the installed Proton source checks;
   its [protected backup runtime](../hosts/infra/obsidian-sync/README.md#protect-the-installed-backup-runtime)
   remains independent of the shared guest archive.
3. Sync the affected guest, run its documented preparation/deployment, and then
   focused verification. Preparation can mutate configuration/mounts; verifiers
   can write probes or create retained test data. Read them first.
4. Confirm `DEPLOYED_COMMIT`, endpoint health, DNS/TLS, and the affected user
   journey. Record results and limits. A code revert cannot undo a schema change.

Example for an already reviewed Navidrome rollout, on PVE:

```bash
scripts/sync-guest-repo.sh 112
pct exec 112 -- /opt/dothomelab/hosts/apps/navidrome/prepare.sh
scripts/deploy-compose.sh 112 hosts/apps/navidrome/compose.yaml
pct exec 112 -- /opt/dothomelab/hosts/apps/navidrome/verify.sh
```

The generic deploy helper temporarily copies mode-0600 `/root/.env` into guest
`/run`, validates Compose quietly, **pulls current tags**, and runs `up -d`, then
removes the temporary env. Review image policy first; use the special runbook
for exact-image repairs, coupled upgrades, or CT114's scoped environment.

## Updates

[WUD](../hosts/infra/wud/README.md) owns production image updates: successful
appdata backup hands off through `OnSuccess`, then eligible containers update
sequentially with health checks and retained images. Backup success does not
prove the update succeeded. Diagnose a failed handoff before retrying.

[Service policies](reference/service-policies.md) identify manual cohorts and
busy-job guards. [Staging](../hosts/staging/README.md) instead owns branch builds,
independent data generations, failed-candidate holds, and data-aware rollback.

## Service monitoring and dashboard enrollment

Apply these checks when adding, moving, renaming, or retiring a service:

1. Follow the [Pulse runbook](../hosts/infra/pulse/README.md). Containers on an
   enrolled Docker host are discovered automatically. For a new Docker LXC,
   update `PULSE_DOCKER_CTIDS`, enroll its agent, and keep bootstrap consistent.
   On PVE, run `python3 hosts/infra/pulse/configure-monitoring.py --verify` and
   confirm the affected containers appear online. PVE guest discovery alone
   does not prove monitoring of applications inside a VM or native processes;
   record those gaps explicitly. Container health is not an end-to-end uptime probe.
2. Give each user-facing application or administration UI a working Homarr tile
   on the appropriate private board. For shared services, maintain
   `hosts/infra/homarr/reconcile-managed-apps.sql` and its apply-script checks;
   inspect the script, retain a current SQLite rollback copy, and verify the
   affected board and destination after applying. Background workers, databases,
   and caches need Pulse coverage but no standalone tile unless they have a
   useful UI. Preserve user-owned tiles and existing access restrictions.
3. Staging projects use the [Staging board sync](../hosts/staging/README.md#push-a-staging-release).
   Verify its registry and `python3 hosts/staging/sync-homarr.py --check` on PVE.
   Shared administration UIs and production sites need their own managed tiles;
   the staging sync does not discover them. Dashboard enrollment does not
   authorize production activation or public exposure.
4. Report the verified Pulse host/container coverage, board and destination URL,
   and any exceptions. Retire only the affected managed entries when a service
   is removed; keep unrelated tiles, telemetry history, and rollback material.

## Synchronize personal worker skills

The [agent instruction](../AGENTS.md#personal-skill-synchronization) makes this
part of editing an already installed personal skill during work in this repo.
Local sources are `/Users/rafael/.codex/skills/<name>`. VM101 has a separate
Symphony catalog at `/etc/openhands-symphony/skills.json`; these files do not
automatically sync through Syncthing. This is an agent completion workflow,
not a background watcher or a change to VM101's recovery scope.

1. Inspect the selected live catalog entries over `ssh afa@192.168.0.126`.
   Confirm the names are already installed and record the catalog digest.
   Read the installed `/opt/openhands-symphony/scripts/install_skill_catalog.py`
   before executing it. Use that version locally for packaging; a source-checkout
   copy is suitable when its checksum matches the installed script.
2. Validate each changed skill and its referenced resources. Package only the
   selected directories with the installer's `pack` command, using a fresh output
   directory. Include supporting files, not just `SKILL.md`; review for secrets.
   The installer checks file types, sizes, credential patterns, and hashes.
3. Copy the bundle to a fresh directory under `/home/afa` on VM101. Confirm the
   catalog has not changed since inspection, then run the installed installer:

   ```bash
   # Mac: use a verified copy of the installed installer and a fresh bundle path.
   python3 /path/to/install_skill_catalog.py pack \
     --source /Users/rafael/.codex/skills --skill document-creation \
     --output /tmp/selected-skill-bundle
   # VM101: substitute the exact uploaded bundle path.
   sudo -n python3 /opt/openhands-symphony/scripts/install_skill_catalog.py install \
     --bundle /home/afa/selected-skill-bundle
   ```

4. Verify as `openhands-agent`: the catalog resolves each selected name to the
   new immutable release, its embedded instructions match the local `SKILL.md`
   after the installer's resource preamble, and every resource matches the bundle
   manifest and is readable. Compare the retained prior catalog to confirm all
   unrelated entries are unchanged. Report the release and verification result;
   failed access or validation leaves synchronization incomplete.

The installer retains `catalog-before-<sha256>.json` and immutable resources under
`/opt/openhands-symphony-skills/releases/`. Keep them for rollback and accepted
tasks. Restore the previous catalog only if there have been no intervening
catalog updates; otherwise restore just the affected entries while preserving
later changes. No service restart is required. Newly accepted tasks resolve the
updated catalog; existing accepted tasks, retries, and inline instruction copies
retain their original text. Do not edit notes or trigger work during synchronization.

## Backup and recovery

| Material | Protection / required input |
|---|---|
| Git | Clone the intended committed revision |
| Appdata and `/root/.env` | Daily encrypted PBS job; supported database hooks prepare logical/SQLite recovery copies |
| Native identities and HAOS VMA | Included under appdata; sensitive recovery material |
| `/vault/shared` | Excluded, including shared binds presented beneath appdata paths |
| Proton's Obsidian/photos/environment scope | Not protection until authenticated, run, restore-tested, and enabled |
| LXC roots | Rebuildable; not recovery inputs |
| VM101 | Outside this repo's recovery scope |

The [PBS runbook](../backup/pbs/README.md) owns snapshot/freeze, retention,
verification, and restore procedures. PBS is on this physical host; keep its
encryption key off-host. A successful job exit alone is not restore evidence.

For full recovery follow [rebuild.md](rebuild.md), including prerequisites,
`--dry-run`, `--appdata-source`, and `--restore-latest`. Existing guests are
retained; absent VM104 uses its [verified VMA](haos-vm.md). For one application,
use its runbook and matching database version; retain current and restored data
until identity, records, files, progress, and a representative workflow pass.
[Status](status.md) links actual recovery evidence and outstanding tests.

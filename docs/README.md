# Documentation map

Start with a question; each guide owns a different kind of information.
Documentation describes this checkout's behavior. Live readiness always has a
date and an evidence boundary. This is the dothomelab pilot for Rafael's proposed
repo documentation structure; reusable skill extraction follows his review.

## Main guides

| Question | Read | Owns |
|---|---|---|
| What is this, and where do I start? | [Repository README](../README.md) | Introduction and recovery entry point |
| What can I do, and how? | [User manual](../USER_DOC.md) | Roles, capability index, user workflows, restrictions |
| What should an agent read and preserve? | [AGENTS](../AGENTS.md) | Essential constraints and task reading map |
| How does a change get accepted? | [Contributing](../CONTRIBUTING.md) | Review and documentation maintenance |
| What has been checked? | [Status](status.md) | Dated readiness, drift, acceptance gaps |
| How is the homelab structured? | [Architecture](architecture.md) | Responsibilities, data flow, storage/network boundaries |
| How do I work on the code? | [Development](development.md) | Setup, implementation map, focused checks |
| How do I run and recover it? | [Operations](operations.md) | Deployment, diagnosis, updates, backup/restore navigation |
| Why were consequential choices made? | [Decisions](decisions/README.md) | Rationale, consequences, supersession |

## Detailed contracts and evidence

| Subject | Authoritative detail |
|---|---|
| Full rebuild / required external inputs | [Rebuild contract](rebuild.md) |
| Managed HAOS VM | [HAOS recovery](haos-vm.md) |
| Canonical media writers and paths | [Media data contract](media-data-contract.md) |
| Application update/data constraints | [Service policies](reference/service-policies.md) |
| Guest addresses, resources, identities | [Declarative inventory](../provision/inventory.env) |
| Environment variable names/defaults | [Environment example](../.env.example) |
| Current review's live checks | [October 12 baseline](evidence/2026-10-12-documentation-baseline.md) |
| Earlier migrations, repairs, plans, experiments | [Evidence and historical reports](evidence/README.md) |

Keep service-specific commands beside the implementation. The operations guide
selects a runbook; it does not replace a database's restore procedure or a
service's special upgrade sequence. Historical reports preserve what happened,
not an instruction to rerun old migration commands.

## Service and client runbooks

The manual's [capability index](../USER_DOC.md#capability-index) is the user view.
This list is the operator/developer view, including rollback and support
services. Listing a runbook does not make a service active.

### Acquisition / Servarr

- [Cleanuparr](../hosts/servarr/cleanuparr/README.md)
- [cross-seed](../hosts/servarr/cross-seed/README.md)
- [Listenarr](../hosts/servarr/listenarr/README.md)
- [Shelfarr](../hosts/servarr/shelfarr/README.md)
- [Sortarr](../hosts/servarr/sortarr/README.md)
- [Soularr](../hosts/servarr/soularr/README.md)

### Applications

- [Audiobookshelf](../hosts/apps/audiobookshelf/README.md)
- [Aurral](../hosts/apps/aurral/README.md)
- [Bar Assistant](../hosts/apps/bar-assistant/README.md)
- [BookOrbit](../hosts/apps/bookorbit/README.md)
- [DroppedNeedle rollback](../hosts/apps/droppedneedle/README.md)
- [Grimmory](../hosts/apps/grimmory/README.md)
- [ImmichFrame](../hosts/apps/immichframe/README.md)
- [Kavita](../hosts/apps/kavita/README.md)
- [Music metadata writer](../hosts/apps/music-metadata/README.md)
- [Navidrome](../hosts/apps/navidrome/README.md)
- [Paperless-GPT](../hosts/apps/paperless-gpt/README.md)
- [Paperless-ngx](../hosts/apps/paperless-ngx/README.md)
- [PinePods](../hosts/apps/pinepods/README.md)
- [slskd](../hosts/apps/slskd/README.md)
- [SnapOtter](../hosts/apps/snapotter/README.md)
- [Stirling-PDF](../hosts/apps/stirling-pdf/README.md)
- [Storyteller](../hosts/apps/storyteller/README.md)
- [Wizarr](../hosts/apps/wizarr/README.md)
- [yt-dlp Web UI](../hosts/apps/yt-dlp-web-ui/README.md)
- [Zotero WebDAV](../hosts/apps/zotero-webdav/README.md)

### Infrastructure

- [Cockpit files and SMB](../hosts/infra/cockpit/README.md)
- [n8n](../hosts/infra/n8n/README.md)
- [Syncthing and Proton Drive backups](../hosts/infra/obsidian-sync/README.md)
- [Consolidated service routes](../hosts/infra/proxy/README.md)
- [Pulse](../hosts/infra/pulse/README.md)
- [Central WUD](../hosts/infra/wud/README.md)

### Staging

- [Staging](../hosts/staging/README.md)

### Desktop clients

- [macOS Media reconnect and Kew](../clients/macos-media/README.md)
- [SNOWSKY ECHO desktop sync](../clients/snowsky-echo/README.md)

### Backup

- [PBS appdata backup](../backup/pbs/README.md)

## Maintaining this map

Update the owning guide in the same change as behavior; use the
[ownership table](../CONTRIBUTING.md#documentation-ownership). Add new dated
results under `docs/evidence/` and link them from status when they change
readiness. Keep old file paths stable, or leave explicit redirects when moving
material. Run `python3 scripts/check-docs.py` after link/heading changes.

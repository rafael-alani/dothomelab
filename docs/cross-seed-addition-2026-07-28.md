# cross-seed addition evidence — 2026-07-28

## Result and safety boundary

Git now declares cross-seed as a separate CT102 Compose project. The live
container is fully created but intentionally stopped:

```text
state=created
restart=no
user=1000:1000
project=cross-seed
image=ghcr.io/cross-seed/cross-seed:6
```

The project is not approved or active yet. The user previously prohibited
automated tracker-login experimentation. The first enabled BTSchool
Prowlarr-create attempt made one request, encountered `Found captcha during
automatic login, aborting`, saved no indexer, and stopped. No cross-seed
daemon was running, and that login was not retried.

The corrected repository flow creates new Prowlarr resources disabled.
Prowlarr therefore performs no tracker login during reconciliation. The live
disabled resources are:

```text
BTSchool   id=30 priority=1
RailgunPT  id=31 priority=2
HDClone    id=32 priority=3
```

Freeleech-only is false and seed ratio, seed time, and pack seed time are all
unset for every resource. `configure.py --check` passed without contacting a
tracker.

## Runtime and data contract

The installed official image reports:

```text
version=6.13.7
digest=sha256:a1fed512261fd968c55cb03c51cff9c6620aa76a34b3b591afca95c890aa8225
```

The generated mode-0600 config exposes only Prowlarr indexer paths
`/30/api`, `/31/api`, and `/32/api` to cross-seed; the API-key query values
were not displayed. Tracker usernames and passwords are absent from that
file. They remain in production `/root/.env` and Prowlarr's protected
appdata.

The strict safety settings are:

```text
matchMode=strict
action=inject
linkType=hardlink
skipRecheck=false
autoResumeMaxDownload=0
ignoreNonRelevantFilesToResume=false
delay=60
searchLimit=50
rssCadence=1 hour
searchCadence=1 day
```

The qBittorrent source is discovered through its API rather than by mounting
`BT_backup`. An ephemeral container on `servarr-hello_default` reached the
existing qBittorrent API and returned version 5.2.2. qBittorrent currently has
919 persisted `.torrent` records.

Persistent paths passed the following live checks:

```text
/docker/cross-seed                    1000:1000 mode 0750
/docker/cross-seed/config.js          1000:1000 mode 0600
/data/torrents/cross-seed-links       1000:1000 mode 0750
/data/torrents device                 51
/data/torrents/cross-seed-links device 51
```

The common `/data` mount is deliberate: Docker hardlinks require source data
and link directories in one container mount. Appdata is on
`rpool/appdata/docker`; link data is on `vault/shared`. The normal encrypted
appdata job covers the former, not the latter.

## Manual acceptance gate

The next step requires a user session:

1. Open each of BTSchool, RailgunPT, and HDClone in Prowlarr.
2. Complete any CAPTCHA/2FA prompt.
3. Run Prowlarr's Test once and save each indexer enabled.
4. Execute the documented
   `approve.sh --manual-tests-passed` workflow from
   `hosts/servarr/cross-seed/README.md`.

Approval checks the local saved settings without repeating tracker tests,
writes `/docker/cross-seed/indexers-approved`, starts the container, and
promotes its restart policy to `unless-stopped`. Only then can focused and
full live verification pass. Until approval, the clean-build verifier is
expected to report one fewer running container than the 74-container desired
state.

Repository commits:

- `11e345b` — initial strict cross-seed project and recovery contract;
- `9b5afed` — CAPTCHA-safe disabled-indexer creation and manual approval gate.

Official implementation references:

- <https://www.cross-seed.org/docs/basics/getting-started>
- <https://www.cross-seed.org/docs/tutorials/injection>
- <https://www.cross-seed.org/docs/tutorials/linking>
- <https://www.cross-seed.org/docs/basics/options>
- <https://github.com/Prowlarr/Prowlarr/blob/develop/src/Prowlarr.Api.V1/ProviderControllerBase.cs>

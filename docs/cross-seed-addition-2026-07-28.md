# cross-seed addition evidence — 2026-07-28

## Result and safety boundary

Git declares cross-seed as a separate CT102 Compose project. The user manually
passed the BTSchool, RailgunPT, and HDClone tests in Prowlarr, and the live
container is active:

```text
state=running
health=healthy
restart=unless-stopped
user=1000:1000
project=cross-seed
image=ghcr.io/cross-seed/cross-seed:6
```

Approval did not repeat any tracker test. It verified the three enabled
resources and their accounts locally, then used Prowlarr's force-save path to
normalize policy without a login request. The final live resources are:

```text
BTSchool   id=33 priority=1 enabled=true
RailgunPT  id=35 priority=2 enabled=true
HDClone    id=34 priority=3 enabled=true
```

Freeleech-only is false and seed ratio, seed time, and pack seed time are all
unset for every resource. The mode-0600 approval marker is in canonical
appdata, and `configure.py --check` passed without contacting a tracker.

The user previously prohibited automated tracker-login experimentation. The
first enabled BTSchool Prowlarr-create attempt made one request, encountered
`Found captcha during automatic login, aborting`, saved no indexer, and
stopped. That failed login was not retried. The corrected initial
reconciliation created all resources disabled and kept the daemon stopped
until manual acceptance.

## Runtime and data contract

The installed official image reports:

```text
version=6.13.7
digest=sha256:a1fed512261fd968c55cb03c51cff9c6620aa76a34b3b591afca95c890aa8225
```

The generated mode-0600 config exposes only Prowlarr indexer paths
`/33/api`, `/35/api`, and `/34/api` to cross-seed; the API-key query values
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
`BT_backup`. The live container reached qBittorrent 5.2.2, indexed all 920
current torrents, found 730 suitable searchees using 724 unique queries, and
limited the initial daily search to 50 queries per indexer. qBittorrent
automatic torrent management is disabled, so cross-seed's generic v6
folder-layout warning does not require a client change.

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

## Acceptance evidence

The user completed the three manual Prowlarr tests and explicitly reported
that all passed. `approve.sh --manual-tests-passed` then normalized the tested
resources locally, wrote `/docker/cross-seed/indexers-approved`, and started
the service. No production dotenv copy remains in CT102.

Focused live verification passed:

```text
cross-seed verification passed: v6.13.7, private API, three Torznab
indexers, strict hardlink injection, forced rechecks, zero-byte auto-resume,
and backup-gated updates.
```

The initial RSS scan completed with 200 new candidates and no runtime error.
All six CT102 Compose projects are running. Fleet counts are CT102 19, CT110
11, and CT112 44: all 74 declared containers are active.

Repository commits:

- `11e345b` — initial strict cross-seed project and recovery contract;
- `9b5afed` — CAPTCHA-safe disabled-indexer creation and manual approval gate;
- `bc2e5de` — normalize manually tested indexers without repeating their tests;
- `510dc44` — align focused verification with Docker's security-option format.

Official implementation references:

- <https://www.cross-seed.org/docs/basics/getting-started>
- <https://www.cross-seed.org/docs/tutorials/injection>
- <https://www.cross-seed.org/docs/tutorials/linking>
- <https://www.cross-seed.org/docs/basics/options>
- <https://github.com/Prowlarr/Prowlarr/blob/develop/src/Prowlarr.Api.V1/ProviderControllerBase.cs>

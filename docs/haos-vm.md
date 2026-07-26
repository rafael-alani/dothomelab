# Managed Home Assistant OS VM

## Decision

VM104 remains Home Assistant OS, not Home Assistant Container. HAOS preserves
Supervisor-managed apps, supported OS updates, A/B boot rollback, and native
full backups. A container conversion would lose those supported management
layers and would not make the existing configuration more portable than a
protected native backup.

The recovery contract is now the same input set as the LXC homelab:

- Git provides inventory, restore, backup, and verification logic;
- `/srv/appdata/docker/home-assistant/vm` contains a complete VMA image and
  SHA-256 sidecar;
- `/srv/appdata/docker/home-assistant/backups` contains protected native HA
  backups;
- `/root/.env` contains `HA_BACKUP_PASSWORD` and the official
  `GOVEE_API_KEY`;
- `/vault/shared` remains unrelated shared durable data.

Bootstrap never replaces an existing VM104 disk. If VM104 is absent, it fully
verifies the newest canonical VMA, restores it to `local-zfs`, applies the
declared name/startup/protection policy, starts it, and waits for HA health.

## 2026-07-25 migration

Observed starting state:

- HAOS 15.0, with 14.1 in the inactive slot;
- Supervisor 2025.09.0;
- Core 2025.3.4;
- static address drifted onto a stale network definition;
- no native HA backups and no ZFS snapshots;
- Govee2MQTT and Spotify Connect already failed or stopped.

The network was corrected to `192.168.0.125/24`, gateway `192.168.0.1`, and
DNS `192.168.0.100`. Before migration, a protected full HA backup was exported
to canonical appdata, a complete Proxmox VMA snapshot passed decompression and
`vma verify`, and the encrypted appdata/PBS job completed successfully.

The HTTPS route is also recovery-managed. NPM terminates TLS for
`ha.rafael.media`, forwards WebSockets over plain HTTP to
`192.168.0.125:8123`, and preserves the existing public exposure policy.
Bootstrap reconciles Home Assistant's `trusted_proxies` entry to the current
Infra address `192.168.0.110`. This prevents a restored pre-migration
`192.168.1.110` trust entry or an HTTPS upstream selection from producing
HTTP 400/502 failures.

The supported HAOS feed required one staging hop:

1. Supervisor 2025.09.0 to 2026.07.3;
2. HAOS 15.0 to 15.2 and an explicit reboot;
3. HAOS 15.2 directly to 18.1 and an explicit reboot.

After 15.2, the supported feed offered 18.1 directly. HAOS 18.1 booted from
slot B and retained healthy 15.2 in slot A. The optional containerd snapshotter
migration was deliberately not combined with this upgrade.

Core configuration and every intervening release were audited before the Core
jump. The only live breaking pattern was deprecated mired/color-temperature
attributes duplicated in 39 scenes; 348 legacy attributes were removed while
the Kelvin equivalents were retained. No live uses were found for the other
reviewed removals or semantic changes: legacy template platforms, MQTT
`object_id`, removed Google Calendar actions, label targets, Supervisor action
failure assumptions, paper theme variables, purpose-trigger renames, or
person/zone state assumptions. Core therefore upgraded directly from 2025.3.4
to 2026.7.4. Recorder schema migration 48 through 53 completed.

Apps were updated individually:

- Mosquitto 7.1.0, running;
- File Editor 6.0.0, running;
- Music Assistant 2.9.9, running;
- Spotify Connect 0.18.0, stopped and non-blocking by operator choice;
- Govee2MQTT 2026.03.25, still rejected by Govee's undocumented API.

Custom components were reconciled with rollback copies retained under
`/config/upgrade-rollbacks/20260725`:

- ICS Calendar 5.2.0, fixing its Python 3.14 dependency conflict;
- BLE Monitor 13.15.0, fixing the deprecated scanner alias;
- Govee compatibility release 2025.7.1;
- HACS 2.0.5 and stable Spotcast 4.0.1 were already current.

## 2026-07-26 Govee acceptance

Govee2MQTT 2026.03.25 is the accepted owner for all three lights through the
MQTT integration. LAN Control must remain enabled in the Govee app for each
device. The accepted inventory is exactly two H60A1 ceiling lights and one
H6072 floor lamp; the bridge exposes 13 segment lights for each H60A1 and
eight for the H6072.

The app configuration uses Celsius, automatic updates, and a newly issued
official Govee Platform API key recovered from `GOVEE_API_KEY` in
`/root/.env`. It deliberately has no Govee email or password: those fields
select the rejected undocumented account API. LAN Control remains enabled for
local discovery and basic power, brightness, and color control. The official
Platform API is required for dynamic scene effects on the H60A1s.

The initial LAN-only acceptance was a false positive. Govee2MQTT exposed the
effect catalogs, accepted scene commands, updated its optimistic state, and
sent LAN packets, but the two physical H60A1s did not animate. This matches the
upstream [H60A1 LAN scene report][govee-h60a1-lan]. A catalog match or a
successful service call therefore proves only command structure, not physical
effect execution.

With the Platform API key configured, Govee2MQTT selected its Platform API
path and received successful `DynamicScene` responses for both H60A1s.
`Aurora` at 50 percent brightness was then applied together to the Bed and
Desk lights and visually confirmed to animate on both physical lights. This
visual acceptance is the evidence that closes the H60A1 effect issue.

The official API republishes virtual `All`, `Ceiling`, `Floor`, `Bed`, and
`Desk` group records. They are bridge metadata, not additional physical
lights. Verification filters physical inventory explicitly and still requires
exactly two H60A1s, one H6072, one bridge, 37 physical light entities, all 34
segments, and the preserved main entity IDs `light.bed_light`,
`light.desk_light`, and `light.rgbicww_floor_lamp_2`.

The catalogs expose 72 effects on each H60A1 and 69 on the H6072. Six legacy
H6072 scene references used the unavailable label `Fireplace`; they now use
`Fire`. All 67 saved Govee effect references pass the live catalog audit.
Catalog verification remains useful for saved-scene compatibility, but is not
treated as proof that a physical moving effect ran.

The add-on web UI is directly available on the HAOS address at
`http://192.168.0.125:8056/assets/index.html`. The hostname
`ha.rafael.media` terminates at Nginx Proxy Manager for port 8123 and does not
forward port 8056, so `ha.rafael.media:8056` is not a valid route.

A focused pre-change rollback is retained inside VM104 at
`/config/upgrade-rollbacks/govee-rebuild-20260726`. It contains the device,
entity, and config-entry registries, Hub dashboard, scenes, and Govee2MQTT app
data from before the rebuild.

For clean recovery, bootstrap runs `hosts/haos/configure-govee.sh` after VM104
is available. The reconciler removes account credentials, installs the
recovered official key through the Supervisor API, restarts only Govee2MQTT,
and requires fresh Platform API device metadata before accepting a changed
configuration. It retains protected option rollbacks under
`/config/upgrade-rollbacks/dothomelab-govee`. If a working key was entered in
Home Assistant before it reached the recovery input, capture it once without
printing it:

```bash
./scripts/capture-haos-govee-api-key.py --env-file /root/.env --vmid 104
```

## Accepted residual issues

- Two configured ICS feeds return HTTP 422 from their remote provider. The
  component itself now imports; the share URLs must be replaced externally.
- BLE Monitor reports no Bluetooth controller because VM104 has no USB
  Bluetooth passthrough.
- Spotcast has no configured Spotify integration, and the installed Spotify
  dashboard card is retired upstream. Spotify/plugin functionality is
  explicitly non-blocking.
- Govee2MQTT's account-login client remains rejected by Govee's undocumented
  API. This is non-blocking because the accepted setup uses the separate
  official Platform API and does not configure account credentials.

## Backup and restore

Create a new full VM recovery point after an accepted HA migration:

```bash
/usr/local/sbin/dothomelab-haos-backup
```

The command refuses to overwrite artifacts and retains older images. A
separate cleanup review is required before deleting them.

On a clean PVE node, restore appdata and run normal bootstrap:

```bash
./bootstrap.sh --restore-latest
```

The HAOS restore path is automatic only when VM104 is absent. For an
application-level rollback, import the chosen protected native `.tar` through
Home Assistant and unlock it with `HA_BACKUP_PASSWORD`. For an OS-only failure,
use HAOS A/B boot-slot rollback before replacing the VM.

## Verification evidence

The accepted final state is HAOS 18.1, Supervisor 2026.07.3, Core 2026.7.4,
Docker 29.5.3, stable/supported/running. QEMU guest agent responds, Core config
validation passes, the LAN UI and `https://ha.rafael.media` return HTTP 200,
Supervisor reports no unsupported or unhealthy condition, and its resolution
issue list is empty.

Govee verification additionally requires the running app, non-empty official
API key, no account credentials, exactly two physical H60A1s plus one H6072,
one bridge, only known physical/virtual models, 37 physical light entities
including all segments, preserved main entity IDs, no legacy `Fireplace`
effect references, and the required live effect catalogs. A changed recovery
configuration must also produce fresh Platform API light metadata. Final
moving-effect acceptance remains a physical observation; the latest accepted
test is `Aurora` on both H60A1s.

The protected pre-Platform-key Govee archive is 44,400,640 bytes and matched
SHA-256 between the guest and canonical appdata; its outer tar is readable.
Both migration-era native backups remain retained. The post-upgrade full VM
archive completed with guest filesystem freeze/thaw and passed full zstd and
VMA verification. A clean restore reapplies the current Govee key from
`/root/.env`, so these retained artifacts do not need to embed the later key.
This proves the artifacts are structurally recoverable; a destructive full-VM
restore test remains future evidence.

## Reviewed upstream releases

The migration review used the official Home Assistant Core release notes for
[2025.4](https://www.home-assistant.io/blog/2025/04/02/release-20254/),
[2025.5](https://www.home-assistant.io/blog/2025/05/07/release-20255/),
[2025.6](https://www.home-assistant.io/blog/2025/06/11/release-20256/),
[2025.7](https://www.home-assistant.io/blog/2025/07/02/release-20257/),
[2025.8](https://www.home-assistant.io/blog/2025/08/06/release-20258/),
[2025.9](https://www.home-assistant.io/blog/2025/09/03/release-20259/),
[2025.10](https://www.home-assistant.io/blog/2025/10/01/release-202510/),
[2025.11](https://www.home-assistant.io/blog/2025/11/05/release-202511/),
[2025.12](https://www.home-assistant.io/blog/2025/12/03/release-202512/),
[2026.1](https://www.home-assistant.io/blog/2026/01/07/release-20261/),
[2026.2](https://www.home-assistant.io/blog/2026/02/04/release-20262/),
[2026.3](https://www.home-assistant.io/blog/2026/03/04/release-20263/),
[2026.4](https://www.home-assistant.io/blog/2026/04/01/release-20264/),
[2026.5](https://www.home-assistant.io/blog/2026/05/06/release-20265/),
[2026.6](https://www.home-assistant.io/blog/2026/06/03/release-20266/), and
[2026.7](https://www.home-assistant.io/blog/2026/07/01/release-20267/).

HAOS review covered
[16.0](https://github.com/home-assistant/operating-system/releases/tag/16.0),
[17.0](https://github.com/home-assistant/operating-system/releases/tag/17.0),
[18.0](https://github.com/home-assistant/operating-system/releases/tag/18.0),
and [18.1](https://github.com/home-assistant/operating-system/releases/tag/18.1).
Custom-component decisions used the maintainers' releases for
[ICS Calendar 5.2.0](https://github.com/franc6/ics_calendar/releases/tag/5.2.0),
[BLE Monitor](https://github.com/custom-components/ble_monitor/releases), and
[Govee](https://github.com/LaggAt/hacs-govee/releases).

[govee-h60a1-lan]: https://github.com/wez/govee2mqtt/issues/406

# Unexpected host reset and service recovery — 2026-10-28

Inspected live PVE `afa` over SSH and its guests through `pct exec`, starting
at 13:46 CET. Rafael reported no household power outage and confirmed that the
server restarted itself. Repository/PVE baseline: `db2f54f33797f0cb63879a1ca7f4a4a5527f230b`.
The existing services recovered; the host reset's trigger remains unproven.
VM101 remains stopped at Rafael's explicit request.

## Reset evidence

- Previous boot journal ends at **13:42:18 CET**; the new boot begins at
  **13:43:21 CET**, boot ID `832a146963c3435aa54e3cf88dd8e911`.
- No orderly shutdown, power-button event, host OOM kill, kernel panic,
  lockup or watchdog-expiry message was found in the preceding boot.
  No persisted crash record was present under `/sys/fs/pstore` or
  `/var/lib/systemd/pstore`. Missing records cannot exclude a sudden failure
  before logs were flushed.
- Prometheus's saved host measurements at 13:41 show **5.77% CPU** and
  **37.42% memory**; maximum recorded memory over the preceding 30 minutes
  was **37.60%**. This does not support resource exhaustion as the trigger,
  but these samples cannot resolve the final seconds.
- There was also an abrupt journal boundary on October 27 at 17:33:45,
  followed by a boot at 17:34:59. October 15, 27 and 28 boots all report
  kernel `6.17.4-1-pve`; this incident did not install a new kernel.
- Runtime systemd watchdog is disabled. Proxmox's software watchdog starts,
  but there are no configured HA resources or recorded expiry identifying
  it as the cause. Panic-on-OOM/oops and automatic panic reboot are disabled.

The evidence establishes an abrupt host restart, not its physical/software
cause. A local power/PSU/board interruption or unrecorded hard reset remains
possible despite household power staying on. No deliberate crash, stress test,
host reboot, package upgrade, or firmware change was used to reproduce it.

## Confirmed storage connection fault

`/dev/sdd`, WD Red Plus 12 TB **serial `D7JE3UKN`**, on `ata4`, reports fresh
`ATA bus error`, `BadCRC`, interface-fatal errors and read I/O errors during
both October 27 and October 28 boots. Linux retries/reset the link and reduces
its negotiated speed from 6 to **3 Gbit/s**. SMART UDMA CRC count is **194**,
up from **182** in the [October 7 incident](../zotero-lxc-outage-2026-10-07.md).
Reallocated, pending and offline-uncorrectable sector counts are all zero.
No further matching kernel errors appeared after the current boot completed;
the CRC count remained 194 at the final check.

These are transmission-path errors. Linux documents this distinction and
speed reduction as an error-recovery measure in its
[libATA guide](https://cdn.kernel.org/doc/html/latest/driver-api/libata.html#ata-bus-error).
The specific cable, connector, controller or drive-side component has not been
isolated. The timing does **not** prove that this fault caused the host reset.
During a planned safe shutdown, inspect/reseat or replace this drive's SATA data
cable and inspect its power connection; record the serial, not only `/dev/sdd`.
If resets persist, physical PSU/board/RAM investigation and better crash capture
remain necessary. No physical repair was performed remotely.

Both `rpool` and `vault` are ONLINE with zero recorded ZFS read/write/checksum
errors and no known data errors. Canonical appdata/shared mounts resolve to
their expected datasets. This is a health check, not a new scrub or restore.
NVMe SMART reports zero media/integrity errors and zero error-log entries;
its cumulative 68 unsafe shutdowns cannot date or explain this specific event.
Current CPU readings were 43–57°C and NVMe 45°C; pre-reset CPU temperatures
were not retained. SSD available space was approximately 78 GiB.

## Recovery and focused repair

Proxmox automatically started CT110, CT113, CT112, CT102, VM104, CT114 and CT115
in configured order, finishing at **13:46:58 CET**. All six LXCs retain `onboot=1`.
VM101 lacks autostart and was already stopped when inspected. A proposed start
was rejected by automatic approval review; Rafael then explicitly chose to
leave it off. Its disk was only inspected, never started or changed.

Homarr alone needed repair: HTTPS `https://rafael.media` returned 502 and
CT110/PVE could not reach `172.19.0.6:7575`. Inside its namespace, both loopback
and that address returned 200. `eth0`'s host peer `veth3314a2b` lacked a bridge
master, while its Compose network was `br-ecf3da1cf6e3`. No duplicate MACs were
present in the inspected Infra Docker networks. The internal health check
could not detect this disconnected interface.

Ran `pct exec 110 -- docker restart --time 30 homarr`. Docker created a new
peer attached to the correct bridge. The same container ID (`cd14f9ec22d9…`),
image `sha256:825ce7c78bc63f746c0b58208968cf10820449da85f7d3d6c71a49556c78b7f0`,
configuration and canonical appdata remained in use. Direct and HTTPS probes
then returned 200. This repairs the observed network failure; its underlying
startup cause was not reproduced or established. No Compose deployment, image
pull, database replacement, migration or data restore occurred.

Loki briefly returned readiness 503 after boot, then recovered without a
restart. Its readiness endpoint and actual log ingestion passed subsequently.

## Final verification and limits

- **89 Docker containers running**: CT102 21; CT110 19; CT112 42; CT114 6;
  CT115 1. None stopped, restarting, unhealthy or still in health-starting
  state at the final check. Some containers have no Docker health check.
- All six LXCs and Home Assistant VM104 running. PVE and the inspected Docker
  guests have no failed systemd units. Native blog listeners on CT114/115,
  CT110 publisher/SMB/Tailscale and PBS services are active. DNS answers from
  `192.168.0.100`; Home Assistant's direct HTTP endpoint returns 200.
- The 70 enabled NPM hostnames were probed through the real TLS virtual hosts.
  After the Homarr repair, 67 respond below 500. Pi-hole's meaningful `/admin/`
  redirects normally and Loki `/ready` returns 200; their bare roots are 404.
  The three unavailable pre-existing routes are `openwebui.rafael.media`
  (invalid legacy upstream `0.0.0.0:8080`), `obsidian.rafael.media`
  (absent legacy CouchDB at Apps port 5984), and `paperless-gpt.rafael.media`
  (absent service at Apps port 8003; known credential blocker). No dummy key
  or substitute service was introduced. Syncthing is running normally.
- From the operator Mac, Homarr, public `rafael.ink`, Pulse and private blog
  staging all return 200. This is endpoint reachability, not every authenticated
  application workflow or an independent external-WAN uptime test.
- All **34 existing Prometheus probes** pass, with no failed scrapes or stale
  fleet resources. Pulse verification covers every managed Docker host and
  current container. Homarr Staging reconciliation reports six apps and no
  pending change. Homarr's own failed route was not covered by those 34 probes;
  the broad route scan found it despite its healthy internal check.
- The installed shared verifier at observability revision `d3615844929f6d65316515e43c2086ca86999788`
  passes authenticated Grafana/datasource checks, fresh fleet measurements,
  five staging page probes, seven scrapes, five rule evaluations and a unique
  sanitized 404 log-ingestion probe into Loki. Alert delivery remains unconfigured.
- Scheduled appdata PBS backup finished successfully at **02:24:13 CET**,
  snapshot `host/afa-appdata/2026-10-28T01:09:56Z`. No new backup or restore
  test ran. `/vault/shared` remains outside that backup. The subsequent WUD
  run failed at 02:26:13, a separate existing maintenance issue; it was not retried.

No temporary containers, source worktrees or data copies were created by this
incident response. Existing staging/production build caches are 21.07/9.7 GB;
their images, current/previous releases and all durable rollback material were
retained. No deletion or pruning was needed for recovery. Guest deployed
archives remain CT102 `a4f1374`, CT110/114 `db2f54f`, CT112 `f35bedc`, CT115
`9c2c154`. No application code was promoted or released. Existing unrelated
local documentation drafts were preserved.

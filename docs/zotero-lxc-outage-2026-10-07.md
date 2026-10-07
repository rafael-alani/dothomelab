# Zotero and LXC outage repair — 2026-10-07

PVE booted on October 6 at 14:25 CEST. Its startup log only started VM104,
CT114 and CT113. CT102, CT110 and CT112 had no `onboot` or `startup` settings
and were started at 20:24 CEST. Enabled onboot and inventory startup orders
for all managed guests; bootstrap now reconciles existing guests and verification
checks these settings. No host reboot or guest stop was performed.

The main guests were running at investigation time. Pi-hole answered internally
but its published DNS address timed out, including from the Mac over Tailscale.
Direct TLS access to NPM succeeded. Docker inspection found stale explicit
legacy generated MAC addresses and duplicate MACs in Infra, Paperless,
Grimmory and media networks. Paperless and Grimmory repeatedly failed to reach
their private cache/database. WUD's pinned clone implementation copied both
Config.MacAddress and endpoint MacAddress into replacement configuration.

Recreated the affected application containers sequentially with Compose,
no dependencies, no image pulls and overrides pinned to their exact running
image IDs: Pi-hole, Homarr, Cloudflare DDNS, Infra Portainer/Agent, Grimmory,
Paperless-ngx, Seerr and Jellystat. No database containers were replaced and no
application data was deleted. Configuration/inspection rollback evidence is
root-only under `/root/dothomelab-incident-20261007T105154`. The scheduled
appdata backup completed successfully at 02:24 CEST on October 7; no new backup
or restore test was run for this repair.

WUD's compatibility preload now strips legacy Docker-generated `02:42:*`
MACs from replacements, preserves custom MACs/static IPAM, and avoids mutating
the original inspection. Tests cover this behavior and existing pull safeguards.
The repository declares no explicit Docker MACs. Future explicit `02:42:*`
configuration requires reviewing this heuristic. Existing unaffected legacy
containers may retain copied MAC configuration until their next replacement;
no broad fleet restart was performed.

Attachment `63SW4L56` was absent from WebDAV and present in the Mac's Zotero
storage, marked for upload with no synced hash/time. The user will perform
native Zotero sync and then ZotFlow refresh/reopen. No paper was manually
uploaded and neither application's database or client settings were changed.
The WebDAV verifier now tests HTTPS PUT/GET byte comparison in addition to
its direct-service/authentication/PROPFIND checks.

ZFS reports both pools healthy with zero recorded data errors. The boot log
also contains SATA interface errors on sdd; SMART has 182 historical CRC
errors, zero pending/reallocated/uncorrectable sectors. The prior journal ends
without an orderly shutdown record. The cause of the host restart is not
established; physical SATA cable/power inspection remains external work if
errors recur. The startup policy is verified without a destructive reboot test.

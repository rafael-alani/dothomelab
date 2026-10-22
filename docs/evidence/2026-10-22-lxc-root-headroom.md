# Production LXC root headroom — 2026-10-22

Applied on PVE `afa` on October 22, 2026, Europe/Amsterdam, following explicit
authorization to give the three production LXCs more disk space. The PVE source
baseline was `2801876c736c1bdc4d392035bb9b977b70114e45`.

## Change and verification

| Guest | Previous quota | New quota | Used | Available after resize |
|---|---:|---:|---:|---:|
| CT102 Servarr | 32 GiB | 64 GiB | 13.9 GiB | 50.1 GiB |
| CT110 Infra | 16 GiB | 64 GiB | 15.2 GiB referenced | 48.8 GiB |
| CT112 Apps | 64 GiB | 192 GiB | 63.7 GiB referenced | 128 GiB |

Applied `pct resize <CTID> rootfs <size>G`, one guest at a time, with Proxmox's
configuration digest guard. Before each operation, checked the exact volume,
previous quota, running state, absence of a guest lock and available pool space.
Confirmed the resulting Proxmox rootfs declaration, ZFS refquota and guest `df`.
Docker container IDs, start times and restart counts were unchanged across each
resize: CT102 21 containers, CT110 12, CT112 44. No guest or service was restarted.

No pool capacity was reserved: ZFS reservation and refreservation remain `none`.
The pool retained approximately 394 GiB usable free after the changes. Quotas
share that free capacity with appdata and staging; they are not guaranteed
independent disk allocations. No data, images, rollback assets or snapshots
were deleted. No permissions, mounts or Docker data-root settings changed.

PBS's 10 GiB root had 8.79 GiB free; staging already had a 500 GiB thin root
quota and about 394 GiB available from the shared pool; HAOS had 18.7 GiB free
on its data filesystem. These did not require expansion.
VM101 also retained 104 GiB free on its existing root filesystem.

## Storage clarification

Docker images and layers are in `/var/lib/docker` within each LXC root, backed
by SSD `rpool/data/subvol-<CTID>-disk-0`. A full guest refquota can prevent image
pulls despite ample free pool space. Durable appdata is separately bind-mounted
from `rpool/appdata/docker` at `/srv/appdata/docker` (CT102 sees `/docker`).
`/vault/data` belongs to the HDD `vault` pool and holds VM101's disk, not these
Docker image stores. See [architecture](../architecture.md).

## Update verification remains pending

The October 22 scheduled appdata backup succeeded at 02:18:31 CEST. The WUD
handoff failed at 02:19:42, before this capacity change. No backup, scan, image
pull or updater was started manually. The next observed backup timer is
**October 23 at 02:03:48 CEST**; automatic updates follow its successful completion.

Increasing capacity removes the observed disk-quota blocker. It does not prove
that the next WUD run will succeed or resolve registry HTTP 429 responses.
Check the next normal handoff's journal, changed image identities and container
health before claiming automatic updates have resumed. Immich remains outside
automatic updates.

Wizarr remains unhealthy. Immich machine-learning briefly reported unhealthy
but returned to healthy on the repeat check without a restart. Service diagnosis
and update acceptance remain separate work.

## Persistence, checks and rollback limits

`provision/inventory.env` declares the new sizes for clean rebuilds. The focused
release is published on `codex/lxc-root-headroom`, based on the PVE checkout,
to preserve unrelated local and remote work. Existing production roots must
match inventory before full bootstrap validation; bootstrap was not run.
Guest source archives were not replaced because no guest software changed.

Checked inventory Bash syntax, documentation links, diff whitespace, live
quota/mount mappings and running-container identity/start/restart continuity.
No application workflow or recovery restore was performed.

The previous source revision remains available in Git. Reverting inventory
alone does not resize existing guests. Proxmox does not support shrinking with
`pct resize`; retain the expanded quotas instead of attempting an implicit
shrink after new data occupies the space.

[Evidence index](README.md) · [Current status](../status.md)

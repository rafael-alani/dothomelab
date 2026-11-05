# Routine host maintenance

`scripts/install-routine-maintenance.sh`, run on PVE, installs the checked-in
unattended-upgrades policy on PVE and all six managed LXCs. Bootstrap invokes
it after provisioning the guests. It also installs the existing bounded
build-cache helper on Staging and Production without replacing their project
archives or deployed application revisions.

After a successful scheduled appdata backup, the existing WUD unit first runs
`/usr/local/sbin/dothomelab-os-update`, then the sequential WUD updater. There is
no separate update timer. An OS maintenance failure fails that unit before image
replacement; inspect `journalctl -u dothomelab-wud-update.service` and the guest's
`/var/log/unattended-upgrades/` for the cause. Fix it and rerun the unit using the
current successful backup; do not bypass a failed backup to force an update.

The APT policy permits Debian base, updates and security repositories **within
the installed codename**, plus the corresponding Proxmox repository. This
covers routine PVE/PBS fixes and new PVE kernel packages without switching
Debian/PVE/PBS major releases. Docker's separate repository is not enrolled:
engine/Compose changes remain a focused runtime upgrade. Unattended-upgrades
retains its normal conffile/dependency safeguards and reports held packages.
It must not remove unused kernels or packages, downgrade, or reboot. Existing
kernel fallbacks remain. New kernels need an explicitly authorized PVE reboot;
the maintenance log prints the running kernel and installed boot selections.
Package installation does not itself prove that every running process has
loaded a patched library. Review runtime restart requirements after security
updates. Routine package updates are not a replacement for migration review.

The same backup handoff caps **unused Docker build cache** at 5 GB on CT114 and
CT115. The helper takes the deployment lock and preserves running containers,
all images, current/previous releases, volumes and data. It never prunes images
or volumes. Protected receipts remain under each environment's
`runtime-cleanup/`. A busy build/deployment fails closed; retry after it finishes.
Native blog code/dependency/site cache already retains its current and previous
release through its separate builder. Retained legacy images still require
explicit removal approval.

## Checks and rollback

On PVE, `/usr/local/sbin/dothomelab-os-update --dry-run` refreshes APT metadata,
simulates unattended upgrades on every guest and PVE, and prints cache cleanup
plans without deleting cache. `WUD_UPDATE_DRY_RUN=true` in the existing root-only
WUD unit configuration also makes its OS pre-step a dry run. Verify
`APT::Periodic::Unattended-Upgrade=0`, disabled `apt-daily-upgrade.timer`, and the
single backup `OnSuccess` handoff; do not enable a second installer schedule.

To suspend automatic routine maintenance, set `WUD_UPDATE_DRY_RUN=true` in
`/etc/dothomelab/wud-update.conf`. This also pauses WUD replacements while
retaining backup and discovery. Keep the installed policy and package history;
do not remove a running kernel. Package rollback is not automatic or atomic:
it depends on retained kernel boot options, package availability and the Git
rebuild contract. Major upgrades and data-bearing applications retain their
specific rollback procedures.

The November 5 fleet dry run passed. The next scheduled backup-triggered apply
is a separate future execution, not claimed as already tested.

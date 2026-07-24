# Obsidian sync and off-site backup

This Infra project runs Syncthing continuously and the official Proton Drive
CLI as an on-demand Compose profile. The authoritative recovery set is Git,
`/vault/shared`, and `/srv/appdata/docker`; no container-local volume is used.

## Data and behavior

- Syncthing state and device keys: `/srv/appdata/docker/syncthing`
- Proton session, GPG/password-store, cache, and last archive:
  `/srv/appdata/docker/proton-drive`
- plaintext vault: `/vault/shared/media/obsidian`
- Syncthing versions: `/vault/shared/media/.obsidian-versions`
- laptop and phone: Send & Receive
- Infra: Receive Only, `ignoreDelete=false`
- server versioning: staggered, 365 days, separate path on the same ZFS dataset

Syncthing must write the server copy to apply laptop and phone changes. Receive
Only prevents server-local changes from being announced to the cluster; it is
not a filesystem permission mode. Only Syncthing mounts the vault read-write.
The Proton container mounts it read-only.

The GUI listens at `127.0.0.1:8384` inside CT110. Nginx Proxy Manager can reach
that address because it uses host networking, but the GUI is not directly
published to the LAN or Internet. TCP/UDP 22000 and discovery UDP 21027 remain
available on `192.168.0.110`.

## Deploy

Run on the Proxmox host after the repository commit has been synced:

```bash
scripts/sync-guest-repo.sh 110
ssh root@192.168.0.250 -- pct exec 110 -- \
  /opt/dothomelab/hosts/infra/obsidian-sync/prepare.sh
scripts/deploy-compose.sh 110 hosts/infra/obsidian-sync/compose.yaml
ssh root@192.168.0.250 -- pct exec 110 -- \
  docker compose -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
  --profile proton build proton-drive
ssh root@192.168.0.250 -- pct exec 110 -- \
  /opt/dothomelab/hosts/infra/obsidian-sync/configure-syncthing.sh \
  EXISTING_LAPTOP_FOLDER_ID
ssh root@192.168.0.250 -- pct exec 110 -- \
  /opt/dothomelab/hosts/infra/obsidian-sync/install-systemd.sh
```

The installer deliberately leaves the timer disabled until Proton authentication
and the first restore-verified upload have succeeded.

## Complete the one-time setup

Run shell commands in this section inside CT110 (or prefix them on the Proxmox
host with `pct exec 110 --`).

1. In NPM, add a private proxy host for the desired Syncthing hostname to
   `http://127.0.0.1:8384`. Enable WebSocket support and restrict access to the
   LAN/Tailscale; do not create a public Cloudflare route.
2. Open the Syncthing GUI and immediately set a GUI username and strong password
   under Settings > GUI. The loopback binding and NPM restriction protect the
   unauthenticated first start.
3. Confirm `Obsidian Vault` is Receive Only, versioning is Staggered with 365
   days, the folder path is `/vault`, and versions path is `/versions`.
4. Before pairing, take a separate laptop copy. In the laptop Syncthing UI,
   open the existing vault folder and copy its **Folder ID** (not its label).
   Preserve that ID by running:

   ```bash
   /opt/dothomelab/hosts/infra/obsidian-sync/configure-syncthing.sh \
     EXISTING_LAPTOP_FOLDER_ID
   ```

   While the server placeholder is unpaired and contains only Syncthing metadata
   plus `.stignore`, this safely replaces it without deleting files. Once paired
   or seeded, the script refuses an ID change.
5. Put the conservative rules from `stignore.example` on the laptop and phone
   too and audit `.obsidian/plugins` for tokens. The chosen policy syncs
   `.obsidian` and vault-local `.trash`, but excludes per-device workspace state.
6. Add the laptop and phone device IDs to Infra, and add Infra device ID to both.
   Share the existing vault folder among all three devices. Keep the laptop and
   phone folders Send & Receive and confirm Infra remains Receive Only. Seed
   from the laptop backup, not from stale phone/server content.
7. Authenticate Proton interactively from CT110:

   ```bash
   docker compose -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
     --profile proton run --rm proton-drive auth login
   ```

   Follow the printed URL in any browser. The terminal may remain on the server;
   Proton supports completing login on another device. The session is stored by
   `pass`, encrypted with the dedicated GPG key in appdata. The key has no
   passphrase because the systemd timer must unlock it unattended; this does not
   weaken the server's existing trust boundary because root can already read the
   plaintext vault.
8. Run the first backup and enable the daily, change-detecting timer:

   ```bash
   systemctl start dothomelab-obsidian-proton-backup.service
   journalctl -u dothomelab-obsidian-proton-backup.service --no-pager
   /opt/dothomelab/hosts/infra/obsidian-sync/install-systemd.sh --enable
   systemctl list-timers dothomelab-obsidian-proton-backup.timer
   ```

Every changed vault is archived while Syncthing is paused, uploaded under
`/my-files/Backups/Obsidian`, downloaded into appdata, and SHA-256 checked before
the job records success. Unchanged vaults do not upload. Remote archives are
timestamped and never automatically deleted; choose Proton retention manually
after several restore tests rather than automating destructive cloud cleanup.

## Verify and restore

Run:

```bash
/opt/dothomelab/hosts/infra/obsidian-sync/verify.sh
docker compose -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
  --profile proton run --rm proton-drive backup status
```

Test phone-to-Infra-to-laptop edits, a conflict, a deletion, restoration from
Syncthing versions, and laptop recovery after an offline edit before relying on
the topology.

To retrieve a Proton archive without any cloud-to-vault write path:

```bash
docker compose -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
  --profile proton run --rm proton-drive backup restore \
  obsidian-vault-YYYYMMDDTHHMMSSZ-SHA12.tar.gz
```

The verified archive lands in
`/srv/appdata/docker/proton-drive/restore`. Extract it to a new temporary
directory, compare notes/checksums, and only then copy selected data back to the
vault. Never point the Proton container or restore command at the live vault.

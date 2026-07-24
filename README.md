# dothomelab

Git-managed recovery definitions for the Proxmox homelab. Guest operating systems are disposable; the recovery set is this repository, the production `/root/.env`, application state under `/srv/appdata/docker`, and large shared data under `/vault/shared`.

Application guests are `servarr` (102), `infra` (110), and `apps` (112), plus VM 101 and HAOS VM 104. The protected PBS appliance remains in LXC 113. Pi-hole keeps service address `192.168.0.100` on `infra`; Apps runs Immich, media/Jellystat, Mealie, Portainer, and Zotero WebDAV as separate Git-managed projects.

## Back up before migration

- Put Compose definitions, scripts, mount requirements, versions, and restore notes in this repository.
- Put persistent Docker state under `/srv/appdata/docker/<service>`.
- Put large application-independent data under `/vault/shared`.
- Create application-consistent database dumps or quiesce writers before the appdata ZFS snapshot.
- Keep secrets only in the production `/root/.env`; the appdata PBS job includes it as an encrypted recovery archive when present.
- Keep the ignored migration ZIPs encrypted off-repository until Homarr and Pi-hole are restored and included in a verified PBS backup.

## Bootup / restore

1. Reinstall Proxmox VE and import the `vault` pool.
2. Clone this repository and recover the off-host PBS encryption key and administrator password.
3. Recreate the PBS LXC, bind-mount `vault/pbs_datastore`, and reconnect the `appdata` datastore.
4. Restore `appdata.pxar` to `/srv/appdata/docker` and the encrypted production `.env` archive to `/root/.env`.
5. Recreate CT110 and CT112, bind `/srv/appdata/docker` into both, bind `/vault/shared` read-only into `apps`, and pass `/dev/dri` into `apps`.
6. On the Proxmox host, run `scripts/sync-guest-repo.sh` for each LXC, then run each stack's `prepare.sh` inside its guest.
7. Deploy Infra, then Apps `immich`, `media`, `mealie`, `services`, and `zotero-webdav` with `scripts/deploy-compose.sh`. Restore Mealie through its backup UI/API when rebuilding without appdata.
8. Run `hosts/infra/cockpit/install.sh` in CT110. Enable `dothomelab-pihole-ip.service` only when the old DNS service is offline.
9. Verify DNS on `192.168.0.100`, Cockpit on `192.168.0.110:9090`, Homarr on 7575, Seerr on 5055, Jellyfin on 8096, Jellystat on 3000, Mealie on 9925, Immich on 2283, Portainer on 9443/9001, Zotero WebDAV on 8088, GPU access, mounts, proxy routes, WUD, and backups.

See [`backup/pbs/README.md`](backup/pbs/README.md) for the backup and recovery implementation.

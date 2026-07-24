# Cockpit files and SMB

Observed 2026-07-24: Cockpit Files and File Sharing were installed; Cockpit,
Samba, Avahi, and WSD were active; NFS/NetBIOS services were inactive; and the
focused verifier confirmed authenticated `Vault` and `Media` access on the LAN.
The current Samba private database and Infra account hash were also captured
under SSD appdata for clean-guest recovery.

Cockpit runs natively in CT110 and uses add-on packages for file navigation and
share management:

- `cockpit-files` is the first-party Cockpit file browser. Use Cockpit's
  **Administrative access** mode when a protected appdata directory requires
  root privileges.
- `cockpit-file-sharing` is the 45Drives Bookworm package. Its Samba page edits
  Samba's registry backend through `net conf`.
- `samba-registry.conf` is the Git source of truth for the registry
  configuration. `/etc/samba/smb.conf` contains `include = registry`.
- `/srv/appdata/docker/infra-samba/private` is the durable Samba private
  directory after a clean rebuild.

The network shares are:

- `Vault` at `/vault/shared`
- `Media` at `/vault/shared/media`

`Media` is intentionally also reachable as a directory inside `Vault`. Do not
export `/srv/appdata/docker`: it contains live databases, service credentials,
and application state. Inspect appdata through Cockpit Files with
administrative access instead.

The SMB share is restricted to the existing Linux user `afa`, disables guest
access and SMB1/NetBIOS, and accepts clients only from the LAN. Samba's `fruit`,
`catia`, and `streams_xattr` modules provide macOS
metadata and directory-enumeration support. Avahi advertises SMB to Finder on
the LAN, while WSD advertises it to current Windows clients. WSD is restricted
to CT110's LAN address and Avahi to its LAN interface, so neither discovery
service publishes on Docker bridges.

Private-key directories, `.env` files, and the legacy `/vault/shared/compose`
tree are hidden from SMB. They remain available locally through Cockpit Files
administrative access.

## Install and authenticate

`./bootstrap.sh` runs `install.sh` automatically. The installer creates the
numeric `afa` account, restores its captured password hash when present,
installs the pinned Cockpit add-ons and Samba packages, imports the Git
configuration, points Samba's private directory at SSD appdata, and enables
Cockpit, SMB, Avahi, and WSD. It disables NFS and legacy NetBIOS. The 45Drives
package pulls in NFS packages, but this deployment stops their NFS/RPC
services because no NFS export is configured.

The current Samba password database is captured at
`/srv/appdata/docker/infra-samba/private/passdb.tdb`. If that recovery file is
absent, set `SAMBA_PASSWORD` or `INFRA_ADMIN_PASSWORD` in the production
`/root/.env`; the installer creates the account non-interactively. An explicit
manual reset remains available:

```bash
smbpasswd -a afa
```

The Samba password may match the Linux/Cockpit password, but it remains a
separate private database. Run `verify.sh` after any credential or share
change.

## Connect clients

- macOS Finder: **Go → Connect to Server**, then
  `smb://192.168.0.110/Vault` and `smb://192.168.0.110/Media`
- Windows Explorer: `\\192.168.0.110\Vault` or
  `\\192.168.0.110\Media`
- Linux file manager: `smb://192.168.0.110/Vault` or
  `smb://192.168.0.110/Media`
- Linux mount: use `mount.cifs //192.168.0.110/Vault <mountpoint> -o
  username=afa,vers=3.1.1`, substituting `Media` when wanted

Use `afa` and the Samba password. Finder and Windows discovery are conveniences;
the explicit address is the deterministic connection method. SMB, WSD, and
mDNS are LAN-only; remote administration continues through Cockpit's existing
HTTPS/Tailscale path.

## Cockpit changes and Git

The File Sharing UI writes to Samba's replaceable registry database. After an
intentional change, export and review its text representation before replacing
the repository file:

```bash
net conf list
```

The installer backs up the previous `/etc/samba/smb.conf` and registry export
under `/var/backups/dothomelab-samba/<UTC timestamp>` before importing Git.
Samba passwords are never included in the Git export.

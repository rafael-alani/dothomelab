# Cockpit files and SMB

Cockpit runs natively in CT110 and uses add-on packages for file navigation and
share management:

- `cockpit-files` is the first-party Cockpit file browser. Use Cockpit's
  **Administrative access** mode when a protected appdata directory requires
  root privileges.
- `cockpit-file-sharing` is the 45Drives Bookworm package. Its Samba page edits
  Samba's registry backend through `net conf`.
- `samba-registry.conf` is the Git source of truth for the registry
  configuration. `/etc/samba/smb.conf` contains `include = registry`.

The only network share is `shared` at `/vault/shared`. Do not export
`/srv/appdata/docker`: it contains live databases, service credentials, and
application state. Inspect appdata through Cockpit Files with administrative
access instead.

The SMB share is restricted to the existing Linux user `afa`, disables guest
access and SMB1/NetBIOS, and accepts clients only from the LAN and Tailscale
ranges. Samba's `fruit`, `catia`, and `streams_xattr` modules provide macOS
metadata and directory-enumeration support. Avahi advertises SMB to Finder on
the LAN, while WSD advertises it to current Windows clients.

## Install and authenticate

Run `install.sh` as root in CT110. It installs the pinned, checksum-verified
Cockpit add-ons and Debian Samba packages, imports the Git configuration, and
enables Cockpit, SMB, Avahi, and WSD. It disables NFS and legacy NetBIOS.

Samba deliberately has a separate password database that is not committed to
Git. Set or reset the password interactively after a rebuild:

```bash
smbpasswd -a afa
```

The Samba password may match the Linux/Cockpit password, but it is stored
separately. Run `verify.sh` after setting it.

## Connect clients

- macOS Finder: **Go → Connect to Server**, then
  `smb://192.168.0.110/shared`
- Windows Explorer: `\\192.168.0.110\shared`
- Linux file manager: `smb://192.168.0.110/shared`
- Linux mount: use `mount.cifs //192.168.0.110/shared <mountpoint> -o
  username=afa,vers=3.1.1`

Use `afa` and the Samba password. Finder and Windows discovery are conveniences;
the explicit address is the deterministic connection method. Tailscale clients
can use CT110's Tailscale IPv4 address instead.

## Cockpit changes and Git

The File Sharing UI writes to Samba's registry database. After intentionally
changing settings in Cockpit, export the text representation and review it
before replacing the repository file:

```bash
net conf list
```

The installer backs up the previous `/etc/samba/smb.conf` and registry export
under `/var/backups/dothomelab-samba/<UTC timestamp>` before importing Git.
Samba passwords are never included in the exported configuration.

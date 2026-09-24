# macOS Media reconnect and Kew

Install as the logged-in Mac user:

```bash
bash clients/macos-media/install.sh
```

Requires Apple's Command Line Tools, Fish, Homebrew Kew, and the existing
`afa` SMB login saved in the user's Keychain. First-time authentication can be
completed in Finder at `smb://afa@192.168.0.110/Media`. The installer does not
read, copy, or store credentials. This is a desktop client setup, independent
of PVE bootstrap and guest deployment archives.

The user LaunchAgent `media.rafael.homelab-media` runs at login and every
30 seconds while awake. It restores the read-only share at `/Volumes/Media`
using native NetFS/NetAuth with authentication UI disabled. Healthy mounts are
left alone. When disconnected, it checks TCP 445 and the declared Infra NIC
MAC (`BC:24:11:EB:87:25`) before mounting, so it stays quiet away from the home
LAN. The MAC check avoids accidental connections on overlapping private
networks; it is not cryptographic server authentication. Routed/Tailscale-only
access is deliberately not an automatic mount path.

Each run has a 25-second deadline and each directory probe has a five-second
deadline. Concurrent Kew/launchd attempts are serialized. A stale mount is
detached only with a normal, non-forced Disk Arbitration unmount while the
home server is reachable; busy mounts are left to native SMB recovery. A
conflicting `/Volumes/Media` path or an existing mount at a different path is
left unchanged rather than deleted or replaced. No files on the share change.

The Fish `kew` function reconnects before starting Homebrew Kew, preventing a
new empty scan while offline. Help/version/path/theme commands still work
offline. Kew's configured library remains `/Volumes/Media/music`. If Kew was
already running with an empty library, press `u` once after reconnecting.
This does not cache music for offline playback or promise uninterrupted
playback while changing Wi-Fi. Normal recovery is the next 30-second tick,
plus the mount time; launching `kew` triggers an immediate attempt.

macOS Files and Folders permissions apply separately to calling applications.
If the terminal is denied Network Volumes access, allow it for that terminal
in System Settings. An agent success does not grant Codex or a terminal extra
filesystem permissions.

## Tailscale exit-node compatibility

When using a Tailscale exit node, enable **Allow Local Network Access** in
Tailscale's Exit Node menu. This is a persistent client preference. It lets
the Mac reach its current LAN directly while internet traffic continues
through the selected exit node. The reconnect agent never changes VPN settings.

For the standalone macOS app, the equivalent command is:

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale set --exit-node-allow-lan-access=true
```

On 2026-09-24, this preference was false: the home subnet was routed through
`utun5`, native NetFS returned error 60, and the mount stayed absent despite
TCP 445 probes succeeding. Enabling the preference restored the `en0` route
and the existing agent mounted successfully. A TCP probe or cached ARP entry
alone therefore does not prove native SMB connectivity. Check:

```bash
/sbin/route -n get 192.168.0.110
```

At home this should select the active LAN interface, not a VPN `utun` interface.
To reverse the preference change, use the same command with `=false`; local
SMB mounting may then fail while an exit node is active. See the official
[Tailscale exit-node setup documentation](https://tailscale.com/docs/features/exit-nodes/how-to/setup?tab=macos).

## Verify and rollback

```bash
launchctl print "gui/$(id -u)/media.rafael.homelab-media"
mount | grep '/Volumes/Media'
"$HOME/Library/Application Support/dothomelab-media/media-reconnect" --check
```

The agent's last exit code is zero only when the expected mount and readable,
nonempty music directory are verified. An offline run exits 1 quietly. To
test remounting, stop playback, run `diskutil unmount /Volumes/Media`, confirm
it is absent, and wait for the next tick. Do not force an in-use mount off.

Disable automatic reconnect without touching the mount or any media:

```bash
launchctl bootout "gui/$(id -u)/media.rafael.homelab-media"
launchctl disable "gui/$(id -u)/media.rafael.homelab-media"
```

Restore any prior `kew.fish` from the installer's timestamped `.before-*`
copy, or rename the installed function out of Fish's functions directory and
run `functions --erase kew` in existing shells. The installer backs up existing
helper, plist, and Fish function before replacement. Re-run it to re-enable.

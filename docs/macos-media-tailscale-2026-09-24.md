# Media reconnect with a Tailscale exit node — 2026-09-24

The Mac again had no Media mount. The existing reconnect LaunchAgent was
loaded (1,014 runs at initial inspection) but its last exit code was 1.
Infra CT110, Samba, its canonical shared mount, and ZFS were healthy.

The installed helper returned `NetFS 60` (timeout). TCP 445 was reachable
and the Infra MAC matched, but macOS's route to `192.168.0.110` selected
Tailscale `utun5` rather than Wi-Fi `en0`. The Mac was physically on the home
LAN at `192.168.0.191`. Tailscale had an exit node selected and
`ExitNodeAllowLANAccess=false`.

Changed only that persistent Mac preference using:

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale set --exit-node-allow-lan-access=true
```

The selected exit node, accepted subnet routes, and running state were
unchanged. The SMB destination then selected `en0`; the unchanged installed
mount helper successfully restored the read-only `/Volumes/Media` mount.
No server, credentials, media, or reconnect binary was modified.

Verification:

- The background agent exited 0, verifying expected mount identity and
  readable, nonempty music directory.
- `diskutil unmount /Volumes/Media` succeeded and absence was verified.
- The regular scheduled agent restored the mount in **4.1 seconds** with
  Tailscale still active, then exited 0.
- Server-side `smbstatus --shares` confirmed `Media` connected from the Mac's
  LAN address `192.168.0.191`.

This verifies recovery with the exit-node configuration that caused this
incident; physical Wi-Fi roaming and audible Kew playback were not tested.
The persistent setting and its reversal are documented in the client README.

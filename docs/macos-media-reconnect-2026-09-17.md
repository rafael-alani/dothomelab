# macOS Media reconnect repair — 2026-09-17

Kew displayed `No music found at /Volumes/Media/music` after returning from
another Wi-Fi network. Live inspection found no SMB mount on the Mac and no
mount recovery LaunchAgent. Kew 4.2.7 retained the correct library path.
Infra CT110 and `smbd` were running, the canonical shared dataset was mounted,
and ZFS pools reported healthy. No server change was needed.

Installed the reproducible `clients/macos-media` client for Rafael on macOS
26.5.2: native Keychain-backed, UI-free, read-only mounting; login and 30-second
retry; home LAN NIC guard; bounded probes; and a Fish function that mounts
before opening Kew. Existing settings and media are retained. Rollback and
fresh-client prerequisites are documented in the client README.

Evidence:

- Compiled the Objective-C helper with `-Wall -Wextra -Werror`.
- Shell/Fish syntax and generated LaunchAgent plist validation passed.
- A saved SMB login exists; no password was retrieved or logged.
- The native mount succeeded at exactly `/Volumes/Media` as `afa`, read-only.
- The LaunchAgent's successful exit verifies the mount identity and a
  readable, nonempty `/Volumes/Media/music` directory.
- `diskutil unmount /Volumes/Media` succeeded, the mount was confirmed absent,
  and the scheduled agent restored it automatically in **19.3 seconds**.
  Its last exit code was 0 after remounting.

Verification limits: macOS denied Codex's direct directory enumeration of
the network volume, while the desktop LaunchAgent's own read check passed.
The computer-use tool disallowed access to Kitty, so the existing Kew window
was not refreshed and audible playback was not verified. Pressing `u` once
refreshes an already-empty Kew view. A real away/home Wi-Fi transition and
reboot/login test remain unperformed; Wi-Fi was not interrupted for testing.
No backups were run or claimed, and no server recovery input changed.

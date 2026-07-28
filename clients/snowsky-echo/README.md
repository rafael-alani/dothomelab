# SNOWSKY ECHO desktop sync

This is a macOS-to-microSD workflow. HifiMule and EchoList are interactive
desktop programs that need the locally mounted card, so neither belongs in the
Apps LXC or in Docker Compose.

The full operating decision and research record are in
[`docs/snowsky-echo-sync-2026-07-28.md`](../../docs/snowsky-echo-sync-2026-07-28.md).

## Install the pinned profile

1. Install and launch HifiMule once, then quit it completely.
2. From the repository root, run:

   ```bash
   python3 clients/snowsky-echo/install-hifimule-profile.py
   ```

3. Start HifiMule and select `SNOWSKY ECHO — Lossless` when initializing the
   card.

The installer refuses symlink and malformed targets, preserves all other
profiles, makes a timestamped backup, and atomically replaces the profiles
file. Running it again is a no-op.

The profile's default card layout is:

```text
/
├── .hifimule.json
├── .pinepods-echo.json       podcast compiler manifest
├── HifiMule-M3U/             HifiMule output; not relied upon by ECHO
├── Music/
    ├── Managed/              HifiMule owns this tree
    └── Playlists/            EchoList owns this tree
└── Podcasts/
    └── PinePods/             podcast compiler owns this tree
```

HifiMule 0.13 generates
`Music/Managed/Album Artist/Album/NN - Track.ext`. It does not currently
support a `YYYY - Album` path template.

## Obtain reviewed release files

The download helper fetches the exact Apple Silicon releases inspected for
this integration and verifies their published SHA-256 values. It does not
install or execute either program:

```bash
clients/snowsky-echo/download-verified-macos-releases.sh /private/tmp/snowsky-tools
```

Both upstream macOS artifacts are ad-hoc signed rather than Developer ID
notarized. Do not automate a Gatekeeper bypass. Review the release/source and
make the macOS trust decision explicitly.

## Configure HifiMule

- Server type: Navidrome/Subsonic
- Server: `https://navidrome.rafael.media`
- Account: Rafael's personal Navidrome user, so favorites, history, and
  playlists are the correct user's data
- Music folder: `Music/Managed`
- Playlist folder: `HifiMule-M3U`
- First sync: the complete library, auto-fill disabled
- Auto-sync on connect: disabled until the real card has passed acceptance

The live library measured 40,555,624,828 bytes with 1,119 FLAC/MP3/M4A tracks
on 2026-07-28. It comfortably fits a 256 GB card, so an arbitrary 48 GB
rotation would discard music without solving a present capacity problem.

## Configure EchoList only after HifiMule

With a card named `ECHO` mounted at `/Volumes/ECHO`, use:

```text
Source:       /Volumes/ECHO/Music/Managed
Destination:  /Volumes/ECHO/Music
Folder:       Playlists
Node name:    * PLAYLISTS *
```

This produces `/Volumes/ECHO/Music/Playlists` as a sibling of `Managed`.
Never configure EchoList's destination workspace inside `Managed`, and never
select the server's canonical `/vault/shared/media/music` tree as its
destination.

The repeatable sequence is:

1. Quit EchoList.
2. Let HifiMule finish its delta sync to `Music/Managed`.
3. Start EchoList and synchronize the selected synthetic playlists.
4. If wanted, run the PinePods compiler described below.
5. Check free space and all sync summaries.
6. Eject the card safely.
7. Refresh the ECHO media library and run the acceptance checklist in the
   research record.

EchoList copies tracks for playlist membership. Keep playlist tracks in the
HifiMule selection; otherwise a later HifiMule prune can remove EchoList's
source. EchoList copies are outside HifiMule's managed tree and are therefore
not pruned by HifiMule.

## Add downloaded PinePods episodes

PinePods remains the subscription, download, and progress authority. Its
download tree is already available to the Mac through the authenticated,
read-only `Media` Samba share:

```text
/Volumes/Media/podcasts/pinepods
```

Do not feed this folder into Navidrome or HifiMule. Live inspection found
`.mp3`-named downloads that were actually MP4 video/AAC, plus episodes without
usable tags. The separate compiler extracts audio, stream-copies real MP3,
transcodes other audio to MP3 128 kbps, adds deterministic podcast tags and
bounded filenames, verifies the result, and records only its own card files in
`.pinepods-echo.json`.

The compiler requires `ffmpeg` and `ffprobe`; both are already present in the
Mac's Homebrew FFmpeg installation.

Mount `smb://192.168.0.110/Media`, insert the card, and preview:

```bash
python3 clients/snowsky-echo/sync-pinepods-to-echo.py \
  --device /Volumes/ECHO \
  --dry-run
```

Then apply the same command without `--dry-run`. The default source is
`/Volumes/Media/podcasts/pinepods`, the destination is
`/Volumes/ECHO/Podcasts/PinePods`, and the compiler leaves at least 10% card
space free.

The compiler retains a card episode if PinePods later removes its source.
Use `--prune` only when the card should mirror those removals; it deletes only
outputs recorded in `.pinepods-echo.json`. It never writes the Samba source,
PinePods database, HifiMule tree, or EchoList tree.

The ECHO cannot report listening position back to PinePods. Continue to treat
PinePods/GPodder as the authoritative progress service and use the card as an
offline export. Select what reaches the card by managing downloaded episodes
in PinePods.

On the first card, verify at least one stream-copied MP3 episode and one
converted AAC episode. Confirm that both appear under the synthetic
`* PODCASTS *` grouping, play without video/unsupported-format errors, sort by
their date-prefixed filenames, seek, and resume after a power cycle. Keep
`--prune` off until that acceptance passes.

## Local verification

```bash
python3 -m unittest discover -s clients/snowsky-echo -p 'test_*.py'
sh -n clients/snowsky-echo/download-verified-macos-releases.sh
python3 -m json.tool clients/snowsky-echo/hifimule-profile.json >/dev/null
```

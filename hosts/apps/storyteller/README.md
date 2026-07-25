# Storyteller

Storyteller is a private CT112 project at
`https://storyteller.rafael.media`. It follows the official stable rolling
image `registry.gitlab.com/storyteller-platform/storyteller:latest`; the
phase-4 floor is web 2.14.13 because that release escaped shell metacharacters
in quoted paths. The observed stable release is 2.14.17.

## Data and ownership

The broad CT112 `/data` bind remains read-only. The reconciler alone reads:

- `/data/media/books/ebooks` as `/sources/ebooks`;
- `/data/media/audiobooks` as `/sources/audiobooks`.

The only new LXC write bind is the narrow
`/vault/shared/media/storyteller` to `/storyteller`. Its `inbox` contains
disposable verified copies; Storyteller's move-to-library scanner consumes
only those copies. Its `library` contains Storyteller-owned source copies,
cache/transcription work, covers, and accepted readaloud EPUBs. Storyteller
never references, hard-links, moves, or edits Shelfarr's canonical files.

`/srv/appdata/docker/storyteller` contains the SQLite database, watcher
snapshots, mode-0600 rendered authentication secret, reconciler manifest and
the latest/previous consistent database copies. The encrypted appdata PBS job
covers this appdata. It does not cover the shared inbox/library or either
canonical source tree. The shared Storyteller data is derived but expensive;
do not call it backed up or delete accepted readalouds merely because their
canonical sources still exist.

## Pairing and processing

`reconciler.py` compares the exact two-component Shelfarr relative key. It
accepts one EPUB and one or more current Storyteller audio inputs
(`m4b`, `m4a`, `mp4`, `mp3`, or `zip`), hashes both sides, copies into a
temporary per-book directory, verifies every copy, and atomically publishes
the folder. Multi-file audio is flattened into deterministic names so all
tracks and the EPUB are recognized as one book folder. The durable JSON
manifest records source device/inode/size/mtime/hash, attempts, stage state,
Storyteller state, and last error.

The companion runs every 15 minutes with one pair per pass. Useful commands:

```bash
docker exec storyteller-reconciler python /app/reconciler.py dry-run
docker exec storyteller-reconciler python /app/reconciler.py status
docker exec storyteller-reconciler python /app/reconciler.py report
docker exec storyteller-reconciler python /app/reconciler.py reconcile --max-items 1
```

Incomplete/ambiguous pairs, changed sources, unsafe keys, conflicts, copy
failures, and low space are reported without source mutation. The default
capacity gate retains at least 50 GiB and additionally budgets two pair copies
plus 5 GiB. Upstream recommends about 1 GiB per processed book.

Storyteller has no documented stable non-interactive server queue API. Do not
use its SQLite database or private web routes to enqueue work. In the Books
view choose the `Missing readaloud` format filter, select the desired pairs,
then use `Actions` → `Begin processing` → `Continue where left off`. The Git
configuration keeps one worker, one transcode, one transcription, and Whisper
turbo/threads at 1. The container is limited to 3 CPUs and 8 GiB. Upstream
reports typical CPU processing of 1–4 hours.

WUD calls the reconciler's guard before replacement. A held reconciliation
lock, any pending/importing inbox folder, or SQLite readaloud status `QUEUED`
or `PROCESSING` blocks the update. Reconciler staging is also paused while the
WUD marker exists.

## Backup, cleanup, and rollback

The PVE pre-hook runs `backup-database.sh`. It uses SQLite's online backup API
against a read-only source connection, verifies `PRAGMA integrity_check`, and
keeps latest/previous database plus counts and SHA-256 metadata in appdata.

Storyteller's supported UI may delete processed audio and transcription cache
after a readaloud is accepted. Never delete canonical source, a staged item
still awaiting import, Storyteller-owned source copies, or an accepted
readaloud as cache cleanup. `cleanCacheAfterReadaloud` starts disabled.

For restore, recover `/root/.env` and
`/srv/appdata/docker/storyteller`, restore the shared Storyteller directory
from its separate protection if available, then run bootstrap. If only
appdata and canonical media survived, leave the manifest in place, inspect
changed-source reports, and explicitly authorize restaging/reprocessing;
never erase manifest history or edit Storyteller SQLite to force an import.

Rollback is a Git revert, guest sync, and Compose redeployment. Keep the
current appdata, shared Storyteller tree, old image, and database backups. A
rollback does not authorize deleting media or readalouds.

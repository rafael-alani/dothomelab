#!/usr/bin/env bash
set -Eeuo pipefail

test_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$test_dir/.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf -- "$test_root"' EXIT
mkdir -p "$test_root"/{bin,remote/my-files,remote/trash,sources/photos,state,work,volatile}
ln -s "$test_dir/mock-proton-drive.sh" "$test_root/bin/proton-drive"
printf '#!/bin/sh\nexit 0\n' >"$test_root/bin/sleep"
chmod 0755 "$test_root/bin/sleep"
printf 'real fixture photo contents\n' >"$test_root/sources/photos/photo.jpg"
export PATH="$test_root/bin:$PATH"
export MOCK_PROTON_LOG="$test_root/operations.log"
export MOCK_PROTON_ROOT="$test_root/remote"
export PROTON_BACKUP_CHUNK_SIZE=4K
export PROTON_BACKUP_REMOTE_ROOT=/my-files/Backups/dothomelab
export PROTON_SHARED_WORK_ROOT="$test_root/work"
export PROTON_SOURCE_PHOTOS="$test_root/sources/photos"
export PROTON_STATE_ROOT="$test_root/state"
export PROTON_VOLATILE_WORK_ROOT="$test_root/volatile"
backup="$project_dir/proton-backup.sh"

# The real upload/read-back path must survive one transient download failure.
cycle=20261102T000000Z
"$backup" stage photos "$cycle"
MOCK_PROTON_FAIL_LIST_ONCE=1 MOCK_PROTON_FAIL_ONCE=archive.tar.part-00000 "$backup" upload photos "$cycle"
[[ "$(<"$test_root/state/sources/photos/last-success.cycle")" == "$cycle" ]]
[[ "$(grep -c '^download archive.tar.part-00000$' "$MOCK_PROTON_LOG")" == 2 ]]
echo 'ok - a transient part-download failure retries without losing the generation'

# Two interrupted attempts must keep verified progress and never re-upload a
# complete remote generation merely because its download is unavailable.
cycle=20261103T000000Z
"$backup" stage photos "$cycle"
# A successful empty listing is a confirmed incomplete upload, not a read error.
mkdir "$MOCK_PROTON_ROOT/my-files/Backups/dothomelab/Photos/photos-$cycle"
: >"$MOCK_PROTON_LOG"
for attempt in 1 2; do
  if MOCK_PROTON_FAIL_DOWNLOAD=archive.tar.part-00001 "$backup" upload photos "$cycle"; then
    echo 'Unavailable part incorrectly accepted' >&2; exit 1
  fi
  [[ "$(grep -c '^upload photos-' "$MOCK_PROTON_LOG")" == 1 ]]
  [[ "$(grep -c '^download archive.tar.part-00000$' "$MOCK_PROTON_LOG")" == 1 ]]
  [[ "$(<"$test_root/state/sources/photos/last-success.cycle")" != "$cycle" ]]
  [[ -s "$test_root/work/staging/photos/pending" ]]
done
echo 'ok - interrupted read-back resumes and leaves old success/retention untouched'

# Replacing even an identical remote file changes its revision, invalidating
# that part's cached verification. Its bytes must be downloaded again.
touch -d '2030-01-01 UTC' "$MOCK_PROTON_ROOT/my-files/Backups/dothomelab/Photos/photos-$cycle/archive.tar.part-00000"
"$backup" upload photos "$cycle"
[[ "$(grep -c '^download archive.tar.part-00000$' "$MOCK_PROTON_LOG")" == 2 ]]
[[ "$(grep -c '^upload photos-' "$MOCK_PROTON_LOG")" == 1 ]]
[[ "$(<"$test_root/state/sources/photos/last-success.cycle")" == "$cycle" ]]
[[ -s "$test_root/state/sources/photos/last-success.remote-verification" ]]
echo 'ok - a changed remote revision is reverified before success'

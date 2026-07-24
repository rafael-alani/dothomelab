#!/usr/bin/env bash
set -Eeuo pipefail

test_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$test_dir/.." && pwd)"
test_root="$(mktemp -d)"

cleanup() {
  rm -rf -- "$test_root"
}
trap cleanup EXIT

mkdir -p \
  "$test_root/bin" \
  "$test_root/remote/my-files" \
  "$test_root/remote/trash" \
  "$test_root/sources/obsidian/.stfolder" \
  "$test_root/sources/photos" \
  "$test_root/sources/environment" \
  "$test_root/state" \
  "$test_root/work" \
  "$test_root/volatile"
ln -s "$test_dir/mock-proton-drive.sh" "$test_root/bin/proton-drive"

export PATH="$test_root/bin:$PATH"
export MOCK_PROTON_LOG="$test_root/operations.log"
export MOCK_PROTON_ROOT="$test_root/remote"
export PROTON_BACKUP_CHUNK_SIZE=1K
export PROTON_BACKUP_REMOTE_ROOT=/my-files/Backups/dothomelab
export PROTON_SHARED_WORK_ROOT="$test_root/work"
export PROTON_SOURCE_ENVIRONMENT="$test_root/sources/environment"
export PROTON_SOURCE_OBSIDIAN="$test_root/sources/obsidian"
export PROTON_SOURCE_PHOTOS="$test_root/sources/photos"
export PROTON_STATE_ROOT="$test_root/state"
export PROTON_VOLATILE_WORK_ROOT="$test_root/volatile"

backup="$project_dir/proton-backup.sh"
cycles=(
  20260701T000000Z
  20260715T000000Z
  20260729T000000Z
)

for cycle in "${cycles[@]}"; do
  printf 'obsidian %s\n' "$cycle" >"$test_root/sources/obsidian/note.md"
  printf 'photo %s\n' "$cycle" >"$test_root/sources/photos/photo.jpg"
  printf 'SECRET_%s=value\n' "$cycle" >"$test_root/sources/environment/root.env"
  chmod 0600 "$test_root/sources/environment/root.env"

  "$backup" begin-cycle "$cycle"
  for dataset in obsidian photos environment; do
    "$backup" stage "$dataset" "$cycle"
  done
  for dataset in obsidian photos environment; do
    "$backup" upload "$dataset" "$cycle"
  done
  "$backup" complete-cycle "$cycle"
done

for dataset_dir in Obsidian Photos Environment; do
  retained=("$test_root/remote/my-files/Backups/dothomelab/$dataset_dir"/*)
  [[ ${#retained[@]} -eq 2 ]] || {
    echo "$dataset_dir retained ${#retained[@]} generations, expected two" >&2
    exit 1
  }
done

for dataset in obsidian photos environment; do
  [[ ! -e "$test_root/remote/my-files/Backups/dothomelab/${dataset^}/$dataset-${cycles[0]}" ]] ||
    {
      echo "$dataset oldest generation was not removed" >&2
      exit 1
    }
  [[ -d "$test_root/remote/my-files/Backups/dothomelab/${dataset^}/$dataset-${cycles[2]}" ]] ||
    {
      echo "$dataset newest generation is missing" >&2
      exit 1
    }

  trash_line="$(grep -n "^trash $dataset-${cycles[0]}$" "$MOCK_PROTON_LOG" | cut -d: -f1)"
  upload_line="$(grep -n "^upload $dataset-${cycles[2]}$" "$MOCK_PROTON_LOG" | cut -d: -f1)"
  [[ -n "$trash_line" && -n "$upload_line" && "$trash_line" -lt "$upload_line" ]] ||
    {
      echo "$dataset retention did not delete before the third upload" >&2
      exit 1
    }
done

[[ "$(<"$test_root/state/last-cycle.id")" == "${cycles[2]}" ]]
[[ ! -e "$test_root/state/current-cycle" ]]

"$backup" restore obsidian "obsidian-${cycles[2]}"
[[ -s "$test_root/work/restore/obsidian/obsidian-${cycles[2]}/SHA256SUMS" ]]

status_output="$("$backup" status)"
grep -q "Last complete cycle:" <<<"$status_output"

printf 'ok - three cycles retained exactly two verified generations per dataset\n'

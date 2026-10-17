#!/usr/bin/env bash
set -Eeuo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source <(sed '/^validate_configuration$/,$d' "$project_dir/proton-backup.sh")
old_uid="$(printf '%086d==~%086d==' 0 1)"
new_uid="$(printf '%022d~%022d' 0 1)"
valid_proton_uid "$old_uid"
valid_proton_uid "$new_uid"
for invalid in plain-name '../escape' 'a/b~c' 'a~b' "$old_uid/escape" "$old_uid extra"; do
  if valid_proton_uid "$invalid"; then echo 'unsafe UID accepted' >&2; exit 1; fi
done
name=photos-20260701T000000Z
one="$(jq -cn --arg name "$name" --arg uid "$old_uid" '[{name:{ok:true,value:$name},uid:$uid}]')"
unique_trash_name_matches_uid "$name" "$old_uid" <<<"$one"
if unique_trash_name_matches_uid "$name" "$new_uid" <<<"$one"; then exit 1; fi
duplicate="$(jq --arg uid "$new_uid" '. + [.[0] | .uid=$uid]' <<<"$one")"
if unique_trash_name_matches_uid "$name" "$old_uid" <<<"$duplicate"; then exit 1; fi
printf 'ok - real Proton UID formats accepted; unsafe IDs and ambiguous trash names rejected\n'

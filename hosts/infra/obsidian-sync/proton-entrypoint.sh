#!/usr/bin/env bash
set -euo pipefail

umask 077

state_root=/state
gpg_home="${GNUPGHOME:-$state_root/gnupg}"
password_store="${PASSWORD_STORE_DIR:-$state_root/password-store}"
key_uid="dothomelab Proton Drive CLI <proton-drive@infra.local>"

mkdir -p \
  "$gpg_home" \
  "$password_store" \
  "$state_root/cache" \
  "$state_root/home" \
  "$state_root/latest" \
  "$state_root/restore" \
  "$state_root/staging" \
  "$state_root/verify"
chmod 0700 "$gpg_home" "$password_store" "$state_root/home"

fingerprint="$(
  gpg --batch --with-colons --list-secret-keys 2>/dev/null |
    awk -F: '$1 == "fpr" { print $10; exit }'
)"

if [[ -z "$fingerprint" ]]; then
  gpg --batch --passphrase '' --quick-gen-key "$key_uid" default default never
  fingerprint="$(
    gpg --batch --with-colons --list-secret-keys |
      awk -F: '$1 == "fpr" { print $10; exit }'
  )"
fi

if [[ ! -s "$password_store/.gpg-id" ]] ||
   [[ "$(head -n 1 "$password_store/.gpg-id")" != "$fingerprint" ]]; then
  pass init "$fingerprint" >/dev/null
fi

if [[ "${1:-}" == "backup" ]]; then
  shift
  exec /usr/local/bin/proton-backup "$@"
fi

exec /usr/local/bin/proton-drive "$@"

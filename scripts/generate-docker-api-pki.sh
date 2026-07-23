#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <new-empty-output-directory>" >&2
  exit 2
fi

readonly output_dir="$1"
readonly repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
readonly ext_dir="$repo_root/hosts/common/docker-api"

if [[ -e "$output_dir" ]]; then
  echo "Refusing to overwrite existing path: $output_dir" >&2
  exit 1
fi

umask 077
install -d -m 0700 "$output_dir/apps" "$output_dir/servarr" "$output_dir/client"

openssl genrsa -out "$output_dir/ca-key.pem" 4096
openssl req -x509 -new -sha256 -days 3650 \
  -key "$output_dir/ca-key.pem" \
  -subj "/CN=dothomelab Docker API CA" \
  -out "$output_dir/ca.pem"

issue_certificate() {
  local name="$1"
  local common_name="$2"
  local extension_file="$3"
  local target_dir="$4"

  openssl genrsa -out "$target_dir/key.pem" 4096
  openssl req -new -sha256 \
    -key "$target_dir/key.pem" \
    -subj "/CN=$common_name" \
    -out "$target_dir/request.csr"
  openssl x509 -req -sha256 -days 825 \
    -in "$target_dir/request.csr" \
    -CA "$output_dir/ca.pem" \
    -CAkey "$output_dir/ca-key.pem" \
    -CAserial "$output_dir/ca.srl" \
    -CAcreateserial \
    -extfile "$extension_file" \
    -out "$target_dir/$name-cert.pem"
  rm -f "$target_dir/request.csr"
}

issue_certificate server apps "$ext_dir/apps-server.ext" "$output_dir/apps"
issue_certificate server servarr "$ext_dir/servarr-server.ext" "$output_dir/servarr"
issue_certificate client wud-infra "$ext_dir/wud-client.ext" "$output_dir/client"

chmod 0400 "$output_dir/ca-key.pem" \
  "$output_dir/apps/key.pem" \
  "$output_dir/servarr/key.pem" \
  "$output_dir/client/key.pem"
chmod 0444 "$output_dir/ca.pem" \
  "$output_dir/apps/server-cert.pem" \
  "$output_dir/servarr/server-cert.pem" \
  "$output_dir/client/client-cert.pem"

echo "Generated Docker API CA, two server certificates, and the WUD client certificate."

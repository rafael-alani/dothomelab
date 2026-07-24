#!/usr/bin/env bash

if [[ -z "${DOTHOMELAB_ENV_LOADER_DIR:-}" ]]; then
  DOTHOMELAB_ENV_LOADER_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd
  )"
fi

load_dothomelab_env() {
  local env_file="$1"
  local parser key value
  parser="$DOTHOMELAB_ENV_LOADER_DIR/dotenv.py"

  [[ -r "$env_file" ]] || {
    echo "Missing environment file: $env_file" >&2
    return 1
  }
  command -v python3 >/dev/null || {
    echo "python3 is required to parse $env_file" >&2
    return 1
  }
  python3 "$parser" --check "$env_file" || return 1

  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "$key" '%s' "$value"
    export "$key"
  done < <(python3 "$parser" "$env_file")
}

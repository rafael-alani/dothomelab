#!/usr/bin/env bash
# Call after loading the deployment dotenv, where applicable.
validate_paperless_gpt_flag() {
  case "${PAPERLESS_GPT_ENABLED:-false}" in
    true|false) return 0 ;;
    *) echo 'PAPERLESS_GPT_ENABLED must be true or false' >&2; return 1 ;;
  esac
}

validate_paperless_gpt_policy() {
  validate_paperless_gpt_flag || return 1
  case "${PAPERLESS_GPT_ENABLED:-false}" in
    false) return 0 ;;
    true)
      if [[ -z "${PAPERLESS_GPT_OPENAI_API_KEY:-}" ||
        "${PAPERLESS_GPT_OPENAI_API_KEY}" == replace-with-* ]]; then
        echo 'PAPERLESS_GPT_ENABLED=true requires a real PAPERLESS_GPT_OPENAI_API_KEY' >&2
        return 1
      fi
      ;;
    *) echo 'PAPERLESS_GPT_ENABLED must be true or false' >&2; return 1 ;;
  esac
}

paperless_gpt_enabled() {
  [[ "${PAPERLESS_GPT_ENABLED:-false}" == true ]]
}

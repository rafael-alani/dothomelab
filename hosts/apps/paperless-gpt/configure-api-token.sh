#!/usr/bin/env bash
set -Eeuo pipefail

: "${PAPERLESS_GPT_API_TOKEN:?set PAPERLESS_GPT_API_TOKEN}"
readonly service_user="${PAPERLESS_GPT_SERVICE_USER:-paperless-gpt}"
readonly shared_network="dothomelab-paperless"

[[ "$PAPERLESS_GPT_API_TOKEN" =~ ^[[:xdigit:]]{40}$ ]] || {
  echo "PAPERLESS_GPT_API_TOKEN must contain exactly 40 hexadecimal characters" >&2
  exit 1
}
[[ -z "${PAPERLESS_ADMIN_USER:-}" || "$service_user" != "$PAPERLESS_ADMIN_USER" ]] || {
  echo "PAPERLESS_GPT_SERVICE_USER must differ from PAPERLESS_ADMIN_USER" >&2
  exit 1
}
docker network inspect "$shared_network" >/dev/null 2>&1 || {
  echo "Paperless shared Docker network is missing: $shared_network" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    paperless-ngx
)"
[[ "$state" == "running healthy" ]] || {
  echo "Paperless-ngx must be healthy before configuring its API token; state=$state" >&2
  exit 1
}

docker exec \
  --env "DOTHOMELAB_PAPERLESS_USER=$service_user" \
  --env "DOTHOMELAB_PAPERLESS_TOKEN=$PAPERLESS_GPT_API_TOKEN" \
  paperless-ngx \
  python3 manage.py shell -c '
import os

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

user, _ = get_user_model().objects.get_or_create(
    username=os.environ["DOTHOMELAB_PAPERLESS_USER"],
    defaults={"is_staff": True, "is_superuser": True},
)
changed = []
if not user.is_staff:
    user.is_staff = True
    changed.append("is_staff")
if not user.is_superuser:
    user.is_superuser = True
    changed.append("is_superuser")
if user.has_usable_password():
    user.set_unusable_password()
    changed.append("password")
if changed:
    user.save(update_fields=changed)
key = os.environ["DOTHOMELAB_PAPERLESS_TOKEN"]
if Token.objects.filter(key=key).exclude(user=user).exists():
    raise RuntimeError("the declared token belongs to another Paperless user")
current = Token.objects.filter(user=user).first()
if current is not None and current.key != key:
    current.delete()
Token.objects.get_or_create(key=key, defaults={"user": user})
' >/dev/null

curl --fail --silent --show-error --output /dev/null \
  --header "Authorization: Token $PAPERLESS_GPT_API_TOKEN" \
  "http://192.168.0.112:8002/api/documents/?page_size=1"

if ! docker inspect paperless-gpt >/dev/null 2>&1; then
  echo "Paperless-GPT API token configured; GPT container is not deployed yet."
  exit 0
fi

docker restart paperless-gpt >/dev/null
deadline=$((SECONDS + 180))
while ((SECONDS < deadline)); do
  health="$(
    docker inspect --format \
      '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
      paperless-gpt 2>/dev/null || true
  )"
  [[ "$health" == "healthy" ]] && {
    echo "Paperless-GPT API token configured without exposing its value."
    exit 0
  }
  [[ "$health" == "unhealthy" ]] && break
  sleep 5
done

docker logs --tail 50 paperless-gpt >&2
echo "Paperless-GPT did not become healthy after API-token configuration" >&2
exit 1

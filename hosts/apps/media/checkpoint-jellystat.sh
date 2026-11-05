#!/usr/bin/env bash
# Capture a quiesced Jellystat database and prove restoration on the candidate.
set -Eeuo pipefail
umask 077
[[ $EUID == 0 && "$(findmnt -no SOURCE -T /srv/appdata/docker/jellystat)" == rpool/appdata/docker ]]
image="${POSTGRES_TEST_IMAGE:-postgres:18}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
evidence="/srv/appdata/docker/jellystat/checkpoints/$stamp"
test_container="jellystat_restore_${stamp,,}"
mkdir -p -m 0700 "$evidence"
docker inspect jellystat jellystat-db >"$evidence/runtime-before.json"
docker image inspect "$image" >/dev/null
[[ "$(docker inspect -f '{{.State.Running}}' jellystat)" == true ]]

counts() {
  docker exec -i "$1" psql -XqAt -v ON_ERROR_STOP=on -U jellystat -d jfstat <<'SQL'
SELECT format('SELECT %L || ''='' || count(*)::text FROM %I.%I;',
              schemaname || '.' || tablename, schemaname, tablename)
FROM pg_tables WHERE schemaname='public' ORDER BY tablename
\gexec
SQL
}

restart_app=0
test_started=0
passed=0
cleanup() {
  if ((restart_app)); then docker start jellystat >/dev/null || true; fi
  if ((test_started && !passed)); then
    docker stop "$test_container" >/dev/null 2>&1 || true
    echo "Failed isolated Jellystat test retained: $test_container; $evidence" >&2
  fi
}
trap cleanup EXIT
restart_app=1
docker stop --time 60 jellystat >/dev/null
docker exec jellystat-db pg_dump -Fc -U jellystat -d jfstat >"$evidence/jellystat.dump"
docker exec jellystat-db pg_dumpall --roles-only -U jellystat >"$evidence/roles.sql"
counts jellystat-db >"$evidence/counts.txt"
docker start jellystat >/dev/null
restart_app=0

# The isolated restored data is disposable RAM; the dump and receipts are durable.
docker run -d --name "$test_container" --pull never --network none \
  --label dothomelab.restore-test=jellystat \
  --tmpfs /var/lib/postgresql:rw,size=1g,mode=1777 \
  -e POSTGRES_USER=jellystat -e POSTGRES_DB=jfstat \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_INITDB_ARGS=--data-checksums \
  "$image" >/dev/null
test_started=1
ready=0
for _ in {1..90}; do
  if [[ "$(docker exec "$test_container" psql -XqAt -U jellystat -d jfstat -c 'SELECT 1' 2>/dev/null || true)" == 1 ]]; then
    ready=1; break
  fi
  sleep 1
done
[[ $ready == 1 ]] || { echo 'Isolated Jellystat database did not start' >&2; exit 1; }
docker exec -i "$test_container" pg_restore --exit-on-error --single-transaction \
  -U jellystat -d jfstat <"$evidence/jellystat.dump" \
  >"$evidence/restore.log" 2>&1
counts "$test_container" >"$evidence/restored-counts.txt"
cmp "$evidence/counts.txt" "$evidence/restored-counts.txt"
docker exec "$test_container" postgres --version >"$evidence/candidate-version.txt"
docker inspect -f '{{.Image}}' "$test_container" >"$evidence/candidate-image.txt"
(cd "$evidence"; sha256sum jellystat.dump roles.sql counts.txt restored-counts.txt >SHA256SUMS)
docker stop "$test_container" >/dev/null
docker rm "$test_container" >/dev/null
passed=1
echo "Jellystat logical restore passed; candidate=$(cat "$evidence/candidate-version.txt"); evidence=$evidence"

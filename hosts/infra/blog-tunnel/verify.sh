#!/usr/bin/env bash
# Read-only checks, run inside CT110.
set -Eeuo pipefail
state="$(docker inspect --format '{{.State.Status}} {{.State.Health.Status}}' cloudflare-blog-tunnel)"
[[ "$state" == 'running healthy' ]]
docker exec cloudflare-blog-tunnel cloudflared tunnel --metrics 127.0.0.1:2000 ready
docker inspect cloudflare-ddns | python3 -c '
import json, sys
values = dict(entry.split("=", 1) for entry in json.load(sys.stdin)[0]["Config"]["Env"])
assert "rafael.ink" not in values["DOMAINS"].split(","), "DDNS still owns tunnel hostname"
print("OK DDNS excludes the blog apex")
'
curl --fail --silent --show-error --resolve rafael.ink:443:192.168.0.110 --max-time 15 -o /dev/null https://rafael.ink/
printf 'OK connector readiness and trusted origin HTTPS; verify public ingress separately through public DNS\n'

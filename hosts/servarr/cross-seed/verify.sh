#!/usr/bin/env bash
set -Eeuo pipefail

readonly expected_image="ghcr.io/cross-seed/cross-seed:6"
readonly expected_proxy_image="python:3.13-alpine@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0"
readonly appdata="/docker/cross-seed"
readonly link_dir="/data/torrents/cross-seed-links"
readonly approval="$appdata/indexers-approved"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}} {{.Config.User}}' \
    cross-seed
)" || fail "cross-seed container is missing"
[[ -s "$approval" ]] ||
  fail "cross-seed is pending manual Prowlarr tests and approval"
[[ "$state" == \
  "running healthy cross-seed true docker.backupgated $expected_image 1000:1000" ]] ||
  fail "cross-seed state, image, project, WUD policy, or user drifted: $state"

/opt/dothomelab/hosts/servarr/cross-seed/reconcile-prowlarr-cross-seed-definitions.py \
  --check ||
  fail "Prowlarr cross-seed proxy definitions drifted"

proxy_state="$(
  docker inspect --format \
    '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{.Config.Image}} {{.Config.User}} {{.HostConfig.NetworkMode}} {{.HostConfig.ReadonlyRootfs}} {{.HostConfig.RestartPolicy.Name}}' \
    cross-seed-prowlarr-proxy
)" || fail "cross-seed Prowlarr proxy container is missing"
[[ "$proxy_state" == \
  "running healthy cross-seed false $expected_proxy_image 1000:1000 container:gluetun true unless-stopped" ]] ||
  fail "cross-seed Prowlarr proxy runtime policy drifted: $proxy_state"

docker inspect cross-seed-prowlarr-proxy |
  python3 -c '
import json
import sys

item = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in item["Mounts"]}
expected = {
    "/app/prowlarr-download-proxy.py": (
        "/opt/dothomelab/hosts/servarr/cross-seed/prowlarr-download-proxy.py",
        False,
    ),
    "/prowlarr": ("/docker/prowlarr", False),
}
if set(mounts) != set(expected):
    raise SystemExit(f"unexpected proxy mounts: {sorted(mounts)}")
for destination, (source, writable) in expected.items():
    mount = mounts[destination]
    if mount["Source"] != source or mount["RW"] != writable:
        raise SystemExit(f"proxy mount drifted: {destination}")
if item["HostConfig"]["PortBindings"]:
    raise SystemExit("proxy unexpectedly publishes a host port")
if "no-new-privileges:true" not in item["HostConfig"]["SecurityOpt"]:
    raise SystemExit("proxy no-new-privileges policy drifted")
if item["HostConfig"]["CapDrop"] != ["ALL"]:
    raise SystemExit("proxy capability policy drifted")
if item["HostConfig"]["Tmpfs"] != {"/tmp": "size=16m,mode=1777"}:
    raise SystemExit("proxy tmpfs policy drifted")
' || fail "cross-seed Prowlarr proxy mounts or security policy failed"

docker inspect cross-seed |
  python3 -c '
import json
import sys

item = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in item["Mounts"]}
if set(mounts) != {"/config", "/data"}:
    raise SystemExit(f"unexpected cross-seed mounts: {sorted(mounts)}")
expected = {
    "/config": ("/docker/cross-seed", True),
    "/data": ("/data", True),
}
for destination, (source, writable) in expected.items():
    mount = mounts[destination]
    if mount["Source"] != source or mount["RW"] != writable:
        raise SystemExit(f"cross-seed mount drifted: {destination}")
if "servarr-hello_default" not in item["NetworkSettings"]["Networks"]:
    raise SystemExit("cross-seed is not on the private Servarr network")
if item["HostConfig"]["PortBindings"]:
    raise SystemExit("cross-seed unexpectedly publishes a host port")
if item["HostConfig"]["RestartPolicy"]["Name"] != "unless-stopped":
    raise SystemExit("cross-seed restart policy is not approved")
if "no-new-privileges:true" not in item["HostConfig"]["SecurityOpt"]:
    raise SystemExit("cross-seed no-new-privileges policy drifted")
if item["HostConfig"]["CapDrop"] != ["ALL"]:
    raise SystemExit("cross-seed capability policy drifted")
' || fail "cross-seed mount, network, or runtime security policy failed"

[[ "$(findmnt -n -o SOURCE -T "$appdata")" == "rpool/appdata/docker" ]] ||
  fail "cross-seed appdata is not canonical"
[[ "$(stat -c '%u:%g %a' "$appdata")" == "1000:1000 750" ]] ||
  fail "cross-seed appdata ownership or mode drifted"
[[ -s "$appdata/config.js" ]] || fail "cross-seed config.js is missing"
[[ "$(stat -c '%u:%g %a' "$appdata/config.js")" == "1000:1000 600" ]] ||
  fail "cross-seed config.js ownership or mode drifted"
[[ "$(stat -c '%u:%g %a' "$approval")" == "1000:1000 600" ]] ||
  fail "cross-seed approval marker ownership or mode drifted"

[[ "$(findmnt -n -o SOURCE -T "$link_dir")" == "vault/shared" ]] ||
  fail "cross-seed links are not on canonical shared storage"
[[ "$(stat -c '%u:%g %a' "$link_dir")" == "1000:1000 750" ]] ||
  fail "cross-seed link directory ownership or mode drifted"
[[ "$(stat -c %d /data/torrents)" == "$(stat -c %d "$link_dir")" ]] ||
  fail "cross-seed cannot hardlink within the torrent data filesystem"

docker exec cross-seed node -e '
const c=require("/config/config.js");
const assert=require("node:assert/strict");
assert.equal(c.matchMode,"strict");
assert.equal(c.action,"inject");
assert.equal(c.linkType,"hardlink");
assert.deepEqual(c.linkDirs,["/data/torrents/cross-seed-links"]);
assert.deepEqual(c.torrentClients,["qbittorrent:http://gluetun:8080"]);
assert.equal(c.useClientTorrents,true);
assert.equal(c.skipRecheck,false);
assert.equal(c.autoResumeMaxDownload,0);
assert.equal(c.ignoreNonRelevantFilesToResume,false);
assert.equal(c.seasonFromEpisodes,null);
assert.equal(c.delay,60);
assert.equal(c.searchLimit,50);
assert.equal(c.torznab.length,3);
const expectedPorts=["9697","9697","9696"];
for (const [index,endpoint] of c.torznab.entries()) {
  const url=new URL(endpoint);
  assert.equal(url.hostname,"gluetun");
  assert.equal(url.port,expectedPorts[index]);
  assert.match(url.pathname,/^\/[0-9]+\/api$/);
  assert.ok(url.searchParams.get("apikey"));
}
' || fail "cross-seed strict runtime configuration failed"

docker exec cross-seed node -e '
fetch("http://gluetun:9697/health")
  .then((response)=>{if(!response.ok) throw new Error("HTTP "+response.status)})
  .catch(()=>process.exit(1));
' || fail "cross-seed cannot reach the Prowlarr download proxy"

docker exec cross-seed node -e '
fetch("http://gluetun:8080/api/v2/app/version")
  .then((response)=>{if(!response.ok) throw new Error("HTTP "+response.status)})
  .catch(()=>process.exit(1));
' || fail "cross-seed cannot reach qBittorrent through the private network"

version="$(docker run --rm "$expected_image" --version 2>/dev/null | tail -n 1)" ||
  fail "cross-seed version command failed"
[[ "$version" == 6.* ]] || fail "cross-seed runtime is not v6: $version"

printf 'cross-seed verification passed: v%s, private API, two notice-aware proxied indexers plus direct HDClone, strict hardlink injection, forced rechecks, zero-byte auto-resume, and backup-gated updates.\n' \
  "$version"

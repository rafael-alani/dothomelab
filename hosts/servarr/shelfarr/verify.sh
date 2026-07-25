#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  echo "FAIL $*" >&2
  exit 1
}

[[ "$(curl --silent --output /dev/null --write-out '%{http_code}' http://192.168.0.102:5056/up)" == "200" ]] ||
  fail "Shelfarr /up is not healthy"

for container in shelfarr shelfarr-libation; do
  [[ "$(docker inspect --format '{{.State.Health.Status}}' "$container")" == "healthy" ]] ||
    fail "$container is not healthy"
  [[ "$(docker inspect --format '{{index .Config.Labels "wud.watch"}}' "$container")" == "true" ]] ||
    fail "$container is not enrolled in WUD"
done

subnet="$(
  docker network inspect servarr-hello_default \
    --format '{{(index .IPAM.Config 0).Subnet}}'
)"
grep -Fqx "WebUI\\AuthSubnetWhitelist=$subnet" \
  /docker/qbittorrent/qBittorrent/qBittorrent.conf ||
  fail "qBittorrent internal authentication subnet drifted"
grep -Fqx 'WebUI\AuthSubnetWhitelistEnabled=true' \
  /docker/qbittorrent/qBittorrent/qBittorrent.conf ||
  fail "qBittorrent internal subnet authentication bypass is disabled"

docker inspect shelfarr |
  python3 -c '
import json
import sys
mounts = {item["Destination"]: item for item in json.load(sys.stdin)[0]["Mounts"]}
expected = {
    "/rails/storage": False,
    "/ebooks": False,
    "/audiobooks": False,
    "/data/torrents": False,
    "/downloads": False,
    "/imports/libation": True,
    "/run/shelfarr-libation": True,
}
for destination, read_only in expected.items():
    mount = mounts.get(destination)
    if not mount or not mount["Source"].startswith(("/docker/", "/data/")):
        raise SystemExit(f"missing deterministic mount {destination}")
    if (not mount["RW"]) != read_only:
        raise SystemExit(f"mount mode drift for {destination}")
'

docker exec --interactive shelfarr \
  sh -lc '. /rails/storage/.encryption_keys; exec bin/rails runner -' <<'RUBY'
expected = {
  indexer_provider: "prowlarr",
  prowlarr_url: "http://gluetun:9696",
  anna_archive_enabled: false,
  zlibrary_enabled: false,
  librivox_enabled: false,
  gutenberg_enabled: false,
  ebooks_com_enabled: false,
  library_platform: "bookorbit",
  bookorbit_url: "http://192.168.0.112:3002",
  ebook_output_path: "/ebooks",
  ebook_path_template: "{author}/{title}",
  audiobook_path_template: "{author}/{title}",
  completed_download_import_mode: "copy"
}
expected.each do |key, value|
  actual = SettingsService.get(key)
  raise "#{key} drifted" unless actual == value
end
raise "unexpected enabled acquisition client" unless DownloadClient.enabled.count == 2
raise "Libation beta became active" if OwnedLibraryConnection.for_provider("libation").enabled.exists?
raise "BookOrbit ebook library is unset" if SettingsService.get(:audiobookshelf_ebook_library_id).blank?
raise "Prowlarr connection failed" unless ProwlarrClient.test_connection
DownloadClient.enabled.find_each do |client|
  raise "#{client.name} connection failed" unless client.test_connection
end
raise "BookOrbit connection failed" unless BookOrbitClient.test_connection
puts "Shelfarr settings preserve the organizer, source, and inactive-Libation contracts"
RUBY

echo "Shelfarr verification passed"

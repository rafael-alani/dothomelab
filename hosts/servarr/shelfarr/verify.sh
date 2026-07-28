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
grep -Fqx 'WebUI\LocalHostAuth=true' \
  /docker/qbittorrent/qBittorrent/qBittorrent.conf ||
  fail "qBittorrent localhost authentication is disabled"

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

[[ "$(findmnt -n -o SOURCE -T /data/media/audiobooks)" == vault/shared* ]] ||
  fail "Shelfarr audiobook library is not on vault/shared"

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
  library_platform: "audiobookshelf",
  audiobookshelf_url: "http://192.168.0.112:13378",
  ebook_output_path: "/ebooks",
  audiobook_output_path: "/audiobooks",
  ebook_path_template: "{author}/{title}",
  audiobook_path_template: "{author}/{title}",
  ebook_filename_template: "{author} - {title}",
  audiobook_filename_template: "{author} - {title}",
  split_audiobook_bundle_imports: false,
  remove_completed_usenet_downloads: true,
  audiobook_approved_formats: [],
  audiobook_rejected_formats: [],
  audiobook_preferred_formats: %w[m4b m4a mp3 flac],
  audiobook_prefer_single_file: true,
  audiobook_prefer_higher_bitrate: false,
  download_remote_path: "",
  download_local_path: "/downloads",
  completed_download_import_mode: "copy"
}
expected.each do |key, value|
  actual = SettingsService.get(key)
  raise "#{key} drifted" unless actual == value
end
raise "unexpected enabled acquisition client" unless DownloadClient.enabled.count == 2
raise "Libation beta became active" if OwnedLibraryConnection.for_provider("libation").enabled.exists?
raise "Audiobookshelf API key is unset" if SettingsService.get(:audiobookshelf_api_key).blank?
raise "Audiobookshelf audiobook library is unset" if SettingsService.get(:audiobookshelf_audiobook_library_id).blank?
%i[
  audiobookshelf_audiobook_scan_library_ids
  audiobookshelf_ebook_library_id
  audiobookshelf_ebook_scan_library_ids
  audiobookshelf_comicbook_library_id
  audiobookshelf_comicbook_scan_library_ids
].each do |key|
  raise "#{key} must remain empty" if SettingsService.get(key).present?
end
qbittorrent = DownloadClient.enabled.find_by(name: "Existing qBittorrent")
nzbget = DownloadClient.enabled.find_by(name: "Existing NZBGet")
raise "qBittorrent remote path drifted" unless qbittorrent&.download_path == "/data/torrents"
raise "NZBGet remote path drifted" unless nzbget&.download_path == "/downloads/completed"
raise "non-admin uploads became active" if SettingsService.get(:allow_user_uploads)
raise "Prowlarr connection failed" unless ProwlarrClient.test_connection
DownloadClient.enabled.find_each do |client|
  raise "#{client.name} connection failed" unless client.test_connection
end
libraries = AudiobookshelfClient.libraries
raise "scoped Audiobookshelf key exposed another library" unless libraries.one?
library = libraries.first
raise "Audiobookshelf audiobook library path drifted" unless library.folder_paths == ["/audiobooks"]
raise "Audiobookshelf audiobook library ID drifted" unless \
  SettingsService.get(:audiobookshelf_audiobook_library_id) == library.id.to_s
raise "Audiobookshelf connection failed" unless AudiobookshelfClient.test_connection
sync = AudiobookshelfLibrarySyncService.new.sync!
raise "Audiobookshelf inventory sync failed: #{sync.errors.join('; ')}" unless sync.success?
puts "Shelfarr settings preserve the shared book key, organizer, seeding, scoped Audiobookshelf, and inactive-Libation contracts"
RUBY

echo "Shelfarr verification passed"

#!/usr/bin/env bash
set -Eeuo pipefail

: "${DOTHOMELAB_ENV:=/run/dothomelab.env}"
readonly shelfarr_env_file="$DOTHOMELAB_ENV"
readonly prowlarr_config="/docker/prowlarr/config.xml"

# shellcheck disable=SC1091
source /opt/dothomelab/hosts/common/load-env.sh
load_dothomelab_env "$shelfarr_env_file"

required=(
  AUDIOBOOKSHELF_SHELFARR_API_KEY
  BOOKORBIT_ADMIN_PASSWORD
  NZBGET_PASS
  NZBGET_USER
  SHELFARR_ADMIN_PASSWORD
  SHELFARR_API_TOKEN
)
for variable in "${required[@]}"; do
  [[ -n "${!variable:-}" ]] || {
    echo "$variable is missing from $shelfarr_env_file" >&2
    exit 1
  }
done

[[ -s "$prowlarr_config" ]] || {
  echo "Prowlarr configuration is missing" >&2
  exit 1
}
prowlarr_api_key="$(
  python3 - "$prowlarr_config" <<'PY'
import sys
import xml.etree.ElementTree as ElementTree

value = ElementTree.parse(sys.argv[1]).getroot().findtext("ApiKey", "")
print(value)
PY
)"
[[ -n "$prowlarr_api_key" ]] || {
  echo "Prowlarr API key was not found" >&2
  exit 1
}

docker exec --interactive \
  --env "DHL_ADMIN_PASSWORD=$SHELFARR_ADMIN_PASSWORD" \
  --env "DHL_API_TOKEN=$SHELFARR_API_TOKEN" \
  --env "DHL_AUDIOBOOKSHELF_API_KEY=$AUDIOBOOKSHELF_SHELFARR_API_KEY" \
  --env "DHL_BOOKORBIT_PASSWORD=$BOOKORBIT_ADMIN_PASSWORD" \
  --env "DHL_PROWLARR_API_KEY=$prowlarr_api_key" \
  --env "DHL_NZBGET_USER=$NZBGET_USER" \
  --env "DHL_NZBGET_PASSWORD=$NZBGET_PASS" \
  shelfarr sh -lc '. /rails/storage/.encryption_keys; exec bin/rails runner -' <<'RUBY'
user = User.find_or_initialize_by(username: "rafael")
user.name = "Rafael"
user.role = "admin"
user.password = ENV.fetch("DHL_ADMIN_PASSWORD")
user.password_confirmation = ENV.fetch("DHL_ADMIN_PASSWORD")
user.save!

settings = {
  indexer_provider: "prowlarr",
  prowlarr_url: "http://gluetun:9696",
  prowlarr_api_key: ENV.fetch("DHL_PROWLARR_API_KEY"),
  anna_archive_enabled: false,
  zlibrary_enabled: false,
  librivox_enabled: false,
  gutenberg_enabled: false,
  ebooks_com_enabled: false,
  immediate_search_enabled: false,
  auto_approve_requests: false,
  completed_download_import_mode: "copy",
  split_audiobook_bundle_imports: false,
  remove_completed_usenet_downloads: true,
  library_platform: "audiobookshelf",
  audiobookshelf_url: "http://192.168.0.112:13378",
  audiobookshelf_api_key: ENV.fetch("DHL_AUDIOBOOKSHELF_API_KEY"),
  bookorbit_url: "http://192.168.0.112:3002",
  bookorbit_username: "rafael",
  bookorbit_password: ENV.fetch("DHL_BOOKORBIT_PASSWORD"),
  ebook_output_path: "/ebooks",
  audiobook_output_path: "/audiobooks",
  ebook_path_template: "{author}/{title}",
  audiobook_path_template: "{author}/{title}",
  ebook_filename_template: "{author} - {title}",
  audiobook_filename_template: "{author} - {title}",
  audiobook_approved_formats: [],
  audiobook_rejected_formats: [],
  audiobook_preferred_formats: %w[m4b m4a mp3 flac],
  audiobook_prefer_single_file: true,
  audiobook_prefer_higher_bitrate: false,
  download_remote_path: "",
  download_local_path: "/downloads",
  api_token: ENV.fetch("DHL_API_TOKEN"),
  allow_user_uploads: false,
  auth_disabled: false
}
settings.each { |key, value| SettingsService.set(key, value) }

clients = [
  {
    name: "Existing qBittorrent",
    client_type: "qbittorrent",
    url: "http://gluetun:8080",
    username: "",
    password: "",
    category: "shelfarr",
    download_path: "/data/torrents",
    priority: 0
  },
  {
    name: "Existing NZBGet",
    client_type: "nzbget",
    url: "http://gluetun:6789",
    username: ENV.fetch("DHL_NZBGET_USER"),
    password: ENV.fetch("DHL_NZBGET_PASSWORD"),
    category: "Books",
    download_path: "/downloads/completed",
    priority: 0
  }
]
clients.each do |attributes|
  client = DownloadClient.find_or_initialize_by(name: attributes.fetch(:name))
  client.assign_attributes(attributes.merge(enabled: true))
  client.save!
end

OwnedLibraryConnection.for_provider("libation").update_all(
  enabled: false,
  scheduled_sync_enabled: false,
  automatic_backup_enabled: false,
  bridge_token: nil,
  auth_session_id: nil,
  auth_login_url: nil
)

libraries = AudiobookshelfClient.libraries
audiobook_libraries = libraries.select do |library|
  library.audiobook_library? && library.folder_paths.include?("/audiobooks")
end
raise "Audiobookshelf /audiobooks library is unavailable or ambiguous" unless audiobook_libraries.one?
audiobooks = audiobook_libraries.first
SettingsService.set(:audiobookshelf_audiobook_library_id, audiobooks.id.to_s)
SettingsService.set(:audiobookshelf_audiobook_scan_library_ids, "")
SettingsService.set(:audiobookshelf_ebook_library_id, "")
SettingsService.set(:audiobookshelf_ebook_scan_library_ids, "")
SettingsService.set(:audiobookshelf_comicbook_library_id, "")
SettingsService.set(:audiobookshelf_comicbook_scan_library_ids, "")

raise "Prowlarr connection failed" unless ProwlarrClient.test_connection
DownloadClient.enabled.find_each do |client|
  raise "#{client.name} connection failed" unless client.test_connection
end
raise "Audiobookshelf connection failed" unless AudiobookshelfClient.test_connection
sync = AudiobookshelfLibrarySyncService.new.sync!
raise "Audiobookshelf inventory sync failed: #{sync.errors.join('; ')}" unless sync.success?

puts "Shelfarr ebook organizer, read-only audiobook inventory, existing acquisition clients, shared book key, and Audiobookshelf scan integration reconciled"
RUBY

#!/bin/bash
set -euo pipefail
[[ $(uname -s) == Darwin ]] || { echo 'This client is macOS-only.' >&2; exit 1; }
[[ $EUID -ne 0 ]] || { echo 'Run as the logged-in desktop user, not root.' >&2; exit 1; }
client_dir=$(cd -- "$(dirname -- "$0")" && pwd)
support="$HOME/Library/Application Support/dothomelab-media"
agent="$HOME/Library/LaunchAgents/media.rafael.homelab-media.plist"
fish_function="$HOME/.config/fish/functions/kew.fish"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$support" "$(dirname "$agent")" "$(dirname "$fish_function")"
for target in "$support/media-reconnect" "$agent" "$fish_function"; do
    [[ ! -L "$target" ]] || { echo "Refusing symlink: $target" >&2; exit 1; }
    if [[ -f "$target" ]]; then cp -p "$target" "$target.before-$stamp"; fi
done
xcrun clang -Wall -Wextra -Werror -fobjc-arc -framework Foundation -framework NetFS \
    "$client_dir/media-reconnect.m" -o "$support/media-reconnect.new"
chmod 755 "$support/media-reconnect.new"
mv "$support/media-reconnect.new" "$support/media-reconnect"
cp "$client_dir/kew.fish" "$fish_function"
# PlistBuddy handles spaces and XML quoting without template substitution.
plist_tmp=$(mktemp "$support/agent.XXXXXX")
cat > "$plist_tmp" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict/></plist>
PLIST
/usr/libexec/PlistBuddy -c 'Clear dict' \
    -c 'Add :Label string media.rafael.homelab-media' \
    -c 'Add :ProgramArguments array' \
    -c "Add :ProgramArguments:0 string $support/media-reconnect" \
    -c 'Add :RunAtLoad bool true' \
    -c 'Add :StartInterval integer 30' \
    -c 'Add :LimitLoadToSessionType string Aqua' \
    -c 'Add :ProcessType string Background' \
    "$plist_tmp" >/dev/null
plutil -lint "$plist_tmp"
launchctl bootout "gui/$UID/media.rafael.homelab-media" 2>/dev/null || true
mv "$plist_tmp" "$agent"
chmod 644 "$agent"
launchctl enable "gui/$UID/media.rafael.homelab-media"
launchctl bootstrap "gui/$UID" "$agent"
echo 'Installed Media reconnect agent (login + every 30 seconds) and Fish Kew guard.'

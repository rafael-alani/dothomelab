#!/bin/sh
set -eu

# Upstream v1.0.40 hard-codes one URL for both the QR code and photo link.
# Reapply to each fresh image; never modify the persisted account settings.
webroot="${1:-/app/wwwroot}"
bundles="$(find "$webroot" -type f -name '*.js' -exec grep -lF \
    'https://my.immich.app/photos/' {} \;)"
if [ -n "$bundles" ]; then
    printf '%s\n' "$bundles" | while IFS= read -r bundle; do
        sed 's|https://my\.immich\.app/photos/|https://pictures.rafael.ink/photos/|g' \
            "$bundle" > "$bundle.tmp"
        cat "$bundle.tmp" > "$bundle"
        rm "$bundle.tmp"
        # ASP.NET can serve precompressed siblings instead of the patched JS.
        gzip -c "$bundle" > "$bundle.gz"
        rm -f "$bundle.br"
    done
fi

# Fail visibly if an upstream layout change invalidates this workaround.
if ! find "$webroot" -type f -name '*.js' -exec grep -lF \
    'https://pictures.rafael.ink/photos/' {} \; | grep -q .; then
    echo 'ImmichFrame photo-link patch needs review: link builder not found' >&2
    exit 1
fi

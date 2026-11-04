#!/usr/bin/env bash
set -Eeuo pipefail
[[ $(findmnt -n -o SOURCE -T /srv/appdata/docker) == rpool/appdata/docker ]]
[[ -d /srv/appdata/docker/speech/models && ! -L /srv/appdata/docker/speech/models ]]
[[ $(stat -c %u /srv/appdata/docker/speech/models) == 1000 ]]
[[ -s /srv/appdata/docker/speech/runtime.env ]]

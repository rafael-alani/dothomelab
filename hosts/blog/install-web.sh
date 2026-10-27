#!/usr/bin/env bash
# CT114/115: install native build/serve tools; cutover starts the server separately.
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
environment="$(hostname -s)"
[[ "$environment" == staging || "$environment" == production ]] || exit 1
bash "$here/install-node.sh"
packages=(rsync git ca-certificates)
new_nginx=false
if [[ ! -x /usr/sbin/nginx ]]; then
  packages+=(nginx-light)
  new_nginx=true
fi
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${packages[@]}"
# Only a newly installed default server is disabled; existing native sites stay up.
if "$new_nginx"; then systemctl disable --now nginx.service; fi
root="/srv/appdata/docker/$environment/blog"
install -d -m 0755 /var/lib/dothomelab-blog/site /etc/dothomelab
python3 - "$here" "$environment" <<'PY'
import json,sys
from pathlib import Path
here=Path(sys.argv[1]); environment=sys.argv[2]
config=json.loads((here/'environments.json').read_text())[environment]
root=Path('/srv/appdata/docker')/environment/'blog'
text=(here/'nginx.conf').read_text().replace('ADDRESS',config['address']).replace('SITE_ROOT','/var/lib/dothomelab-blog/site').replace('ROBOTS_VALUE',config['robots'])
# Preserve the separately supplied private audio; it is never a production input.
listening=''
if environment=='staging':
    sources=sorted((root/'listening').glob('*/track.json'))
    if sources:
        import subprocess
        target=Path('/var/lib/dothomelab-blog/listening')
        target.mkdir(exist_ok=True)
        subprocess.run(['rsync','-a','--chmod=D755,F644',str(sources[-1].parent)+'/',str(target)+'/'],check=True)
        listening='location /listening/ { alias '+str(target)+'/; }'
text=text.replace('LISTENING_LOCATION',listening)
Path('/etc/dothomelab/blog-nginx.conf').write_text(text)
PY
install -m 0644 "$here/dothomelab-blog-web.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable dothomelab-blog-web.service

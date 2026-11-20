#!/usr/bin/env python3
"""PVE: create the separate Codex VM from a verified Debian image; never replace a VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

VMID = '116'
IP = '192.168.0.116'
DATA = Path('/srv/appdata/docker/codex-dev')
IMAGE_VERSION = '20261116-2664'
IMAGE_SHA512 = 'e53a93ef33f828ceed0e7278c2cc2753bdc7d5098fbfae15bd64b6d878db350ea3744247763a1c8ecb6b4019a0f623c38caf6038ad6f9c357fb4e01493ddf1a3'
IMAGE_URL = f'https://cloud.debian.org/images/cloud/trixie/{IMAGE_VERSION}/debian-13-generic-amd64-{IMAGE_VERSION}.qcow2'


def run(*args, capture=False):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE if capture else None).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-key', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if os.geteuid() or not Path('/etc/pve').is_dir():
        parser.error('Run on PVE as root')
    key = args.public_key.read_text().strip()
    if not key.startswith(('ssh-ed25519 ', 'ssh-rsa ')) or '\n' in key:
        parser.error('Expected one SSH public key')
    config = Path(f'/etc/pve/qemu-server/{VMID}.conf')
    if config.exists():
        if 'name: codex-dev' not in config.read_text():
            raise RuntimeError('VM116 already belongs to another workload')
        print('Codex VM already exists; left unchanged. Use the runbook to verify or repair it.')
        return
    if Path(f'/etc/pve/lxc/{VMID}.conf').exists():
        raise RuntimeError('Guest116 already exists as an LXC')
    if subprocess.run(['ping', '-c', '1', '-W', '1', IP], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        raise RuntimeError('Proposed IP already responds; choose another address')
    available = int(run('zfs', 'get', '-Hp', '-o', 'value', 'available', 'rpool', capture=True))
    if available < 90 * 1024**3:
        raise RuntimeError('Require 90 GiB pool headroom before adding this 24 GiB thin VM')
    print('Plan: new Debian13 VM116, 4 CPUs, 8 GiB RAM, 24 GiB thin root, private .116; narrow virtiofs workspaces')
    if args.dry_run:
        return
    DATA.mkdir(mode=0o750, exist_ok=True)
    (DATA / 'authorized.pub').write_text(key + '\n')
    workspace = DATA / 'workspace'
    workspace.mkdir(mode=0o700, exist_ok=True)
    if workspace.is_symlink():
        raise RuntimeError('Workspace must not be a symlink')
    os.chown(workspace, 1000, 1000)
    cache = Path('/var/lib/vz/template/cache')
    cache.mkdir(exist_ok=True)
    image = cache / f'debian13-codex-{IMAGE_VERSION}.qcow2'
    if not image.exists():
        urllib.request.urlretrieve(IMAGE_URL, image)
    with image.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha512').hexdigest()
    if digest != IMAGE_SHA512:
        raise RuntimeError('Debian image checksum mismatch; image retained for inspection')
    mapping = json.loads(run('pvesh', 'get', '/cluster/mapping/dir', '--output-format', 'json', capture=True))
    if any(item['id'] == 'codex-workspace' for item in mapping):
        raise RuntimeError('Directory mapping already exists without VM; inspect before adopting')
    run('pvesh', 'create', '/cluster/mapping/dir', '--id', 'codex-workspace', '--map', f'node=afa,path={workspace}')
    snippets = Path('/var/lib/vz/snippets')
    snippets.mkdir(exist_ok=True)
    snippet = snippets / 'codex-dev-user.yaml'
    node_installer = (Path(__file__).resolve().parents[1] / 'staging/branchline/install-node.sh').read_text()
    setup = '''#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p /workspace
mountpoint -q /workspace || mount -t virtiofs codex-workspace /workspace
grep -q '^codex-workspace ' /etc/fstab || echo 'codex-workspace /workspace virtiofs defaults 0 0' >> /etc/fstab
install -d -o codex -g codex -m 0700 /workspace/repos /workspace/codex-state /workspace/config
grep -q '/workspace/config/shell.env' /home/codex/.profile || echo '[ ! -f /workspace/config/shell.env ] || . /workspace/config/shell.env' >> /home/codex/.profile
if [[ ! -e /home/codex/.codex ]]; then ln -s /workspace/codex-state /home/codex/.codex; fi
bash /usr/local/sbin/install-branchline-node
npm install -g --prefix /opt/codex-0.171.0 @openai/codex@0.171.0
ln -sfn /opt/codex-0.171.0/bin/codex /usr/local/bin/codex
runuser -u codex -- python3 /usr/local/share/codex-dev/browser/install.py
systemctl enable --now qemu-guest-agent
'''
    cloud = {
        'hostname': 'codex-dev', 'manage_etc_hosts': True, 'ssh_pwauth': False,
        'disable_root': True,
        'users': [{'name': 'codex', 'uid': 1000, 'shell': '/bin/bash', 'lock_passwd': True,
                   'ssh_authorized_keys': [key]}],
        'package_update': True,
        'packages': ['qemu-guest-agent', 'git', 'curl', 'ca-certificates', 'python3', 'python3-venv',
                     'tmux', 'unzip', 'xz-utils', 'openjdk-21-jdk-headless', 'chromium', 'bubblewrap'],
        'write_files': [
            {'path': '/usr/local/sbin/install-branchline-node', 'permissions': '0755', 'content': node_installer},
            {'path': '/usr/local/sbin/codex-dev-setup', 'permissions': '0755', 'content': setup}],
        'runcmd': [['bash', '/usr/local/sbin/codex-dev-setup']],
    }
    for name in ('install.py', 'package.json', 'package-lock.json', 'browser.md'):
        cloud['write_files'].append({
            'path': f'/usr/local/share/codex-dev/browser/{name}', 'permissions': '0644',
            'content': (Path(__file__).resolve().parent / 'browser' / name).read_text(),
        })
    snippet.write_text('#cloud-config\n' + json.dumps(cloud, indent=2) + '\n')
    snippet.chmod(0o600)
    run('qm', 'create', VMID, '--name', 'codex-dev', '--memory', '8192', '--cores', '4', '--cpu', 'host',
        '--net0', 'virtio=02:7A:8C:00:01:16,bridge=vmbr0,firewall=1', '--scsihw', 'virtio-scsi-single',
        '--serial0', 'socket', '--vga', 'serial0', '--agent', 'enabled=1', '--onboot', '1', '--startup', 'order=70')
    run('qm', 'set', VMID, '--scsi0', f'local-zfs:0,import-from={image},discard=on,ssd=1')
    run('qm', 'resize', VMID, 'scsi0', '24G')
    run('qm', 'set', VMID, '--ide2', 'local-zfs:cloudinit', '--boot', 'order=scsi0',
        '--ipconfig0', f'ip={IP}/24,gw=192.168.0.1', '--nameserver', '192.168.0.100',
        '--cicustom', 'user=local:snippets/codex-dev-user.yaml', '--virtiofs0', 'dirid=codex-workspace,cache=auto')
    run('qm', 'start', VMID)
    print('Created VM116. Verify cloud-init, pin its SSH host key through the guest agent, then authenticate Codex.')


if __name__ == '__main__':
    main()

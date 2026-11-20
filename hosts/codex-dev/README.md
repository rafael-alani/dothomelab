# Codex SSH development VM

VM116 `codex-dev` is a separate Debian 13 development machine at
`192.168.0.116`: four virtual CPUs, 8 GiB RAM and a 24 GiB thin root disk. VM101
is untouched and remains outside this workflow. No Symphony service is needed.
Branchline and Docker previews run on [CT114](../staging/branchline/README.md);
this VM edits source and sends Git bundles over authenticated HTTPS.

## Provision and verify

On PVE, inspect available storage/RAM and confirm that guest ID 116 and `.116`
are free. Supply one authorized SSH **public** key to the explicit provisioner:

```bash
python3 hosts/codex-dev/provision.py --public-key /absolute/path/to/operator.pub --dry-run
python3 hosts/codex-dev/provision.py --public-key /absolute/path/to/operator.pub
qm config 116
qm guest exec 116 -- cloud-init status --long
qm guest exec 116 -- findmnt /workspace
qm guest exec 116 -- ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

The provisioner requires 90 GiB pool headroom, verifies the pinned Debian cloud
image `20261116-2664` by SHA-512, creates the narrow directory mapping and starts
the VM. It refuses another workload's guest ID and leaves an existing
`codex-dev` VM unchanged; rerunning is not a repair or replacement operation.
This is separate from the full homelab bootstrap and HAOS VMA restore contract.

Cloud-init installs Git, Python, tmux, Java 21, Chromium, the QEMU guest agent,
Node `24.22.3` and Codex CLI `0.143.0` through `/usr/local/bin/codex`.
The cloud image, package/npm registries
and Node distribution are external rebuild inputs. Review cloud-init completion
before using the machine. Confirm the VM's SSH host fingerprint through the
PVE guest agent before accepting it on the client; never disable host-key checks.
Configure a client alias using the authorized key:

```sshconfig
Host codex-dev
    HostName 192.168.0.116
    User codex
    IdentityFile ~/.ssh/homelab
    IdentitiesOnly yes
```

Change `IdentityFile` to the matching local key. Password/root SSH login is
disabled. `ssh codex-dev` enters the development account; use PVE and `pct exec`
for LXC administration. The VM has no staging Docker socket, PVE private key or
production environment. Codex authentication is a user step: run `codex`, follow
its sign-in flow, and verify account access before assigning an agent task.
Installation/version checks alone do not establish authenticated Codex operation.

## Durable workspace

PVE `/srv/appdata/docker/codex-dev/workspace` is exposed through the
`codex-workspace` virtiofs mapping at `/workspace`. It belongs to UID/GID 1000
on the host and VM; this is a direct VM mapping, not the unprivileged LXC offset.
Inspect `findmnt`, `stat`, `namei` and consumers before permission changes.

| VM path | Use |
|---|---|
| `/workspace/repos` | Branchline checkouts and other source work |
| `/workspace/codex-state` | Persistent Codex state, linked from `/home/codex/.codex` |
| `/workspace/bin/branchline` | CLI copied from the accepted CT114 Branchline commit |
| `/workspace/config` | Private client configuration and scoped token file |

Keep work in these paths. The guest home, installed packages and root disk are
replaceable; sessions/processes are not durable recovery state. Codex account
material is sensitive and stays outside Git and logs.

## Connect to Branchline

After the paired Branchline release is accepted, run on PVE:

```bash
python3 hosts/codex-dev/configure-client.py --dry-run
python3 hosts/codex-dev/configure-client.py
```

This verifies VM116's identity, compares the accepted web commit with CT114's
source checkout, and extracts the CLI directly from that Git commit. It installs
`/workspace/bin/branchline`, the mode-0600 scoped credential at
`/workspace/config/branchline-token`, and `/workspace/config/shell.env`. The
credential travels to the UID/GID 1000 writer through stdin, never command
arguments or output. Only those files are atomically replaced; existing directory
permissions and unrelated workspace files are retained. Rerun after a paired
Branchline update. The CLI needs only Node and Git; preview builds stay on CT114.

On first setup it also creates private `/workspace/config/gitconfig` with the
agent identity `Branchline SSH <branchline@localhost>`. An existing regular,
user-owned Git configuration is preserved. This default does not represent a
personal identity; users can set their chosen name/email with `git config --global`
after loading the client environment.

The installed account's `~/.profile` sources `shell.env`, which exports PATH,
`BRANCHLINE_URL`, `BRANCHLINE_TOKEN_FILE` and `GIT_CONFIG_GLOBAL`; it contains the
token path, not its value. For an already open SSH shell, load that client
configuration explicitly:

```bash
. /workspace/config/shell.env
branchline branches
branchline checkout <node-id> /workspace/repos/<new-checkout>
```

Use a node ID returned by `branches`; the checkout directory must be new.
Run Codex in that checkout, inspect its changes and commit them. Then:

```bash
branchline submit /workspace/repos/<new-checkout>
branchline preview <node-id>
branchline status
```

Submit requires a clean worktree and checks the expected server branch tip.
It updates that one imported branch, not GitHub/GitLab and not descendants.
Refresh Branchline's graph to see the new commit. If somebody edited the branch
in the browser, fetch its current tip without replacing working files:

```bash
branchline fetch /workspace/repos/<new-checkout>
git -C /workspace/repos/<new-checkout> merge branchline/current
```

Resolve and commit any merge before submitting. A race refuses the submission
instead of overwriting the other writer. Resolve or undo outstanding partial
propagation in Branchline before further submissions. Git bundles have a
64 MiB transfer limit. See the
[Branchline source manual](https://github.com/rafael-alani/branchline/blob/staging/README.md#ssh-development-workflow)
for logs, stop and capacity commands.

## Recovery limits

The workspace lies under canonical appdata and is in the scheduled encrypted
backup scope. No VM116 disk restore, workspace restore or authenticated Codex
recovery is claimed. Keep the client SSH key separately; a rebuild needs an
authorized public key and renewed host-key verification. Cloud-init restores
the runtime around retained workspace data, but the provisioner refuses an
existing VM or orphaned directory mapping rather than replacing it.

Do not destroy VM116, its disk, mapping or workspace as a routine rollback.
Retain its data and inspect failures through the guest agent/cloud-init first.
A controlled recreation or database restore needs its own verified rollback;
VM101 remains out of scope.

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
Node `24.22.3`, bubblewrap and Codex CLI `0.171.0` through
`/usr/local/bin/codex`. It also installs the pinned browser integration below.
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
| `/workspace/tools/playwright-mcp` | Lockfile-addressed browser tool releases |
| `/workspace/browser-artifacts` | Private screenshot/output directory per browser session |

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

## Browser testing from Codex

The VM uses [Playwright MCP](https://github.com/microsoft/playwright-mcp) `0.0.86`
over stdio with its installed Chromium. Codex can navigate, click, type, inspect
console/network failures and take screenshots. Chromium runs headlessly with its
sandbox enabled; there is no browser HTTP listener or desktop display to manage.
Each session has an isolated profile and a private output directory, so parallel
agents do not share login cookies or lock the same browser profile.

New VMs install this through cloud-init. To install/repair an existing VM, copy
the tracked `hosts/codex-dev/browser` directory from the accepted homelab revision
to the development account, then run **as codex on the VM**:

```bash
python3 /absolute/path/to/browser/install.py
codex mcp get playwright
codex login status
```

The installer preserves authentication, other MCP entries and existing global
instructions. It refuses an unrelated server using the `playwright` name. A
pre-existing Codex configuration gets a private backup before first registration.
The launcher uses absolute paths, including in noninteractive SSH sessions.
The lockfile pins all three npm packages; installation skips lifecycle scripts
and uses the OS Chromium instead of downloading another browser.

Start a new Codex session in the source checkout and ask it to test the preview.
For example: “Use the browser tools to test this branch's ready preview. Log in
with the project's test fixture, check the changed flow, inspect browser errors,
and capture desktop and mobile screenshots.” Global agent instructions point to
`/workspace/config/browser.md`, which explains how to find ready URLs through
`branchline status`. Screenshots with automatic names land under
`/workspace/browser-artifacts/session-*`; explicitly named files resolve against
the agent's workspace instead. These artifacts can contain test-account data;
keep them private. Close the browser after testing.

Interactive Codex can ask for approval of browser actions. For an unattended
authorized check, `codex exec --approve-for-me "<specific test request>"` keeps
the workspace sandbox and sends required approvals to automatic review. Plain
`codex exec` defaults to no approval prompts and rejects browser tools that need
approval; that is not a browser installation failure. Keep the request bounded
to the intended previews and test actions.

CLI `0.143.0` selected retired ChatGPT models during acceptance; `0.171.0`
replaces it without changing account authentication or forcing a model preference.
The provisioner installs it at `/opt/codex-0.171.0`. For an existing VM, run these
commands as root **inside VM116** through the PVE guest agent:

```bash
/usr/local/bin/npm install -g --prefix /opt/codex-0.171.0 @openai/codex@0.171.0
ln -sfn /opt/codex-0.171.0/bin/codex /usr/local/bin/codex
apt-get install -y bubblewrap
```

Pass guest shell commands as one argument (for example with Python's subprocess
argument list), not an unquoted SSH command string. The earlier CLI remains
under `/opt/node-v24.22.3-linux-x64`; it is retained for rollback, but its default
model is no longer usable with this ChatGPT account.

To disable browser integration, run `codex mcp remove playwright` and remove
only its pointer line from global `~/.codex/AGENTS.md`. Keep artifacts, account
state and retained tool releases. Restoring a whole old configuration would
also discard later user settings, so compare before doing so.

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

## Branchline planning and implementation sessions

Branchline MCP is available to normal Codex conversations on this VM. The
workflow skill at `/workspace/config/branchline/SKILL.md` explains how to refine
plans, read graph/source context and preserve manual edits. Planning leaves Git
unchanged. The Branchline UI's submit action dispatches one separate Codex session
per planned task; prerequisite results are merged before dependents start.

The worker is a user service, `branchline-worker.service`, under the development
account. It polls the existing private HTTPS workspace; CT114 stores no VM SSH
key. `/workspace/config/branchline-worker.json` owns the agent command, workspace,
concurrency (initially two) and four-hour task timeout. Codex runs with automatic
approval review and workspace sandboxing. Existing Playwright MCP supports
browser verification of a task's published checkpoint preview before completion.
The scoped `BRANCHLINE_RUN_CONTEXT` is passed to the task's Branchline MCP process;
it is a path to a private claim file, never a token in command output.

| Path | Purpose |
|---|---|
| `/workspace/tools/branchline/releases/<commit>` | Self-contained MCP/worker modules, checksums and workflow skill |
| `/workspace/bin/branchline-mcp` | Launcher registered in Codex MCP |
| `/workspace/bin/branchline-worker` | Service launcher |
| `/workspace/branchline-runs/<run-id>` | Isolated checkout, frozen plan, private events, result bundles |
| `/workspace/config/branchline-integration-commit` | Accepted runtime source commit |

After deploying the matching Branchline web release, build its integrations from
that committed application checkout using `npm ci && npm run build:integrations`.
Copy the resulting `dist/integrations` directory over SSH into the release path
above, retaining its `SOURCE_COMMIT` and `manifest.json`. Copy this repository's
tracked `hosts/codex-dev/branchline/install.py` to the development account, then run:

```bash
python3 /absolute/path/to/install.py --release /workspace/tools/branchline/releases/<commit> --dry-run
python3 /absolute/path/to/install.py --release /workspace/tools/branchline/releases/<commit>
systemctl --user status branchline-worker.service
codex mcp get branchline
```

The installer verifies the release manifest, refuses to replace an unrelated MCP
entry, retains account/other MCP settings, and refuses runtime replacement while
this worker has an active task. Existing worker configuration is preserved.
For a fresh VM, first run the existing client configurator to install the scoped
token and shell environment. Provisioning enables user lingering; on an existing
VM enable it once as root through PVE's guest agent:

```bash
qm guest exec 116 -- loginctl enable-linger codex
```

Lingering keeps the user service running after SSH logout and across reboot.
Start a new Codex session after MCP registration. Local desktop clients can use
the same stdio package and their own private token file; HTTP-capable clients can
connect to the private workspace's `/mcp` endpoint with its bearer token. Neither
route makes the homelab publicly reachable.

The plan UI reports session ID, retained checkout, result commit and verification
evidence. Inspect failed/interrupted sessions through SSH and `codex resume <id>`;
resuming a CLI session does not automatically reacquire a cancelled worker claim.
Use a revised plan for a new scheduled attempt. To pause new execution, stop the
worker after active tasks finish; stopping it mid-task interrupts its process
group and retains work. Roll back by reinstalling a retained compatible release
while idle. Never delete run directories, account state or graph branches as part
of runtime rollback. Scheduled appdata backup covers these paths; recovery of
these new records is not claimed without a restore test.

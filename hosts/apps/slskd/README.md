# slskd

The `slskd` project runs the official stable
`slskd/slskd:latest` channel on Apps ports 5030 and 50300. The accepted
2026-07-26 runtime is 0.26.x. Nginx Proxy
Manager publishes `https://slskd.rafael.media` only to the LAN and Tailscale.
NPM terminates HTTPS; slskd's self-signed port 5031 is disabled.

The web, Soulseek, API, and JWT credentials come from production
`/root/.env`. The API key is restricted to local verification, the rollback
Docker bridge, CT102 Soularr, and CT110's sequential WUD guard. Remote
configuration and remote file deletion stay disabled.

Application databases, configuration, logs, and the disk-backed share index
persist under `/srv/appdata/docker/slskd`. The existing music library is
mounted read-only at `/music`. Completed and incomplete downloads use the
narrow read-write `/slskd-downloads` bind backed by
`/vault/shared/media/slskd`.

The prior 0.25.1 image ID and a task-specific appdata ZFS snapshot are recorded
in the phase-6 evidence. Version 0.26.0's only relevant breaking configuration
note concerns the old `permissions.file.mode` setting, which this deployment
never used. Soularr 1.2.2 compatibility and a real import were required before
acceptance. Do not delete the old image or snapshot.

slskd is digest-watched through backup-gated WUD. Before replacement, the
sequential runner atomically holds Soularr's per-cycle lock and rejects any
download or upload whose slskd state is not completed. It releases the lock
only after `/health` passes.

The repository and router continue to expose only TCP 80/443 publicly. Port
50300 listens on the Apps LAN address but is not forwarded by the declared
router contract. Full inbound Soulseek connectivity would require a separate
network-exposure review and explicit router change.

# slskd

The `slskd` project runs the DroppedNeedle-tested
`slskd/slskd:0.25.1` release on Apps ports 5030 and 50300. Nginx Proxy
Manager publishes `https://slskd.rafael.media` only to the LAN and Tailscale.
NPM terminates HTTPS; slskd's self-signed port 5031 is disabled.

The web, Soulseek, API, and JWT credentials come from the Proxmox
`/root/.env`. The DroppedNeedle API key is restricted to Docker bridge
addresses. Remote configuration and remote file deletion stay disabled.

Application databases, configuration, logs, and the disk-backed share index
persist under `/srv/appdata/docker/slskd`. The existing music library is
mounted read-only at `/music`. Completed and incomplete downloads use the
narrow read-write `/slskd-downloads` bind backed by
`/vault/shared/media/slskd`.

DroppedNeedle upstream tests against and explicitly recommends pinning slskd
0.25.1. The container therefore has `wud.watch=false`. Update it manually only
after review of slskd configuration migrations and confirmation that the target
remains supported by DroppedNeedle. Verify web login, Soulseek connectivity,
shares, search/download, DroppedNeedle API access, and an import before
accepting the new image. The scheduled appdata job is not a manual update gate.

The repository and router continue to expose only TCP 80/443 publicly. Port
50300 listens on the Apps LAN address but is not forwarded by the declared
router contract. Full inbound Soulseek connectivity would require a separate
network-exposure review and explicit router change.

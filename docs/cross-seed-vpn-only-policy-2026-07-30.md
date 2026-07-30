# cross-seed VPN-only policy evidence — 2026-07-30

## Enforced rule

All BitTorrent peer traffic must use qBittorrent's Gluetun network namespace
and `tun0` interface. A tracker whose required connectivity conflicts with
that fail-closed policy is not eligible for cross-seed. HDClone is therefore
excluded; BTSchool and RailgunPT are the complete cross-seed allowlist.

HDClone's authenticated Prowlarr resource remains managed for interactive or
Arr search use. Any torrent selected through it would still be sent to the
single qBittorrent client behind Gluetun. It is never offered to cross-seed,
and focused verification resolves its live numeric ID and rejects that ID in
`config.js`.

## Pre-change live state

Read-only inspection established:

```text
qBittorrent network mode:          container:<gluetun-id>
Prowlarr network mode:             container:<gluetun-id>
download proxy network mode:       container:<gluetun-id>
qBittorrent/proxy direct ports:    none
Gluetun tun0:                      present
VPN port forwarding:               off
cross-seed endpoints:              3
existing HDClone cross-seeds:      0
active qBittorrent downloads:      1
latest scheduled appdata backup:   success
```

The active download was not interrupted. Gluetun's existing effective
port-forwarding state was already off, so the policy could be made explicit
in Compose without recreating its shared namespace cohort during this task.
The prior mode-0600 generated configuration and checksum were retained at:

```text
/docker/cross-seed/backups/codex-manual/2026-07-30T084244Z-vpn-only-policy
```

## Reproducible enforcement

- Gluetun declares `VPN_PORT_FORWARDING=off`.
- qBittorrent, NZBGet, and Prowlarr declare
  `network_mode: service:gluetun`.
- The Servarr verifier resolves Gluetun's live container ID and requires all
  three consumers to use `container:<that-id>` with no direct host port
  bindings.
- qBittorrent's existing verifier requires its listening interface to be
  `tun0`, random ports and UPnP off, the high peer port absent from LAN
  publications, and Gluetun's native health check to pass.
- The notice-aware download proxy separately requires Gluetun's exact live
  namespace ID and has no host port.
- cross-seed renders only the BTSchool and RailgunPT Prowlarr IDs, both through
  the notice-aware proxy on Gluetun port 9697.
- The focused verifier reads all three managed IDs from Prowlarr's database,
  requires exactly the first two in `config.js`, and explicitly rejects the
  HDClone ID.
- Deployment restarts cross-seed after every generated-config reconciliation,
  ensuring an updated bind-mounted allowlist is actually loaded.

The configuration has network-free regression tests proving exactly two
eligible endpoints and the absence of HDClone/direct Prowlarr port 9696.

## Live acceptance

The final deployment retained the active qBittorrent transfer and existing
cross-seed torrent. The rendered runtime configuration contains two Torznab
endpoints, both at `gluetun:9697`; HDClone's ID and direct Prowlarr port 9696
are absent. The focused cross-seed verifier and the VPN portion of the Servarr
verifier pass.

No tracker credential, Prowlarr API key, private announce URL, passkey, peer
address, or VPN credential was printed or committed.

## Rollback

Revert the policy commit and rerender cross-seed only. Do not recreate the
Gluetun/qBittorrent/NZBGet/Prowlarr cohort merely to roll back the allowlist.
Retain canonical appdata and all cross-seed hardlinks. Re-enabling HDClone for
cross-seed would deliberately weaken this policy and requires a new explicit
user decision.

Official references:

- <https://github.com/qdm12/gluetun-wiki/blob/main/setup/options/port-forwarding.md>
- <https://github.com/qdm12/gluetun-wiki/blob/main/setup/options/firewall.md>

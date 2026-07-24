# Zotero WebDAV

This service stores personal-library attachment files only. Zotero metadata
continues to sync through the Zotero account, and Zotero group-library
attachments cannot use WebDAV.

Observed 2026-07-24: the Compose project was healthy and its focused verifier
confirmed unauthenticated rejection plus authenticated PROPFIND, PUT, GET,
byte comparison, DELETE, and HTTPS proxying. The server side is complete;
whether each Zotero client has been configured cannot be inferred from the
server.

The private endpoint is `https://zotero.rafael.media/zotero/`. Pi-hole's
`rafael.media` wildcard points to Infra NPM, which terminates HTTPS and proxies
to Apps port 8088. Keep the route private to LAN/Tailscale.

In Zotero, open **Settings → Sync → File Syncing**, enable attachment syncing
for **My Library**, choose **WebDAV**, and enter:

- URL: `https://zotero.rafael.media/zotero/`
- Username: the `ZOTERO_WEBDAV_USERNAME` value in Proxmox `/root/.env`
- Password: the `ZOTERO_WEBDAV_PASSWORD` value in Proxmox `/root/.env`

Retrieve the credentials locally when configuring Zotero. Run this only in a
private terminal and do not paste its output into task logs:

```bash
ssh root@192.168.0.250 \
  "sed -n -e 's/^ZOTERO_WEBDAV_USERNAME=//p' -e 's/^ZOTERO_WEBDAV_PASSWORD=//p' /root/.env"
```

Click **Verify Server** in Zotero after entering the settings.

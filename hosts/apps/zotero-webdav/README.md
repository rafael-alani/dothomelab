# Zotero WebDAV

This service stores personal-library attachment files only. Zotero metadata
continues to sync through the Zotero account, and Zotero group-library
attachments cannot use WebDAV.

The private endpoint is `https://zotero.rafael.media/zotero/`. Pi-hole's
`rafael.media` wildcard points to Infra NPM, which terminates HTTPS and proxies
to Apps port 8088. Keep the route private to LAN/Tailscale.

In Zotero, open **Settings → Sync → File Syncing**, enable attachment syncing
for **My Library**, choose **WebDAV**, and enter:

- URL: `https://zotero.rafael.media/zotero/`
- Username: the `ZOTERO_WEBDAV_USERNAME` value in Proxmox `/root/.env`
- Password: the `ZOTERO_WEBDAV_PASSWORD` value in Proxmox `/root/.env`

Retrieve the credentials locally when configuring Zotero:

```bash
ssh root@192.168.0.250 \
  "sed -n -e 's/^ZOTERO_WEBDAV_USERNAME=//p' -e 's/^ZOTERO_WEBDAV_PASSWORD=//p' /root/.env"
```

Click **Verify Server** in Zotero after entering the settings.

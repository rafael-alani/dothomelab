# Syncthing canonical shared paths

## Scope and rollback

This change lets Syncthing folder definitions use the same complete paths seen
on PVE and CT110, such as `/vault/shared/media/obsidian`. It does not start a
Proton backup, authenticate Proton, enable the Proton timer, or change any
shared-data ownership.

Before changing the container mounts, the live Syncthing configuration was
copied with its ownership and mode intact to:

```text
/srv/appdata/docker/syncthing/config/config.xml.pre-canonical-paths-20260726T0937Z
```

The copy contains sensitive Syncthing configuration and remains in protected
appdata at mode 0600. The prior Compose behavior is commit `28f695d`; restoring
that Compose definition and the saved XML returns the legacy `/vault` and
`/versions` aliases without deleting the received vault bytes.

## Observed pre-change state

- CT110 already had PVE `/vault/shared` mounted read-write at
  `/vault/shared`.
- Syncthing instead received only
  `/vault/shared/media/obsidian -> /vault` and
  `/vault/shared/media/.obsidian-versions -> /versions`.
- The live placeholder folder `obsidian-vault` was Receive Only, listed only
  the Infra device, and its directory contained only `.stfolder` and
  `.stignore`.
- Folder `6bmya-jvonu` was pending from the already configured MacBook device.
- Static GUI authentication was already configured.

## Applied state

- Syncthing now receives `/vault/shared -> /vault/shared` read-write.
- Folder `6bmya-jvonu` is accepted from the MacBook at
  `/vault/shared/media/obsidian`, is Receive Only, and keeps 365-day staggered
  versions at `/vault/shared/media/.obsidian-versions`.
- The helper's placeholder safety check now inspects the canonical CT110 path,
  validates pending offer devices before deleting the placeholder, and
  preserves existing GUI authentication.
- Proton continues to receive only the Obsidian and photo subtrees read-only,
  but both appear at their canonical `/vault/shared/media/...` paths.
- The Proton helper image is rebuilt from the pinned Dockerfile so its embedded
  backup script and the Compose mount destinations agree.

The broader Syncthing mount is intentional and user-authorized. Only configured
folders participate in synchronization, but the container can access any
shared path permitted to UID/GID `1000:1000`; every future folder path still
needs an ownership and scope review. Proton retains narrower read-only mounts.

## Verification evidence

- Syncthing kept the same image ID across its brief recreation:
  `sha256:62cee511289c3fcbaec0d0eaf1be0d24cfc329f641a6ab38d843bf9128f632f8`.
- The bcrypt GUI password hash before and after the change matched exactly.
- The pending folder list became empty and the accepted folder listed both the
  Infra and MacBook devices.
- The initial seed reached 100% completion: 12,296 in-sync files,
  2,488,959,488 in-sync bytes, zero needed items/bytes, and zero folder or
  system errors.
- The focused verifier passed Compose rendering, container health, canonical
  folder/version paths, private GUI/DNS/HTTPS, sync port, canonical read-write
  Syncthing mount, absence of the legacy alias, read-only Proton source mounts,
  private Proton work storage, and the pinned Proton CLI.
- The Proton archive test passed inside the purpose-built Linux image,
  including three cycles, two-generation retention, upload/download checksum
  verification, and a non-destructive Obsidian restore download.

No real Proton upload or restore has been claimed. The first authenticated
cycle, isolated restore tests, and timer enablement remain separate acceptance
steps.

# Media pipeline phase 2 evidence

Date: 2026-07-25

Scope: deploy Shelfarr on CT102 and BookOrbit on CT112, exercise one legal
ebook lifecycle, and retain Readarr and Kavita unchanged. Production secrets
and external-service credentials are deliberately absent from this document.

## Upstream revalidation

Primary sources were rechecked immediately before implementation:

- [Shelfarr getting started](https://shelfarr.org/getting-started.html),
  [configuration](https://shelfarr.org/configuration.html), and
  [repository](https://github.com/Pedro-Revez-Silva/shelfarr), observed at
  source commit `fe13918c749295412de0e47bac9c4755296de6a0` from 2026-07-24;
- [BookOrbit installation](https://bookorbit.app/installation),
  [library creation](https://bookorbit.app/creating-a-library),
  [adding books](https://bookorbit.app/adding-books), and
  [repository](https://github.com/bookorbit/bookorbit), observed at source
  commit `d70f06fc073b8f606eefd6d340fbd0a4ab06f437` from 2026-07-22;
- BookOrbit's [OPDS](https://bookorbit.app/opds),
  [KOReader](https://bookorbit.app/koreader-plugin), and
  [Kobo](https://bookorbit.app/kobo) integration documentation.

The validated contracts are Shelfarr's rolling GHCR application image,
`/up` health endpoint, port 80, persistent `/rails/storage`, and its current
minimum Libation companion; and BookOrbit's rolling GHCR application image,
port 3000, `/api/v1/health`, durable `/data`, and
`pgvector/pgvector:pg18`. Both applications use upstream `latest`; the
BookOrbit database uses the explicit supported PostgreSQL major and is
excluded from WUD.

## Preflight and recovery boundary

PVE 9.1.2, both ZFS pools, canonical mounts, the managed guests, and the most
recent scheduled appdata job were healthy before mutation. CT102 had 13
running containers and CT112 had 30. The canonical book directories already
had the mapped ownership needed by guest UID/GID `1000:1000`.

No database or existing durable data was migrated. The normal scheduled
appdata backup remains the rollback source; no routine on-demand PBS backup
was started. The production environment's exact mode-0600 pre-change copy is
retained as
`/root/.env.pre-shelfarr-bookorbit-20260725T190253Z`. Readarr and Kavita
appdata were neither written nor migrated. The qBittorrent change is limited
to the exact private `servarr-hello_default` subnet authentication whitelist
and can be reversed by removing its two deterministic whitelist settings.

## Declared and deployed state

Implementation commit
`ba63453b4665f6e827baea7508ec56e032827c5a`
(`Deploy Shelfarr and BookOrbit media pipeline`) was pushed to `main` and
deployed to CT102, CT110, and CT112 for the acceptance run. All three guests'
`DEPLOYED_COMMIT` files matched it.

Shelfarr is a separate two-container `shelfarr` project on CT102:

- `shelfarr` and its minimum `shelfarr-libation` companion are healthy and
  run their application processes without root;
- Libation has no Audible credentials; its connection, synchronization,
  scheduled synchronization, and automatic backup are disabled;
- every direct source is disabled and no indexer was added;
- the only enabled integrations are existing Prowlarr, qBittorrent, NZBGet,
  and BookOrbit, and every connection test passed;
- canonical output is
  `/ebooks/{author}/{title}/{author} - {title}.ext`, with the same relative
  `{author}/{title}` key declared for the next audiobook phase;
- NZBGet's existing `/data/usernet` path is now present at `/downloads`, while
  qBittorrent retains `/data/torrents`.

BookOrbit is a separate two-container `bookorbit` project on CT112:

- the application is healthy as user `node`, has a read-only root filesystem,
  drops all capabilities except its documented startup permission set, and
  persists only `/data`;
- PostgreSQL/pgvector runs as UID 999 and persists under canonical appdata;
- Ebooks, PDFs, Comics, and Manga use only paths that already existed and all
  four mounts are read-only;
- each library uses `book_per_folder`, daily scan and filesystem watch;
- physical rename and every embedded-file metadata write are disabled.

The live result is CT102 15 containers in two projects, CT110 11 in five, and
CT112 32 in seventeen: 58 running containers in 24 projects. The repository's
clean-build declaration is 61 containers in 27 projects. The three-container
and three-project difference is pre-existing: Paperless-GPT cannot start
without its externally supplied OpenAI key, and Prometheus/Loki were already
documented as pending live deployment.

## Secret and database recovery

`scripts/initialize-shelfarr-bookorbit-env.py` creates only missing values,
writes atomically with mode 0600, and never displays a value. Its local
idempotency test created eight secrets on the first pass and preserved all
eight on the second. The production rerun reported zero new secrets and eight
preserved. `.env.example` contains placeholders only.

The installed PVE pre-backup hook is
`/etc/dothomelab/backup-pre.d/40-bookorbit-database`. It enters CT112 and
creates a custom-format PostgreSQL dump, roles dump, extension inventory,
application counts, and SHA-256 manifest before the normal appdata snapshot.
The latest acceptance dump contained:

```text
users=1
libraries=4
books=1
pg_trgm=1.6
unaccent=1.1
uuid-ossp=1.1
vector=0.8.5
```

The final dump SHA-256 was
`6717850f61376d1e0148ed0787b236244e2ca8ce2870e63cc77f09f40362956c`.
An isolated `pgvector/pgvector:pg18` container with `--network none` restored
the dump and matched both the source counts and extension versions. The final
retained successful test is
`/srv/appdata/docker/bookorbit/restore-tests/20260725T194303Z`; its stopped
container is `bookorbit_restore_test_20260725t194303z`. Earlier failed,
stopped test artifacts were retained for diagnosis and rollback rather than
deleted.

## Ebook acceptance lifecycle

The legal sample was the official Project Gutenberg EPUB for
[Alice's Adventures in Wonderland, ebook 11](https://www.gutenberg.org/ebooks/11),
which Project Gutenberg identifies as public domain in the USA. The source
EPUB SHA-256 was:

```text
4ac9fc092435338fdb28e96b02989a46bbe075ec310f1789db87a653761cce92
```

Shelfarr created and approved request `1` for Open Library work
`OL138052W`. Because no authorized existing indexer returned this
public-domain edition, the test used Shelfarr's supported administrator manual
fulfillment path. No source, indexer, provider, or credential was added.
Shelfarr completed the request and organized the file as:

```text
/vault/shared/media/books/ebooks/Lewis Carroll/
  Alice's Adventures in Wonderland/
    Lewis Carroll - Alice's Adventures in Wonderland.epub
```

The destination is mode 0640, mapped guest owner/group `1000:1000`, 189,199
bytes, and has the same SHA-256 as the source. The shared book-key result is
therefore `Lewis Carroll/Alice's Adventures in Wonderland`.

Shelfarr invoked its supported BookOrbit library scan integration. BookOrbit
discovered book `1` and file `1`; its browser reader served the EPUB with a
successful byte-range response (`206`) and valid ZIP header. An authenticated
download reproduced the source hash. OPDS search returned one acquisition
entry and its acquisition download reproduced the same hash. Repeated
BookOrbit scan, read, download, and focused write-denial tests left the
canonical file hash unchanged.

## Device surfaces

The authenticated KOReader credentials and device-management surfaces passed.
The plugin endpoint correctly rejected an unauthenticated request with `401`;
no KOReader credential or physical device was invented. The authenticated
Kobo settings/device surfaces also passed and reported zero devices.

No physical reader was available, so device sync is not claimed:

- KOReader: in BookOrbit, open **Settings > Integrations > KOReader**, create
  a separate account, download and unzip the plugin, copy
  `bookorbit.koplugin` to `koreader/plugins/`, restart KOReader, then use
  **Tools > BookOrbit Sync**.
- Kobo: add the device in BookOrbit **Settings > Kobo**; over USB edit
  `.kobo/Kobo/Kobo eReader.conf`, set `[OneStoreServices] api_endpoint` to
  the one-time private `/api/v1/kobo/{deviceToken}` endpoint, safely eject,
  connect to the private network, and sync. The token must not be logged.

## Network, UX, updates, and preservation

Pi-hole resolves both private names to `192.168.0.110`. NPM routes Shelfarr to
CT102 port 5056 and BookOrbit to CT112 port 3002 with the retained wildcard
certificate, WebSockets, LAN/Tailscale allow rules, and final `deny all`.
Nginx configuration and NPM SQLite integrity passed. Private HTTPS returned
Shelfarr's expected authenticated redirect and BookOrbit HTTP 200.

Homarr reconciliation is idempotent and passed with 19 managed applications,
57 items, and 133 layouts. The central WUD dry-run found 41 watched
containers, all backup-gated, including Shelfarr, Libation, and BookOrbit.
BookOrbit PostgreSQL was absent from discovery and retains `wud.watch=false`.
No eligible update was applied.

Readarr remained healthy with container ID
`a90a28ee892f97fab36aa4dced13e711f98b7d2d8878d9512cba5ef9865dfeac`;
its configuration SHA-256 remained
`99288ee54f5a5f656027dc3a7599e3dd77bc99c5b347785d379005f1207652e6`.
Kavita remained healthy with container ID
`b7786934e63f604b18624598bc00a94a01797cff7c07edf6810c436a23005d2f`.

## Verification and known external gap

Completed checks:

- final `docker compose config --quiet` passed for both projects against a
  temporary mode-0600 production environment copy, which was then removed;
- Python compilation, Bash parsing, Node syntax, `git diff --check`, and a
  generated-secret idempotency/length/mode test passed; local `shellcheck` was
  unavailable;
- CT102's existing Servarr verifier, Shelfarr's focused verifier, BookOrbit's
  focused verifier, Infra services/NPM/Homarr verification, and the WUD
  dry-run passed from the deployed implementation commit;
- direct health, storage mounts, read-only enforcement, process identities,
  DNS, private HTTPS, database dump/restore, source/destination hashes,
  OPDS/reader/download, and unchanged Readarr/Kavita checks passed.

The production `bootstrap.sh --dry-run` was run without inventing an external
credential. It stops before mutation because the pre-existing production
environment lacks `PAPERLESS_GPT_OPENAI_API_KEY`. A second dry-run with a
mode-0600 temporary environment copy and an explicit non-production
Paperless-GPT placeholder is used only to exercise the remaining dry-run
path; the temporary copy is removed and production is not changed.

`provision/verify.sh` was also invoked. Its ZFS, live media-contract, HAOS,
and every LXC configuration/mount check passed. It then reported the exact
known boundary: `LXC 112 has 32 active containers; expected 35`. The complete
clean-build verifier cannot pass against today's live inventory because it
correctly declares the three already-known pending Apps projects described
above. This phase does not weaken that declaration or add a dummy OpenAI
credential merely to turn the check green. All phase-specific checks passed.

Rollback is a Git revert followed by exact guest sync and Compose
reconciliation. Shelfarr's new state, BookOrbit state/database, generated
secrets, database dumps, prior environment copy, stopped isolated-restore
artifacts, and old container images remain available. Canonical book files
are outside PBS appdata protection and must not be deleted as part of an
application rollback.

# Contentflow

Contentflow is Rafael's custom Python companion to n8n, from the local project
`/Users/rafael/Repos/n8n`. It reads Obsidian publication notes, prepares bundles
and delivery receipts, reviews incoming media, and supports explicitly selected
archive operations. It is separate from n8n itself and from the native blog
publisher. Its deployed source revision is `5ac453771bad66662275362217394a59cfb07d7f`.

On November 5, n8n had five Contentflow workflows. **Ready notes** and
**Incoming media** were active; **Archive preview**, **Apply reviewed archive**
and **Integration smoke test** were inactive. External publication is disabled
(`CONTENTFLOW_PUBLISH_ENABLED=false`). The media inbox contains example files,
not the production media library. These are real configuration limits, not
evidence of working social publication or production-media ingestion.

## Deployment and data

CT110 runs the exact existing image, now enrolled in this repository's Compose
contract. Nothing rebuilds or updates application code automatically. The API
listens on guest loopback port 8787 and n8n reaches `http://contentflow:8787` on
`n8n_default`. Its token is in the existing n8n credential and a protected file;
never put it in a workflow URL or Git. No public proxy route is declared.

| Input | Canonical location | Access |
|---|---|---|
| Queue, bundles, reports and receipts | `/srv/appdata/docker/contentflow/state` | Application read/write |
| Deployment settings | `/srv/appdata/docker/contentflow/deployment.env` | Root-only dotenv, retained from the existing deployment |
| API token | `/srv/appdata/docker/contentflow/secrets/api-token` | Read-only secret mount |
| Obsidian notes | `/vault/shared/media/obsidian` | Read-only; shared media backup class |
| Example media inbox | `/srv/appdata/docker/contentflow/example-media` | Read-only; explicitly still examples |
| Source and image archives | `contentflow/recovery/5ac453771bad66662275362217394a59cfb07d7f/` below canonical appdata | Root-only recovery artifacts |

The source project currently has no configured Git remote. Recovery therefore
uses the preserved committed source archive and **exact exported running image**,
with their hashes and image ID recorded in `release.json`. This avoids depending
on an untracked guest checkout or rebuilding against changed Python base images.
The existing `/opt/contentflow` checkout remains a retained rollback artifact;
the active service no longer mounts files from it.

## Recover and verify

Restore canonical appdata, shared Obsidian data and n8n first. On CT110,
`python3 /opt/dothomelab/hosts/infra/contentflow/prepare.py` verifies both archive
hashes and all durable inputs, loads a missing image and gives it the declared
immutable revision tag. It refuses an unexpected existing image. Then deploy
the Compose file with quiet validation. Bootstrap performs this sequence.

Run `python3 /opt/dothomelab/hosts/infra/contentflow/verify.py` to check the exact
image, private listener, mounts, disabled publishing and n8n-to-Contentflow
health request. Pulse covers the Infra Docker container; the existing private
Homarr n8n tile is the workflow entry point. There is no standalone Homarr tile
for the loopback-only API.

Future application changes belong in the Contentflow project. Publish a reviewed
source revision and prepare a new verified recovery image/source pair before
changing this enrollment. Provider credentials, selecting a real media inbox,
activating archive workflows and external publication require their own explicit
setup; this maintenance does not activate them. Do not rotate the existing token
or re-import workflows merely to rebuild the container.

The November recovery archives are in current appdata and enter the next
scheduled PBS backup. A full clean-host restoration has not been performed.

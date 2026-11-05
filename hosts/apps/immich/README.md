# Immich updates and PostgreSQL recovery

Immich and its database remain manual. The baseline is Immich 3.3.6,
PostgreSQL 18.6, VectorChord 1.1.1, pgvector 0.8.5 and Valkey 9.1.3.
The PostgreSQL Dockerfile pins the upstream extension image and installs the
current PostgreSQL patch. Rebuilding requires that image and the exact Debian
PGDG package versions to remain available. Preserve the installed image for
offline rollback; a registry-independent rebuild has not been tested.

`IMMICH_DB_DATA_LOCATION` names the parent mounted at `/var/lib/postgresql`;
the database lives below `18/docker`. Bootstrap validates existing version-18
data and builds the image from Git. It never converts a PostgreSQL 14 directory.

For a future database migration, run `checkpoint.py capture <label>`, then
`migrate-postgres.py <checkpoint> <new-parent>` inside CT112. The helper is
specific to this 14-to-18 transition: it restores logically on an isolated
network, checks every table count and managed-original hash, checks extension
versions and indexes, and leaves the production database untouched. It rejects
an existing destination. Inspect its source before adapting it to another major.

After a successful rehearsal, capture again with `--quiesce`. This stops the
server and machine-learning writers and deliberately leaves them stopped.
Restore that fresh checkpoint to a different, absent `postgres18-*` directory.
Only then update the PVE dotenv path, validate Compose quietly, replace the
database and start the writers. Run `verify.sh 3.3.6` and compare checkpoint
counts before accepting the cutover. Never copy database files between majors.

Retain the old database directory, old image, private runtime inspection and
dotenv backup with the checkpoint. Rollback before new writes means restoring
that path and the old database image/mount in Compose. Once the new database
accepts writes, switching back loses those writes; reconcile or restore them
before rollback. Successful isolated containers are removed automatically;
their data and receipts remain until the upgrade is accepted. Failed tests are
stopped and retained for diagnosis.

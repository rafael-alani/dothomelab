# BookOrbit

BookOrbit runs as a private CT112 project on
`https://bookorbit.rafael.media`. Its application state and PostgreSQL data
live under `/srv/appdata/docker/bookorbit`. The application follows upstream
root-filesystem hardening and its four existing libraries are mounted
read-only:

- `/library/ebooks`
- `/library/pdfs`
- `/library/comics`
- `/library/mangas`

Every library uses `book_per_folder`, daily scan plus filesystem watch, and has
physical rename and embedded-file metadata writes disabled. Shelfarr selects
the `Ebooks` library through BookOrbit's supported scan API.

`bookorbit:latest` follows the rolling application channel and is
backup-gated in WUD. `pgvector/pgvector:pg18` is an explicit application-local
database major and has `wud.watch=false`. Before a manual database image
change, run `./backup-database.sh` and `./restore-test.sh`; never copy the live
PostgreSQL directory between versions.

The initializer creates the first administrator and an OPDS identity from
PVE `/root/.env`. KOReader can install the package exposed by BookOrbit's
authenticated plugin endpoint; Kobo registration remains a physical-device
step.

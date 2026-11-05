# Upstream's current VectorChord image still includes PostgreSQL 18.4.
# Keep its tested extension bundle and install the current PostgreSQL patch.
FROM ghcr.io/immich-app/postgres:18-vectorchord1.1.1-pgvector0.8.5@sha256:b427de4534e09120dd32cba873a2e88f9d026db7a0d813b226c5421c30669546
RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        postgresql-18=18.6-1.pgdg12+2 postgresql-client-18=18.6-1.pgdg12+2 \
    && rm -rf /var/lib/apt/lists/*

# pgvector 0.8.0 recovery definition

Unmodified SQL and license from [pgvector v0.8.0](https://github.com/pgvector/pgvector/tree/2627c5ff775ae6d7aef0c430121ccf857842d2f2).
The upstream Makefile copies `sql/vector.sql` to `vector--0.8.0.sql`.

The captured database uses extension SQL version 0.8.0, while its installed
image contains only the 0.8.1 creation script. The checkpoint tester supplies
this definition only to its isolated database container, using the same binary
image as production. It never changes production packages or extension versions.
The helper pins the SQL checksum. Retain [the upstream license](pgvector-LICENSE)
with this file; recovery needs no live upstream download.

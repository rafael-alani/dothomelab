# Consolidated service routes

Nginx Proxy Manager is still a legacy project. Until its persistent state is
moved out of CT110's root disk, the route mapping in
`update-consolidated-routes.sql` is the Git-managed recovery definition.

Back up `/var/lib/docker/volumes/proxy_data/_data/database.sqlite`, apply the SQL
with `sqlite3`, verify `PRAGMA integrity_check`, then regenerate the affected
proxy files through NPM. Validate with `nginx -t` before reloading Nginx.

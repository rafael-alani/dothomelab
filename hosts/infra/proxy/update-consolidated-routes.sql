BEGIN IMMEDIATE;

UPDATE proxy_host
SET forward_host = '192.168.0.110', forward_port = 7575, modified_on = datetime('now')
WHERE domain_names = '["rafael.media"]';

UPDATE proxy_host
SET forward_host = '192.168.0.110', forward_port = 9090, modified_on = datetime('now')
WHERE domain_names = '["vault.rafael.media"]';

UPDATE proxy_host
SET forward_host = '192.168.0.112', forward_port = 5055, modified_on = datetime('now')
WHERE domain_names = '["jellyseerr.rafael.media"]';

UPDATE proxy_host
SET forward_host = '192.168.0.112', forward_port = 8096, modified_on = datetime('now')
WHERE domain_names = '["jellyfin.rafael.media"]';

UPDATE proxy_host
SET forward_host = '192.168.0.110', forward_port = 8080, modified_on = datetime('now')
WHERE domain_names = '["pi-hole.rafael.media"]';

COMMIT;

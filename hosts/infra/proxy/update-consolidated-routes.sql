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

UPDATE proxy_host
SET forward_host = '192.168.0.112',
    forward_port = 3000,
    modified_on = datetime('now')
WHERE domain_names = '["jellystat.rafael.media"]';

UPDATE proxy_host
SET forward_host = '192.168.0.112',
    forward_port = 9925,
    modified_on = datetime('now')
WHERE domain_names = '["mealie.rafael.media"]';

UPDATE proxy_host
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = '192.168.0.112',
    forward_port = 8088,
    advanced_config = 'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 0;
proxy_request_buffering off;',
    modified_on = datetime('now')
WHERE domain_names = '["zotero.rafael.media"]';

INSERT INTO proxy_host (
  created_on,
  modified_on,
  owner_user_id,
  is_deleted,
  domain_names,
  forward_host,
  forward_port,
  access_list_id,
  certificate_id,
  ssl_forced,
  caching_enabled,
  block_exploits,
  advanced_config,
  meta,
  allow_websocket_upgrade,
  http2_support,
  forward_scheme,
  enabled,
  locations,
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
)
SELECT
  datetime('now'),
  datetime('now'),
  owner_user_id,
  0,
  '["zotero.rafael.media"]',
  '192.168.0.112',
  8088,
  access_list_id,
  certificate_id,
  1,
  0,
  block_exploits,
  'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 0;
proxy_request_buffering off;',
  meta,
  allow_websocket_upgrade,
  http2_support,
  'http',
  1,
  '[]',
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
FROM proxy_host
WHERE domain_names = '["mealie.rafael.media"]'
  AND is_deleted = 0
  AND NOT EXISTS (
    SELECT 1
    FROM proxy_host
    WHERE domain_names = '["zotero.rafael.media"]'
  )
LIMIT 1;

UPDATE proxy_host
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = '192.168.0.112',
    forward_port = 8002,
    access_list_id = 0,
    ssl_forced = 1,
    caching_enabled = 0,
    block_exploits = 1,
    allow_websocket_upgrade = 1,
    http2_support = 1,
    advanced_config = 'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 512m;
proxy_request_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;',
    modified_on = datetime('now')
WHERE domain_names = '["paperless.rafael.media"]';

INSERT INTO proxy_host (
  created_on,
  modified_on,
  owner_user_id,
  is_deleted,
  domain_names,
  forward_host,
  forward_port,
  access_list_id,
  certificate_id,
  ssl_forced,
  caching_enabled,
  block_exploits,
  advanced_config,
  meta,
  allow_websocket_upgrade,
  http2_support,
  forward_scheme,
  enabled,
  locations,
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
)
SELECT
  datetime('now'),
  datetime('now'),
  owner_user_id,
  0,
  '["paperless.rafael.media"]',
  '192.168.0.112',
  8002,
  0,
  certificate_id,
  1,
  0,
  1,
  'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 512m;
proxy_request_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;',
  meta,
  1,
  1,
  'http',
  1,
  '[]',
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
FROM proxy_host
WHERE domain_names = '["mealie.rafael.media"]'
  AND is_deleted = 0
  AND NOT EXISTS (
    SELECT 1
    FROM proxy_host
    WHERE domain_names = '["paperless.rafael.media"]'
  )
LIMIT 1;

UPDATE proxy_host
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = '192.168.0.112',
    forward_port = 8003,
    access_list_id = 0,
    ssl_forced = 1,
    caching_enabled = 0,
    block_exploits = 1,
    allow_websocket_upgrade = 1,
    http2_support = 1,
    advanced_config = 'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 512m;
proxy_request_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;',
    modified_on = datetime('now')
WHERE domain_names = '["paperless-gpt.rafael.media"]';

INSERT INTO proxy_host (
  created_on,
  modified_on,
  owner_user_id,
  is_deleted,
  domain_names,
  forward_host,
  forward_port,
  access_list_id,
  certificate_id,
  ssl_forced,
  caching_enabled,
  block_exploits,
  advanced_config,
  meta,
  allow_websocket_upgrade,
  http2_support,
  forward_scheme,
  enabled,
  locations,
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
)
SELECT
  datetime('now'),
  datetime('now'),
  owner_user_id,
  0,
  '["paperless-gpt.rafael.media"]',
  '192.168.0.112',
  8003,
  0,
  certificate_id,
  1,
  0,
  1,
  'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 512m;
proxy_request_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;',
  meta,
  1,
  1,
  'http',
  1,
  '[]',
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
FROM proxy_host
WHERE domain_names = '["mealie.rafael.media"]'
  AND is_deleted = 0
  AND NOT EXISTS (
    SELECT 1
    FROM proxy_host
    WHERE domain_names = '["paperless-gpt.rafael.media"]'
  )
LIMIT 1;

UPDATE proxy_host
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = '192.168.0.112',
    forward_port = 9090,
    access_list_id = 0,
    ssl_forced = 1,
    caching_enabled = 0,
    block_exploits = 1,
    allow_websocket_upgrade = 1,
    http2_support = 1,
    advanced_config = 'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;',
    modified_on = datetime('now')
WHERE domain_names = '["prometheus.rafael.media"]';

INSERT INTO proxy_host (
  created_on,
  modified_on,
  owner_user_id,
  is_deleted,
  domain_names,
  forward_host,
  forward_port,
  access_list_id,
  certificate_id,
  ssl_forced,
  caching_enabled,
  block_exploits,
  advanced_config,
  meta,
  allow_websocket_upgrade,
  http2_support,
  forward_scheme,
  enabled,
  locations,
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
)
SELECT
  datetime('now'),
  datetime('now'),
  owner_user_id,
  0,
  '["prometheus.rafael.media"]',
  '192.168.0.112',
  9090,
  0,
  certificate_id,
  1,
  0,
  1,
  'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;',
  meta,
  1,
  1,
  'http',
  1,
  '[]',
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
FROM proxy_host
WHERE domain_names = '["mealie.rafael.media"]'
  AND is_deleted = 0
  AND NOT EXISTS (
    SELECT 1
    FROM proxy_host
    WHERE domain_names = '["prometheus.rafael.media"]'
  )
LIMIT 1;

UPDATE proxy_host
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = '192.168.0.112',
    forward_port = 3100,
    access_list_id = 0,
    ssl_forced = 1,
    caching_enabled = 0,
    block_exploits = 1,
    allow_websocket_upgrade = 1,
    http2_support = 1,
    advanced_config = 'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 64m;
proxy_request_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;',
    modified_on = datetime('now')
WHERE domain_names = '["loki.rafael.media"]';

INSERT INTO proxy_host (
  created_on,
  modified_on,
  owner_user_id,
  is_deleted,
  domain_names,
  forward_host,
  forward_port,
  access_list_id,
  certificate_id,
  ssl_forced,
  caching_enabled,
  block_exploits,
  advanced_config,
  meta,
  allow_websocket_upgrade,
  http2_support,
  forward_scheme,
  enabled,
  locations,
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
)
SELECT
  datetime('now'),
  datetime('now'),
  owner_user_id,
  0,
  '["loki.rafael.media"]',
  '192.168.0.112',
  3100,
  0,
  certificate_id,
  1,
  0,
  1,
  'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 64m;
proxy_request_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;',
  meta,
  1,
  1,
  'http',
  1,
  '[]',
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
FROM proxy_host
WHERE domain_names = '["mealie.rafael.media"]'
  AND is_deleted = 0
  AND NOT EXISTS (
    SELECT 1
    FROM proxy_host
    WHERE domain_names = '["loki.rafael.media"]'
  )
LIMIT 1;

UPDATE proxy_host
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = '192.168.0.112',
    forward_port = 8080,
    access_list_id = 0,
    ssl_forced = 1,
    caching_enabled = 0,
    block_exploits = 1,
    allow_websocket_upgrade = 1,
    http2_support = 1,
    advanced_config = 'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;',
    modified_on = datetime('now')
WHERE domain_names = '["immichframe.rafael.media"]';

INSERT INTO proxy_host (
  created_on,
  modified_on,
  owner_user_id,
  is_deleted,
  domain_names,
  forward_host,
  forward_port,
  access_list_id,
  certificate_id,
  ssl_forced,
  caching_enabled,
  block_exploits,
  advanced_config,
  meta,
  allow_websocket_upgrade,
  http2_support,
  forward_scheme,
  enabled,
  locations,
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
)
SELECT
  datetime('now'),
  datetime('now'),
  owner_user_id,
  0,
  '["immichframe.rafael.media"]',
  '192.168.0.112',
  8080,
  0,
  certificate_id,
  1,
  0,
  1,
  'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;',
  meta,
  1,
  1,
  'http',
  1,
  '[]',
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
FROM proxy_host
WHERE domain_names = '["mealie.rafael.media"]'
  AND is_deleted = 0
  AND NOT EXISTS (
    SELECT 1
    FROM proxy_host
    WHERE domain_names = '["immichframe.rafael.media"]'
  )
LIMIT 1;

UPDATE proxy_host
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = '192.168.0.112',
    forward_port = 5690,
    access_list_id = 0,
    ssl_forced = 1,
    caching_enabled = 0,
    block_exploits = 1,
    allow_websocket_upgrade = 1,
    http2_support = 1,
    advanced_config = 'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_read_timeout 300s;
proxy_send_timeout 300s;',
    modified_on = datetime('now')
WHERE domain_names = '["wizarr.rafael.media"]';

INSERT INTO proxy_host (
  created_on,
  modified_on,
  owner_user_id,
  is_deleted,
  domain_names,
  forward_host,
  forward_port,
  access_list_id,
  certificate_id,
  ssl_forced,
  caching_enabled,
  block_exploits,
  advanced_config,
  meta,
  allow_websocket_upgrade,
  http2_support,
  forward_scheme,
  enabled,
  locations,
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
)
SELECT
  datetime('now'),
  datetime('now'),
  owner_user_id,
  0,
  '["wizarr.rafael.media"]',
  '192.168.0.112',
  5690,
  0,
  certificate_id,
  1,
  0,
  1,
  'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_read_timeout 300s;
proxy_send_timeout 300s;',
  meta,
  1,
  1,
  'http',
  1,
  '[]',
  hsts_enabled,
  hsts_subdomains,
  trust_forwarded_proto
FROM proxy_host
WHERE domain_names = '["mealie.rafael.media"]'
  AND is_deleted = 0
  AND NOT EXISTS (
    SELECT 1
    FROM proxy_host
    WHERE domain_names = '["wizarr.rafael.media"]'
  )
LIMIT 1;

COMMIT;

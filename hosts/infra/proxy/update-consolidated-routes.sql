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
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = '192.168.0.112',
    forward_port = 8096,
    access_list_id = 0,
    ssl_forced = 1,
    allow_websocket_upgrade = 1,
    modified_on = datetime('now')
WHERE domain_names = '["stream.rafael.ink"]';

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

UPDATE proxy_host
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = '192.168.0.112',
    forward_port = 5690,
    access_list_id = 0,
    certificate_id = (
      SELECT template.certificate_id
      FROM proxy_host AS template
      WHERE template.domain_names = '["stream.rafael.ink"]'
        AND template.is_deleted = 0
      LIMIT 1
    ),
    ssl_forced = 1,
    caching_enabled = 0,
    block_exploits = 1,
    allow_websocket_upgrade = 1,
    http2_support = 1,
    advanced_config = 'proxy_read_timeout 300s;
proxy_send_timeout 300s;',
    modified_on = datetime('now')
WHERE domain_names = '["join-stream.rafael.ink"]';

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
  template.owner_user_id,
  0,
  '["join-stream.rafael.ink"]',
  '192.168.0.112',
  5690,
  0,
  template.certificate_id,
  1,
  0,
  1,
  'proxy_read_timeout 300s;
proxy_send_timeout 300s;',
  template.meta,
  1,
  1,
  'http',
  1,
  '[]',
  template.hsts_enabled,
  template.hsts_subdomains,
  template.trust_forwarded_proto
FROM proxy_host AS template
WHERE template.domain_names = '["stream.rafael.ink"]'
  AND template.is_deleted = 0
  AND NOT EXISTS (
    SELECT 1
    FROM proxy_host
    WHERE domain_names = '["join-stream.rafael.ink"]'
  )
LIMIT 1;

CREATE TEMP TABLE dothomelab_new_proxy_routes (
  domain_names TEXT PRIMARY KEY,
  forward_host TEXT NOT NULL DEFAULT '192.168.0.112',
  forward_port INTEGER NOT NULL,
  advanced_config TEXT NOT NULL
);

INSERT INTO dothomelab_new_proxy_routes (
  domain_names,
  forward_port,
  advanced_config
)
VALUES
  (
    '["bar.rafael.media"]',
    8200,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;'
  ),
  (
    '["bar-api.rafael.media"]',
    8201,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 64m;
proxy_request_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;'
  ),
  (
    '["bar-search.rafael.media"]',
    8202,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 64m;
proxy_request_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;'
  ),
  (
    '["yt-dlp.rafael.media"]',
    3033,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_buffering off;
proxy_read_timeout 900s;
proxy_send_timeout 900s;'
  ),
  (
    '["snapotter.rafael.media"]',
    1349,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 500m;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;'
  ),
  (
    '["pdf.rafael.media"]',
    8084,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 500m;
proxy_request_buffering off;
proxy_read_timeout 600s;
proxy_send_timeout 600s;'
  ),
  (
    '["slskd.rafael.media"]',
    5030,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 0;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 900s;
proxy_send_timeout 900s;'
  ),
  (
    '["aurral.rafael.media"]',
    3001,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 64m;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 900s;
proxy_send_timeout 900s;'
  ),
  (
    '["navidrome.rafael.media"]',
    4533,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_buffering off;
proxy_read_timeout 900s;
proxy_send_timeout 900s;'
  ),
  (
    '["audiobookshelf.rafael.media"]',
    13378,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 10240m;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;'
  ),
  (
    '["kavita.rafael.media"]',
    5000,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 512m;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 600s;
proxy_send_timeout 600s;'
  ),
  (
    '["bookorbit.rafael.media"]',
    3002,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 512m;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 600s;
proxy_send_timeout 600s;'
  ),
  (
    '["grimmory.rafael.media"]',
    6060,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 10240m;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;'
  ),
  (
    '["storyteller.rafael.media"]',
    8001,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 10240m;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;'
  ),
  (
    '["pinepods.rafael.media"]',
    8040,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 2048m;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;'
  );

INSERT INTO dothomelab_new_proxy_routes (
  domain_names,
  forward_host,
  forward_port,
  advanced_config
)
VALUES
  (
    '["n8n.rafael.media"]',
    '192.168.0.110',
    5678,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 0;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;'
  ),
  (
    '["pulse.rafael.media"]',
    '192.168.0.110',
    7655,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_buffering off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;'
  ),
  (
    '["shelfarr.rafael.media"]',
    '192.168.0.102',
    5056,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
client_max_body_size 2048m;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 900s;
proxy_send_timeout 900s;'
  ),
  (
    '["listenarr.rafael.media"]',
    '192.168.0.102',
    4545,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_buffering off;
proxy_read_timeout 900s;
proxy_send_timeout 900s;'
  ),
  (
    '["cleanuparr.rafael.media"]',
    '192.168.0.102',
    11011,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;'
  ),
  (
    '["sortarr.rafael.media"]',
    '192.168.0.102',
    9595,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_request_buffering off;
proxy_buffering off;
proxy_read_timeout 900s;
proxy_send_timeout 900s;'
  ),
  (
    '["syncthing.rafael.media"]',
    '127.0.0.1',
    8384,
    'allow 192.168.0.0/24;
allow 100.64.0.0/10;
deny all;
proxy_buffering off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;'
  );

UPDATE proxy_host
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = (
      SELECT route.forward_host
      FROM dothomelab_new_proxy_routes AS route
      WHERE route.domain_names = proxy_host.domain_names
    ),
    forward_port = (
      SELECT route.forward_port
      FROM dothomelab_new_proxy_routes AS route
      WHERE route.domain_names = proxy_host.domain_names
    ),
    access_list_id = 0,
    certificate_id = (
      SELECT template.certificate_id
      FROM proxy_host AS template
      WHERE template.domain_names = '["mealie.rafael.media"]'
        AND template.is_deleted = 0
      LIMIT 1
    ),
    ssl_forced = 1,
    caching_enabled = 0,
    block_exploits = 1,
    allow_websocket_upgrade = 1,
    http2_support = 1,
    advanced_config = (
      SELECT route.advanced_config
      FROM dothomelab_new_proxy_routes AS route
      WHERE route.domain_names = proxy_host.domain_names
    ),
    modified_on = datetime('now')
WHERE domain_names IN (
  SELECT domain_names
  FROM dothomelab_new_proxy_routes
);

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
  template.owner_user_id,
  0,
  route.domain_names,
  route.forward_host,
  route.forward_port,
  0,
  template.certificate_id,
  1,
  0,
  1,
  route.advanced_config,
  template.meta,
  1,
  1,
  'http',
  1,
  '[]',
  template.hsts_enabled,
  template.hsts_subdomains,
  template.trust_forwarded_proto
FROM dothomelab_new_proxy_routes AS route
CROSS JOIN (
  SELECT
    owner_user_id,
    certificate_id,
    meta,
    hsts_enabled,
    hsts_subdomains,
    trust_forwarded_proto
  FROM proxy_host
  WHERE domain_names = '["mealie.rafael.media"]'
    AND is_deleted = 0
  LIMIT 1
) AS template
WHERE NOT EXISTS (
  SELECT 1
  FROM proxy_host AS existing
  WHERE existing.domain_names = route.domain_names
);

DROP TABLE dothomelab_new_proxy_routes;

UPDATE proxy_host
SET enabled = 0,
    modified_on = datetime('now')
WHERE domain_names = '["droppedneedle.rafael.media"]';

COMMIT;

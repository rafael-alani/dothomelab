PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- Git-managed Homarr applications for private Apps services.

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlpaperlessngxapp000001',
  'Paperless-ngx',
  'Document management',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/paperless-ngx.svg',
  'https://paperless.rafael.media',
  'http://192.168.0.112:8002'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlpaperlessgptapp000001',
  'Paperless-GPT',
  'AI-assisted document processing',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/openai.svg',
  'https://paperless-gpt.rafael.media',
  'http://192.168.0.112:8003'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlprometheusapp000001',
  'Prometheus',
  'Metrics and time-series queries',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/prometheus.svg',
  'https://prometheus.rafael.media',
  'http://192.168.0.112:9090/-/ready'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhllokiapp000000000001',
  'Loki',
  'Private log ingestion and query API',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/loki.svg',
  'https://loki.rafael.media/ready',
  'http://192.168.0.112:3100/ready'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlimmichframeapp0000001',
  'ImmichFrame',
  'Digital photo frame for Immich',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/immich.svg',
  'https://immichframe.rafael.media',
  'http://192.168.0.112:8080'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlwizarrapp000000000001',
  'Wizarr',
  'Jellyfin invitations and onboarding',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/wizarr.svg',
  'https://wizarr.rafael.media',
  'http://192.168.0.112:5690'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlbarassistantapp000001',
  'Bar Assistant',
  'Cocktail recipes and home bar management',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/bar-assistant.svg',
  'https://bar.rafael.media',
  'http://192.168.0.112:8200'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlytdlpwebuiapp00000010',
  'yt-dlp Web UI',
  'Authenticated media download queue',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/yt-dlp.svg',
  'https://yt-dlp.rafael.media',
  'http://192.168.0.112:3033'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlsnapotterapp000000001',
  'SnapOtter',
  'Private file processing and local AI',
  'https://snapotter.rafael.media/favicon.ico',
  'https://snapotter.rafael.media',
  'http://192.168.0.112:1349/api/v1/health'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlstirlingpdfapp0000001',
  'Stirling-PDF',
  'Authenticated PDF editing and conversion',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/stirling-pdf.svg',
  'https://pdf.rafael.media',
  'http://192.168.0.112:8084/api/v1/info/status'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlslskdapp0000000000001',
  'slskd',
  'Private Soulseek client and Soularr download source',
  'https://slskd.rafael.media/favicon.ico',
  'https://slskd.rafael.media',
  'http://192.168.0.112:5030/health'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlaurralapp000000000001',
  'Aurral',
  'Private music discovery, requests, and flows',
  'https://aurral.rafael.media/favicon.ico',
  'https://aurral.rafael.media',
  'http://192.168.0.112:3001/api/health/live'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlaudiobookshelfapp0001',
  'Audiobookshelf',
  'Private audiobook and podcast server',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/audiobookshelf.svg',
  'https://audiobookshelf.rafael.media',
  'http://192.168.0.112:13378'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlkavitaapp000000000001',
  'Kavita',
  'Private books, comics, and manga reader',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/kavita.svg',
  'https://kavita.rafael.media',
  'http://192.168.0.112:5000/api/health'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhln8napp000000000000001',
  'n8n',
  'Private workflow automation',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/n8n.svg',
  'https://n8n.rafael.media',
  'http://192.168.0.110:5678/healthz'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlpulseapp000000000001',
  'Pulse',
  'Proxmox and Docker resource monitoring',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/pulse.svg',
  'https://pulse.rafael.media',
  'http://192.168.0.110:7655/api/health'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlsyncthingapp000000001',
  'Syncthing',
  'Private file synchronization and Obsidian receiver',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/syncthing.svg',
  'https://syncthing.rafael.media',
  'https://syncthing.rafael.media/rest/noauth/health'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlshelfarrapp00000000001',
  'Shelfarr',
  'Ebook and audiobook acquisition',
  'https://shelfarr.rafael.media/favicon.ico',
  'https://shelfarr.rafael.media',
  'http://192.168.0.102:5056/up'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlbookorbitapp000000001',
  'BookOrbit',
  'Private books, comics, and PDF reader',
  'https://bookorbit.rafael.media/favicon.ico',
  'https://bookorbit.rafael.media',
  'http://192.168.0.112:3002/api/v1/health'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlstorytellerapp000001',
  'Storyteller',
  'Paired ebook and audiobook readalouds',
  'https://storyteller.rafael.media/favicon.ico',
  'https://storyteller.rafael.media',
  'http://192.168.0.112:8001/api/health'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlpinepodsapp0000000000',
  'PinePods',
  'Private podcast subscriptions, downloads, and playback',
  'https://pinepods.rafael.media/favicon.ico',
  'https://pinepods.rafael.media',
  'http://192.168.0.112:8040/api/health'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

INSERT INTO app (id, name, description, icon_url, href, ping_url)
VALUES (
  'dhlnavidromeapp000000001',
  'Navidrome',
  'Private Subsonic music server',
  'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/navidrome.svg',
  'https://navidrome.rafael.media',
  'http://192.168.0.112:4533/ping'
)
ON CONFLICT(id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  icon_url = excluded.icon_url,
  href = excluded.href,
  ping_url = excluded.ping_url;

-- Replace the two pre-existing, split app definitions and their stale
-- homarr.dev/backend references with one deterministic app per service.
CREATE TEMP TABLE dothomelab_legacy_reader_apps AS
SELECT id, name
FROM app
WHERE name IN ('Audiobookshelf', 'Kavita')
  AND id NOT IN (
    'dhlaudiobookshelfapp0001',
    'dhlkavitaapp000000000001'
  );

UPDATE integration
SET app_id = CASE (
  SELECT legacy.name
  FROM dothomelab_legacy_reader_apps AS legacy
  WHERE legacy.id = integration.app_id
)
  WHEN 'Audiobookshelf' THEN 'dhlaudiobookshelfapp0001'
  WHEN 'Kavita' THEN 'dhlkavitaapp000000000001'
END
WHERE app_id IN (SELECT id FROM dothomelab_legacy_reader_apps);

DELETE FROM item_layout
WHERE item_id IN (
  SELECT item.id
  FROM item
  JOIN dothomelab_legacy_reader_apps AS legacy
    ON item.options LIKE '%' || legacy.id || '%'
);

DELETE FROM item
WHERE id IN (
  SELECT item.id
  FROM item
  JOIN dothomelab_legacy_reader_apps AS legacy
    ON item.options LIKE '%' || legacy.id || '%'
);

DELETE FROM app
WHERE id IN (SELECT id FROM dothomelab_legacy_reader_apps);

DROP TABLE dothomelab_legacy_reader_apps;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlpaperlessngxitemdash1',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlpaperlessngxapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlpaperlessgptitemdash1',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlpaperlessgptapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlpaperlessngxitemadm01',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlpaperlessngxapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlpaperlessgptitemadm01',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlpaperlessgptapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlpaperlessngxitemdef01',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlpaperlessngxapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlpaperlessgptitemdef01',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlpaperlessgptapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlprometheusitemdash1',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlprometheusapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhllokiitemdashboard001',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhllokiapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlprometheusitemadm01',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlprometheusapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhllokiitemadmin000001',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhllokiapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlprometheusitemdef01',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlprometheusapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhllokiitemdefault0001',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhllokiapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlimmichframeitemdash01',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlimmichframeapp0000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlwizarritemdashboard01',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlwizarrapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlimmichframeitemadm001',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlimmichframeapp0000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlwizarritemadmin000001',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlwizarrapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlimmichframeitemdef001',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlimmichframeapp0000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlwizarritemdefault0001',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlwizarrapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlbarassistantdash00001',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlbarassistantapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlbarassistantadmin0001',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlbarassistantapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlbarassistantdef000010',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlbarassistantapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlytdlpwebuidash0000010',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlytdlpwebuiapp00000010","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlytdlpwebuiadmin000010',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlytdlpwebuiapp00000010","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlytdlpwebuidef00000100',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlytdlpwebuiapp00000010","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlsnapotteritemdash0001',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlsnapotterapp000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlsnapotteritemadmin001',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlsnapotterapp000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlsnapotteritemdef00001',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlsnapotterapp000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlstirlingpdfitemdash01',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlstirlingpdfapp0000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlstirlingpdfitemadmin1',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlstirlingpdfapp0000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlstirlingpdfitemdef001',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlstirlingpdfapp0000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlslskditemdashboard001',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlslskdapp0000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlslskditemadmin0000001',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlslskdapp0000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlslskditemdefault00001',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlslskdapp0000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlaurralitemdashboard01',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlaurralapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlaurralitemadmin000001',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlaurralapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlaurralitemdefault0001',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlaurralapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlaudiobookitemdash0001',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlaudiobookshelfapp0001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlaudiobookitemadmin001',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlaudiobookshelfapp0001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlaudiobookitemdefault1',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlaudiobookshelfapp0001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlkavitaitemdash0000001',
  (SELECT id FROM board WHERE name = 'dashboard'),
  'app',
  '{"json":{"appId":"dhlkavitaapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlkavitaitemadmin000001',
  (SELECT id FROM board WHERE name = 'Admin'),
  'app',
  '{"json":{"appId":"dhlkavitaapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES (
  'dhlkavitaitemdefault0001',
  (SELECT id FROM board WHERE name = 'default'),
  'app',
  '{"json":{"appId":"dhlkavitaapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
  '{"json": {}}'
)
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

INSERT INTO item (id, board_id, kind, options, advanced_options)
VALUES
  (
    'dhln8nitemdashboard00001',
    (SELECT id FROM board WHERE name = 'dashboard'),
    'app',
    '{"json":{"appId":"dhln8napp000000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhln8nitemadmin00000001',
    (SELECT id FROM board WHERE name = 'Admin'),
    'app',
    '{"json":{"appId":"dhln8napp000000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhln8nitemdefault0000001',
    (SELECT id FROM board WHERE name = 'default'),
    'app',
    '{"json":{"appId":"dhln8napp000000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlpulseitemdashboard001',
    (SELECT id FROM board WHERE name = 'dashboard'),
    'app',
    '{"json":{"appId":"dhlpulseapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlpulseitemadmin0000001',
    (SELECT id FROM board WHERE name = 'Admin'),
    'app',
    '{"json":{"appId":"dhlpulseapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlpulseitemdefault00001',
    (SELECT id FROM board WHERE name = 'default'),
    'app',
    '{"json":{"appId":"dhlpulseapp000000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlsyncthingitemdash0001',
    (SELECT id FROM board WHERE name = 'dashboard'),
    'app',
    '{"json":{"appId":"dhlsyncthingapp000000001","openInNewTab":true,"pingEnabled":false,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlsyncthingitemadmin001',
    (SELECT id FROM board WHERE name = 'Admin'),
    'app',
    '{"json":{"appId":"dhlsyncthingapp000000001","openInNewTab":true,"pingEnabled":false,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlsyncthingitemdef00001',
    (SELECT id FROM board WHERE name = 'default'),
    'app',
    '{"json":{"appId":"dhlsyncthingapp000000001","openInNewTab":true,"pingEnabled":false,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlshelfarritemdash00001',
    (SELECT id FROM board WHERE name = 'dashboard'),
    'app',
    '{"json":{"appId":"dhlshelfarrapp00000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlshelfarritemadmin0001',
    (SELECT id FROM board WHERE name = 'Admin'),
    'app',
    '{"json":{"appId":"dhlshelfarrapp00000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlshelfarritemdef000001',
    (SELECT id FROM board WHERE name = 'default'),
    'app',
    '{"json":{"appId":"dhlshelfarrapp00000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlbookorbititemdash0001',
    (SELECT id FROM board WHERE name = 'dashboard'),
    'app',
    '{"json":{"appId":"dhlbookorbitapp000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlbookorbititemadmin001',
    (SELECT id FROM board WHERE name = 'Admin'),
    'app',
    '{"json":{"appId":"dhlbookorbitapp000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlbookorbititemdef00001',
    (SELECT id FROM board WHERE name = 'default'),
    'app',
    '{"json":{"appId":"dhlbookorbitapp000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlstorytelleritemdash01',
    (SELECT id FROM board WHERE name = 'dashboard'),
    'app',
    '{"json":{"appId":"dhlstorytellerapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlstorytelleritemadm001',
    (SELECT id FROM board WHERE name = 'Admin'),
    'app',
    '{"json":{"appId":"dhlstorytellerapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlstorytelleritemdef001',
    (SELECT id FROM board WHERE name = 'default'),
    'app',
    '{"json":{"appId":"dhlstorytellerapp000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlpinepodsitemdash00001',
    (SELECT id FROM board WHERE name = 'dashboard'),
    'app',
    '{"json":{"appId":"dhlpinepodsapp0000000000","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlpinepodsitemadmin0001',
    (SELECT id FROM board WHERE name = 'Admin'),
    'app',
    '{"json":{"appId":"dhlpinepodsapp0000000000","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlpinepodsitemdefault01',
    (SELECT id FROM board WHERE name = 'default'),
    'app',
    '{"json":{"appId":"dhlpinepodsapp0000000000","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlnavidromeitemdash001',
    (SELECT id FROM board WHERE name = 'dashboard'),
    'app',
    '{"json":{"appId":"dhlnavidromeapp000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlnavidromeitemadmin01',
    (SELECT id FROM board WHERE name = 'Admin'),
    'app',
    '{"json":{"appId":"dhlnavidromeapp000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  ),
  (
    'dhlnavidromeitemdefault1',
    (SELECT id FROM board WHERE name = 'default'),
    'app',
    '{"json":{"appId":"dhlnavidromeapp000000001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
    '{"json": {}}'
  )
ON CONFLICT(id) DO UPDATE SET
  board_id = excluded.board_id,
  kind = excluded.kind,
  options = excluded.options;

WITH managed_items(item_id, x_offset) AS (
  VALUES
    ('dhlpaperlessngxitemdash1', 0),
    ('dhlpaperlessgptitemdash1', 1),
    ('dhlprometheusitemdash1', 2),
    ('dhllokiitemdashboard001', 3),
    ('dhlimmichframeitemdash01', 4),
    ('dhlwizarritemdashboard01', 5),
    ('dhlbarassistantdash00001', 6),
    ('dhlytdlpwebuidash0000010', 7),
    ('dhlsnapotteritemdash0001', 8),
    ('dhlstirlingpdfitemdash01', 9),
    ('dhlslskditemdashboard001', 10),
    ('dhlaurralitemdashboard01', 11),
    ('dhlaudiobookitemdash0001', 12),
    ('dhlkavitaitemdash0000001', 13),
    ('dhln8nitemdashboard00001', 14),
    ('dhlpulseitemdashboard001', 15),
    ('dhlsyncthingitemdash0001', 16),
    ('dhlshelfarritemdash00001', 17),
    ('dhlbookorbititemdash0001', 18),
    ('dhlstorytelleritemdash01', 19),
    ('dhlpinepodsitemdash00001', 20),
    ('dhlnavidromeitemdash001', 21),
    ('dhlpaperlessngxitemadm01', 0),
    ('dhlpaperlessgptitemadm01', 1),
    ('dhlprometheusitemadm01', 2),
    ('dhllokiitemadmin000001', 3),
    ('dhlimmichframeitemadm001', 4),
    ('dhlwizarritemadmin000001', 5),
    ('dhlbarassistantadmin0001', 6),
    ('dhlytdlpwebuiadmin000010', 7),
    ('dhlsnapotteritemadmin001', 8),
    ('dhlstirlingpdfitemadmin1', 9),
    ('dhlslskditemadmin0000001', 10),
    ('dhlaurralitemadmin000001', 11),
    ('dhlaudiobookitemadmin001', 12),
    ('dhlkavitaitemadmin000001', 13),
    ('dhln8nitemadmin00000001', 14),
    ('dhlpulseitemadmin0000001', 15),
    ('dhlsyncthingitemadmin001', 16),
    ('dhlshelfarritemadmin0001', 17),
    ('dhlbookorbititemadmin001', 18),
    ('dhlstorytelleritemadm001', 19),
    ('dhlpinepodsitemadmin0001', 20),
    ('dhlnavidromeitemadmin01', 21),
    ('dhlpaperlessngxitemdef01', 0),
    ('dhlpaperlessgptitemdef01', 1),
    ('dhlprometheusitemdef01', 2),
    ('dhllokiitemdefault0001', 3),
    ('dhlimmichframeitemdef001', 4),
    ('dhlwizarritemdefault0001', 5),
    ('dhlbarassistantdef000010', 6),
    ('dhlytdlpwebuidef00000100', 7),
    ('dhlsnapotteritemdef00001', 8),
    ('dhlstirlingpdfitemdef001', 9),
    ('dhlslskditemdefault00001', 10),
    ('dhlaurralitemdefault0001', 11),
    ('dhlaudiobookitemdefault1', 12),
    ('dhlkavitaitemdefault0001', 13),
    ('dhln8nitemdefault0000001', 14),
    ('dhlpulseitemdefault00001', 15),
    ('dhlsyncthingitemdef00001', 16),
    ('dhlshelfarritemdef000001', 17),
    ('dhlbookorbititemdef00001', 18),
    ('dhlstorytelleritemdef001', 19),
    ('dhlpinepodsitemdefault01', 20),
    ('dhlnavidromeitemdefault1', 21)
),
placements AS (
  SELECT
    managed_items.item_id,
    coalesce(
      (
        SELECT current_placement.section_id
        FROM item_layout AS current_placement
        JOIN section AS current_section
          ON current_section.id = current_placement.section_id
        WHERE current_placement.item_id = managed_items.item_id
          AND current_placement.layout_id = layout.id
          AND current_section.board_id = board.id
        ORDER BY current_placement.section_id
        LIMIT 1
      ),
      (
        SELECT candidate.id
        FROM section AS candidate
        WHERE candidate.board_id = board.id
        ORDER BY candidate.id
        LIMIT 1
      )
    ) AS section_id,
    layout.id AS layout_id,
    managed_items.x_offset,
    coalesce(
      (
        SELECT max(existing.y_offset + existing.height)
        FROM item_layout AS existing
        WHERE existing.layout_id = layout.id
          AND existing.item_id NOT IN (
            'dhlpaperlessngxitemdash1',
            'dhlpaperlessgptitemdash1',
            'dhlpaperlessngxitemadm01',
            'dhlpaperlessgptitemadm01',
            'dhlpaperlessngxitemdef01',
            'dhlpaperlessgptitemdef01',
            'dhlprometheusitemdash1',
            'dhllokiitemdashboard001',
            'dhlprometheusitemadm01',
            'dhllokiitemadmin000001',
            'dhlprometheusitemdef01',
            'dhllokiitemdefault0001',
            'dhlimmichframeitemdash01',
            'dhlwizarritemdashboard01',
            'dhlimmichframeitemadm001',
            'dhlwizarritemadmin000001',
            'dhlimmichframeitemdef001',
            'dhlwizarritemdefault0001',
            'dhlbarassistantdash00001',
            'dhlbarassistantadmin0001',
            'dhlbarassistantdef000010',
            'dhlytdlpwebuidash0000010',
            'dhlytdlpwebuiadmin000010',
            'dhlytdlpwebuidef00000100',
            'dhlsnapotteritemdash0001',
            'dhlsnapotteritemadmin001',
            'dhlsnapotteritemdef00001',
            'dhlstirlingpdfitemdash01',
            'dhlstirlingpdfitemadmin1',
            'dhlstirlingpdfitemdef001',
            'dhlslskditemdashboard001',
            'dhlslskditemadmin0000001',
            'dhlslskditemdefault00001',
            'dhlaurralitemdashboard01',
            'dhlaurralitemadmin000001',
            'dhlaurralitemdefault0001',
            'dhlaudiobookitemdash0001',
            'dhlaudiobookitemadmin001',
            'dhlaudiobookitemdefault1',
            'dhlkavitaitemdash0000001',
            'dhlkavitaitemadmin000001',
            'dhlkavitaitemdefault0001',
            'dhln8nitemdashboard00001',
            'dhln8nitemadmin00000001',
            'dhln8nitemdefault0000001',
            'dhlpulseitemdashboard001',
            'dhlpulseitemadmin0000001',
            'dhlpulseitemdefault00001',
            'dhlsyncthingitemdash0001',
            'dhlsyncthingitemadmin001',
            'dhlsyncthingitemdef00001',
            'dhlshelfarritemdash00001',
            'dhlshelfarritemadmin0001',
            'dhlshelfarritemdef000001',
            'dhlbookorbititemdash0001',
            'dhlbookorbititemadmin001',
            'dhlbookorbititemdef00001',
            'dhlstorytelleritemdash01',
            'dhlstorytelleritemadm001',
            'dhlstorytelleritemdef001',
            'dhlpinepodsitemdash00001',
            'dhlpinepodsitemadmin0001',
            'dhlpinepodsitemdefault01',
            'dhlnavidromeitemdash001',
            'dhlnavidromeitemadmin01',
            'dhlnavidromeitemdefault1'
          )
      ),
      0
    ) AS y_offset
  FROM managed_items
  JOIN item ON item.id = managed_items.item_id
  JOIN board ON board.id = item.board_id
  JOIN layout ON layout.board_id = board.id
)
INSERT OR IGNORE INTO item_layout (
  item_id,
  section_id,
  layout_id,
  x_offset,
  y_offset,
  width,
  height
)
SELECT
  item_id,
  section_id,
  layout_id,
  x_offset,
  y_offset,
  1,
  1
FROM placements;

COMMIT;

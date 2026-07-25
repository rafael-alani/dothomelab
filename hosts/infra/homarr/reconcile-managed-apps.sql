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
    ('dhlpaperlessngxitemdef01', 0),
    ('dhlpaperlessgptitemdef01', 1),
    ('dhlprometheusitemdef01', 2),
    ('dhllokiitemdefault0001', 3),
    ('dhlimmichframeitemdef001', 4),
    ('dhlwizarritemdefault0001', 5),
    ('dhlbarassistantdef000010', 6),
    ('dhlytdlpwebuidef00000100', 7),
    ('dhlsnapotteritemdef00001', 8),
    ('dhlstirlingpdfitemdef001', 9)
),
placements AS (
  SELECT
    managed_items.item_id,
    section.id AS section_id,
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
            'dhlstirlingpdfitemdef001'
          )
      ),
      0
    ) AS y_offset
  FROM managed_items
  JOIN item ON item.id = managed_items.item_id
  JOIN board ON board.id = item.board_id
  JOIN layout ON layout.board_id = board.id
  JOIN section ON section.id = (
    SELECT candidate.id
    FROM section AS candidate
    WHERE candidate.board_id = board.id
    ORDER BY candidate.id
    LIMIT 1
  )
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

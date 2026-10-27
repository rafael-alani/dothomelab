PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- Refuse to take over a user-created board or change an existing public board.
CREATE TEMP TABLE production_guard (valid INTEGER CHECK(valid = 1));
INSERT INTO production_guard SELECT NOT EXISTS (
  SELECT 1 FROM board WHERE lower(name) = 'production' AND id != 'dhlproductionboard00001'
);
INSERT INTO production_guard SELECT NOT EXISTS (
  SELECT 1 FROM board WHERE id = 'dhlproductionboard00001' AND (name != 'Production' OR is_public != 0)
);
INSERT INTO production_guard SELECT EXISTS (
  SELECT 1 FROM groupMember JOIN "group" ON "group".id = groupMember.group_id
  WHERE "group".name = 'credentials-admin'
);

INSERT INTO board(id, name, is_public, creator_id, page_title, meta_title, primary_color, secondary_color)
SELECT 'dhlproductionboard00001', 'Production', 0, user_id, 'Production', 'Production · Homarr', '#087f5b', '#1098ad'
FROM groupMember JOIN "group" ON "group".id = groupMember.group_id
WHERE "group".name = 'credentials-admin' ORDER BY user_id LIMIT 1
ON CONFLICT(id) DO NOTHING;

INSERT INTO app(id, name, description, icon_url, href, ping_url)
VALUES ('dhlproductionblogapp001', 'Blog', 'The Night Archive — production',
        'https://rafael.ink/favicon.svg',
        'https://rafael.ink', 'https://rafael.ink')
ON CONFLICT(id) DO UPDATE SET name=excluded.name, description=excluded.description,
  icon_url=excluded.icon_url, href=excluded.href, ping_url=excluded.ping_url;

INSERT INTO section(id, board_id, kind, x_offset, y_offset, options)
VALUES ('dhlproductionroot00001', 'dhlproductionboard00001', 'empty', 0, 0, '{"json":{}}')
ON CONFLICT(id) DO NOTHING;

INSERT INTO layout(id, name, board_id, column_count, breakpoint, role)
VALUES ('dhlproductiondesktop01', 'Desktop', 'dhlproductionboard00001', 8, 1080, 'base'),
       ('dhlproductioncompact01', 'Compact', 'dhlproductionboard00001', 6, 720, 'custom'),
       ('dhlproductionmobile001', 'Mobile', 'dhlproductionboard00001', 4, 0, 'mobile')
ON CONFLICT(id) DO NOTHING;

INSERT INTO item(id, board_id, kind, options, advanced_options)
VALUES ('dhlproductionblogitem01', 'dhlproductionboard00001', 'app',
        '{"json":{"appId":"dhlproductionblogapp001","openInNewTab":true,"pingEnabled":true,"showTitle":true,"layout":"column","descriptionDisplayMode":"tooltip"}}',
        '{"json":{}}')
ON CONFLICT(id) DO UPDATE SET options=excluded.options;

INSERT INTO item_layout(item_id, section_id, layout_id, x_offset, y_offset, width, height)
SELECT 'dhlproductionblogitem01', 'dhlproductionroot00001', id, 0, 0, 2, 2
FROM layout WHERE id IN ('dhlproductiondesktop01', 'dhlproductioncompact01', 'dhlproductionmobile001')
ON CONFLICT(item_id, section_id, layout_id) DO NOTHING;

DROP TABLE production_guard;
COMMIT;

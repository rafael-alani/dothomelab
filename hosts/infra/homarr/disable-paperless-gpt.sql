PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;
-- Remove only this optional service's tiles; retain its durable appdata.
DELETE FROM item_layout WHERE item_id IN (
  SELECT id FROM item WHERE json_extract(options, '$.json.appId') = 'dhlpaperlessgptapp000001'
);
DELETE FROM item WHERE json_extract(options, '$.json.appId') = 'dhlpaperlessgptapp000001';
UPDATE integration SET app_id = NULL WHERE app_id = 'dhlpaperlessgptapp000001';
DELETE FROM app WHERE id = 'dhlpaperlessgptapp000001';
COMMIT;

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;
-- Observed legacy IDs; preserve unrelated apps, widgets and telemetry.
DELETE FROM integration
WHERE id IN ('g7c95ortn1f3l5nyxganvyd2', 'oxsgjw79kfzj5c4wxf4hus2o')
  AND lower(name) = 'readarr';
DELETE FROM item
WHERE json_extract(options, '$.json.appId') = 'm8rb0y1fm0ze7d9lvbspeg8u';
DELETE FROM app
WHERE id = 'm8rb0y1fm0ze7d9lvbspeg8u' AND lower(name) = 'readarr';
COMMIT;

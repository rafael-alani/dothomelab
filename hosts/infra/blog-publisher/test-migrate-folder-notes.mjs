import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, readdir, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import matter from 'gray-matter';
import { migrateFolderNotes } from './migrate-folder-notes.mjs';

test('migration verifies originals, combines metadata/body, removes Waypoint index links, and is idempotent', async () => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'folder-migration-'));
  try {
    const root = path.join(temporary, 'Blog'), folder = path.join(root, 'photos'), backupRoot = path.join(temporary, 'backup');
    await mkdir(folder, { recursive: true });
    const original = '---\nid: stable-folder\norder: 4\nkind: gallery\nstatus: draft\n---\n---\n[[photo.jpg]]\n---\n';
    await writeFile(path.join(folder, '_index.md'), original);
    await writeFile(path.join(folder, 'photos.md'), '%% Begin Waypoint %%\n- [_index](./_index.md)\n%% End Waypoint %%');
    assert.equal((await migrateFolderNotes(root)).folders, 1);
    await migrateFolderNotes(root, { apply: true, backupRoot });
    const result = await readFile(path.join(folder, 'photos.md'), 'utf8');
    assert.deepEqual(matter(result).data.status, 'draft');
    assert.match(result, /Begin Waypoint/);
    assert.match(result, /\[\[photo.jpg\]\]/);
    assert.doesNotMatch(result, /_index/);
    assert.equal(await readFile(path.join(backupRoot, 'photos/_index.md'), 'utf8'), original);
    assert.deepEqual(await readdir(folder), ['photos.md']);
    assert.equal((await migrateFolderNotes(root, { apply: true, backupRoot })).folders, 0);
  } finally { await rm(temporary, { recursive: true, force: true }); }
});

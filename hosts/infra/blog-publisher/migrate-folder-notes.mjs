#!/usr/bin/env node
// Move taxonomy into Obsidian folder notes, retaining byte-verified originals.
import { readdir, readFile, writeFile, mkdir, lstat, unlink, realpath } from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import matter from 'gray-matter';

const digest = value => createHash('sha256').update(value).digest('hex');
const withoutWaypoint = value => value.replace(/%% Begin Waypoint %%[\s\S]*?%% End Waypoint %%/g, '').trim();

export async function migrateFolderNotes(root, { apply = false, backupRoot, preferFolderBody = [] } = {}) {
  root = await realpath(root);
  const plans = [];
  async function scan(directory) {
    const children = await readdir(directory, { withFileTypes: true });
    if (children.some(child => child.isSymbolicLink())) throw new Error('Refusing a symlink in the authoring tree');
    if (children.some(child => child.name === '_index.md')) {
      const source = path.join(directory, '_index.md');
      const target = path.join(directory, path.basename(directory) + '.md');
      const before = await readFile(source, 'utf8');
      let existing = null;
      try { existing = await readFile(target, 'utf8'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
      const index = matter(before), note = matter(existing ?? '');
      if (note.data.id && index.data.id && note.data.id !== index.data.id) throw new Error(`Conflicting identities: ${path.relative(root, target)}`);
      const first = withoutWaypoint(index.content), second = withoutWaypoint(note.content);
      const folder = path.relative(root, directory);
      if (first && second && first !== second && !preferFolderBody.includes(folder)) throw new Error(`Both notes contain prose: ${folder}; choose the retained body explicitly`);
      const body = second || first;
      const data = { ...index.data, ...note.data };
      const modified = (await lstat(source)).mtime.toISOString().slice(0, 10);
      if (body) {
        data.publishedAt ??= modified;
        data.status ??= folder === 'about' && !data.draft ? 'published' : 'draft';
      }
      data.lastEditedAt ??= '';
      const waypoint = (note.content.match(/%% Begin Waypoint %%[\s\S]*?%% End Waypoint %%/)?.[0] ?? '%% Begin Waypoint %%\n%% End Waypoint %%')
        .replace(/^.*\[(?:_index)\].*\n?/gm, '');
      const after = matter.stringify(`\n${waypoint}\n\n${body}\n`, data).trimEnd() + "\n";
      plans.push({ source, target, before, existing, after });
    }
    for (const child of children.filter(child => child.isDirectory() && !child.name.startsWith('.'))) await scan(path.join(directory, child.name));
  }
  await scan(root);
  if (!apply || !plans.length) return { folders: plans.length, applied: false };
  if (!backupRoot) throw new Error('An explicit backup directory is required');
  await mkdir(backupRoot, { recursive: true, mode: 0o700 });
  const manifest = [];
  for (const plan of plans) {
    for (const [file, value] of [[plan.source, plan.before], [plan.target, plan.existing]]) {
      if (value === null) continue;
      const relative = path.relative(root, file);
      const saved = path.join(backupRoot, relative);
      await mkdir(path.dirname(saved), { recursive: true, mode: 0o700 });
      await writeFile(saved, value, { flag: 'wx', mode: 0o600 });
      if (digest(await readFile(saved)) !== digest(value)) throw new Error('Backup verification failed');
    }
    manifest.push({ source: path.relative(root, plan.source), target: path.relative(root, plan.target), existed: plan.existing !== null,
      sourceHash: digest(plan.before), previousTargetHash: plan.existing === null ? null : digest(plan.existing), migratedHash: digest(plan.after) });
  }
  await writeFile(path.join(backupRoot, 'migration.json'), JSON.stringify({ root, files: manifest }, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
  // Verify all source files again before the first mutation.
  for (const plan of plans) {
    if (await readFile(plan.source, 'utf8') !== plan.before) throw new Error('Concurrent index edit; rerun migration');
    let current = null;
    try { current = await readFile(plan.target, 'utf8'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (current !== plan.existing) throw new Error('Concurrent folder-note edit; rerun migration');
  }
  for (const plan of plans) {
    await writeFile(plan.target, plan.after);
    if (await readFile(plan.target, 'utf8') !== plan.after) throw new Error('Folder-note verification failed');
    await unlink(plan.source);
  }
  return { folders: plans.length, applied: true, backup: backupRoot };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2), root = args[0];
  if (!root) throw new Error('Usage: migrate-folder-notes.mjs ROOT [--apply --backup DIRECTORY] [--prefer-folder-body RELATIVE_FOLDER]');
  const option = name => args[args.indexOf(name) + 1];
  console.log(JSON.stringify(await migrateFolderNotes(root, { apply: args.includes('--apply'),
    backupRoot: args.includes('--backup') ? option('--backup') : undefined,
    preferFolderBody: args.includes('--prefer-folder-body') ? [option('--prefer-folder-body')] : [] })));
}

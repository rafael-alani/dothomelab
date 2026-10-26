// Preserve the exact PDF selection from the existing course exports when bare
// names in the vault have multiple editions. Normal source notes stay untouched.
import { readFile, writeFile, readdir, mkdir, copyFile } from 'node:fs/promises';
import path from 'node:path';
import matter from 'gray-matter';
const [vault, repo] = process.argv.slice(2);
if (!vault || !repo) throw new Error('Usage: node migrate-map-links.mjs VAULT BLOG_REPOSITORY');
async function files(root, prefix='') {
  const found=[];
  for(const item of await readdir(path.join(root,prefix),{withFileTypes:true})) {
    if(item.name.startsWith('.'))continue;
    const name=path.posix.join(prefix,item.name);
    if(item.isDirectory())found.push(...await files(root,name));
    else if(item.isFile())found.push(name);
  }
  return found;
}
const vaultFiles=await files(vault);
const configs=JSON.parse(await readFile(path.join(repo,'content/obsidian/collections.json')));
const backup=path.join(vault,'.blog-publisher-backups','map-links-'+new Date().toISOString().replaceAll(':','-'));
let changed=0;
for(const config of configs) {
  const exported=await files(path.join(repo,'content/obsidian',config.directory));
  const links={};
  for(const file of exported.filter(file=>file.toLowerCase().endsWith('.pdf'))) {
    const basename=path.posix.basename(file);
    if(vaultFiles.includes(file) && vaultFiles.filter(name=>path.posix.basename(name)===basename).length>1 &&
       exported.filter(name=>path.posix.basename(name)===basename).length===1) links[basename]=file;
  }
  for (const note of exported.filter(file => file.endsWith('.md'))) {
    const body = await readFile(path.join(repo,'content/obsidian',config.directory,note),'utf8');
    const byName = new Map();
    for (const match of body.matchAll(/\[\[([^\]|]+\.pdf)(#[^\]|]*)?(?:\|[^\]]*)?\]\]/gi)) {
      const target = match[1], basename = path.posix.basename(target);
      if (!target.includes('/') || !vaultFiles.includes(target) || vaultFiles.filter(name => path.posix.basename(name) === basename).length < 2) continue;
      const entries = byName.get(basename) ?? [];
      entries.push({target,fragment:match[2]??''}); byName.set(basename,entries);
    }
    for (const [basename, entries] of byName) {
      if (new Set(entries.map(e=>e.target)).size===1) links[note+'::'+basename]=entries[0].target;
      else for (const entry of entries) links[note+'::'+basename+entry.fragment]=entry.target;
    }
  }
  if(!Object.keys(links).length)continue;
  const name=path.join('Blog',path.dirname(config.articleUrl),config.title.replaceAll('/','-')+'.md');
  const target=path.join(vault,name), original=await readFile(target,'utf8');
  const parsed=matter(original);
  parsed.data['map-links']={...links,...parsed.data['map-links']};
  const updated=matter.stringify(parsed.content,parsed.data);
  if(updated===original)continue;
  await mkdir(path.dirname(path.join(backup,name)),{recursive:true});
  await copyFile(target,path.join(backup,name));
  await writeFile(target,updated);changed++;
}
console.log(JSON.stringify({changed,backup}));

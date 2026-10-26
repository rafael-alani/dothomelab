// Disposable, uniquely named vault probe. Remove only exact files this command created.
import { mkdir, readFile, writeFile, unlink, rmdir } from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
const [action, vault] = process.argv.slice(2);
if (!['create', 'edit', 'cleanup'].includes(action) || !vault) throw new Error('Usage: node check-live-sync.mjs create|edit|cleanup VAULT');
const root = path.join(vault, '.blog-publisher-backups/live-sync-111-113');
const marker = path.join(root, 'files.json');
const article = 'Blog/work-and-nerdy/ai-technical-write-ups/Live sync check 111-113.md';
const map = 'Blog sync probe 111-113/Map.md';
const note = 'Blog sync probe 111-113/one/two/three/four/five/Deep note.md';
const digest = value => createHash('sha256').update(value).digest('hex');
if (action === 'create') {
  const element = {id:'live-sync-card', type:'embeddable', x:0,y:0,width:500,height:400,angle:0,strokeColor:'#000000',backgroundColor:'#ffffff',fillStyle:'solid',strokeWidth:1,strokeStyle:'solid',roughness:0,opacity:100,groupIds:[],frameId:null,roundness:null,seed:1,version:1,versionNonce:1,isDeleted:false,boundElements:null,updated:1,link:`[[${note}]]`,locked:false};
  const files = {
    [article]: `---\nid: 2f845a41-8916-4b76-8174-b87f198f097e\nurl: /work-and-nerdy/ai-technical-write-ups/live-sync-check-111-113\npublishedAt: '2026-10-26'\nstatus: draft\ndescription: Temporary end-to-end synchronization acceptance probe.\nmap-id: live-sync-check-111-113\n---\n![[${map}]]\n`,
    [map]: '---\nexcalidraw-plugin: parsed\n---\n```json\n' + JSON.stringify({type:'excalidraw',version:2,elements:[element],appState:{viewBackgroundColor:'#ffffff'},files:{}}) + '\n```\n',
    [note]: 'Live synchronization probe: initial content.\n',
  };
  for (const name of Object.keys(files)) {
    try { await readFile(path.join(vault,name)); throw new Error('Probe path already exists'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  await mkdir(root,{recursive:true});
  for (const [name,bytes] of Object.entries(files)) {await mkdir(path.dirname(path.join(vault,name)),{recursive:true});await writeFile(path.join(vault,name),bytes,{flag:'wx'});}
  await writeFile(marker,JSON.stringify(Object.fromEntries(Object.entries(files).map(([name,bytes])=>[name,digest(bytes)])),null,2));
} else {
  const files = JSON.parse(await readFile(marker,'utf8'));
  for (const [name,hash] of Object.entries(files)) if (digest(await readFile(path.join(vault,name))) !== hash) throw new Error('Probe was edited externally; preserve it');
  if (action === 'edit') {
    const bytes='Live synchronization probe: updated through Syncthing at depth five. '+new Date().toISOString()+'\n';
    await writeFile(path.join(vault,note),bytes); files[note]=digest(bytes);
    await writeFile(marker,JSON.stringify(files,null,2));
  } else {
    for (const name of Object.keys(files)) await unlink(path.join(vault,name));
    let directory=path.dirname(path.join(vault,note));
    while(directory.startsWith(path.join(vault,'Blog sync probe 111-113'))) {
      try {await rmdir(directory);} catch(error) {if(error.code!=='ENOTEMPTY')throw error;break;}
      directory=path.dirname(directory);
    }
  }
}
console.log(JSON.stringify({action,article:'/work-and-nerdy/ai-technical-write-ups/live-sync-check-111-113',manifest:marker}));

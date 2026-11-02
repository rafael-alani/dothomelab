#!/usr/bin/env node
// One-time private example installation. Source refreshes never invoke this.
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {playerBlock, range} = require('./obsidian/model.cjs');
const [vault, archive, assetId, seconds] = process.argv.slice(2);
if (!vault || !archive || !assetId || !seconds) throw new Error('Pass vault, archive, selected asset ID and observed duration');
const duration = Number(seconds);
range(0, duration, duration);
if (duration < 15) throw new Error('Choose a video at least 15 seconds long');
const catalog = JSON.parse(fs.readFileSync(path.join(vault, 'References/Catalog.json')));
const asset = catalog.assets.find(a => a.id === assetId);
if (!asset || !asset.path.endsWith('.mp4')) throw new Error('Selected video is not in the archive catalog');
const prefix = 'References/Projects';
fs.mkdirSync(path.join(vault, prefix), {recursive:true});
function note(name, text) {
  const relative = prefix + '/' + name + '.md';
  fs.writeFileSync(path.join(vault, relative), '---\nprivate: true\n---\n\n# ' + name + '\n\n' + text, {flag:'wx'});
  return relative;
}
function video(name, start, end, loop=false) {
  return note(name, playerBlock({asset:{id:asset.id,path:asset.path,title:asset.title},start,end,loop}, pathToFileURL(path.join(archive,asset.path)).href) + '\n\nMy annotation: this excerpt belongs to this project.\n');
}
function drawing(name, cards) {
  const scene = {type:'excalidraw',version:2,source:'https://github.com/zsviczian/obsidian-excalidraw-plugin',files:{},appState:{viewBackgroundColor:'#ffffff',gridSize:null},
    elements:cards.map((file,i)=>({id:'reference'+i,type:'embeddable',x:(i%3)*500,y:Math.floor(i/3)*460,width:460,height:420,angle:0,
      strokeColor:'#1e1e1e',backgroundColor:'transparent',fillStyle:'solid',strokeWidth:1,strokeStyle:'solid',roughness:0,opacity:100,
      groupIds:[],frameId:null,roundness:null,seed:i+1,version:1,versionNonce:i+1,isDeleted:false,boundElements:null,updated:0,
      link:'[['+file+']]',locked:false,customData:{referenceNote:file}}))};
  const relative='References/'+name+'.excalidraw.md';
  fs.writeFileSync(path.join(vault,relative),'---\nprivate: true\nexcalidraw-plugin: parsed\n---\n\n# Excalidraw Data\n## Text Elements\n\n%%\n## Drawing\n```json\n'+JSON.stringify(scene,null,2)+'\n```\n%%\n',{flag:'wx'});
  return relative;
}
const cards=[video('Motion study — full video',0,duration),video('Motion study — excerpt A',2,6),video('Motion study — excerpt B',10,14)];
const thumbnail='References/Thumbnails/'+asset.id+'.jpg';
if (fs.existsSync(path.join(vault,thumbnail))) cards.push(note('Motion study — first frame','![['+thumbnail+']]\n\nFrame at 0 seconds from the archived original. Use the excerpt command to capture a different instant.\n'));
const origin=catalog.items.find(i=>i.source==='yaay' && i.metadata.places?.some(p=>p.country?.toLowerCase()==='china' && p.latitude!=null && p.longitude!=null));
if (origin) {
  const place=origin.metadata.places.find(p=>p.country?.toLowerCase()==='china' && p.latitude!=null && p.longitude!=null);
  const url=place.map_url || 'https://www.openstreetmap.org/?mlat='+place.latitude+'&mlon='+place.longitude;
  cards.push(note('China — itinerary stop','## '+place.title+'\n\n[Open map](<'+url+'>)\n\nPlace provenance: Yaay saved-item location; not inferred from the motion-study video.\n\n[Original source](<'+origin.url+'>)\n\nMy itinerary notes:\n'));
}
cards.push(note('Reference boards — how to use','Open the command palette and choose **Reference Boards: Add a reference to this board**. Search by title or collection.\n\nUse **Choose excerpt or capture frame on this board** to adjust start, end, loop or capture a still. Each card owns its excerpt.\n\nVideos stay on the read-only Media archive. Click a player to start; starting another pauses it.\n\n[[References/Archive|Browse collections and import status]]\n\n[[References/Second project.excalidraw|Open the independent second project]]\n'));
console.log(drawing('Start here — reference board',cards));
console.log(drawing('Second project',[video('Second project — independent loop',6,9,true)]));

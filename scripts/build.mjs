// Build a static web bundle with the documents linked by the application.
import { cp, mkdir, rm, readdir, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
const root = fileURLToPath(new URL('../', import.meta.url));
const dist = resolve(root, 'dist');
await rm(dist, { recursive:true, force:true });
await mkdir(dist, { recursive:true });
await cp(resolve(root, 'web'), dist, { recursive:true });
await cp(resolve(root, 'docs'), resolve(dist, 'docs'), { recursive:true });
// A bundled snapshot keeps fitted medians and held-out evaluation on one trace hash.
for(const [source,target] of [['eta_bundle.json','eta-bundle.json'],['eta_bundle_5.json','eta-bundle-5.json'],['eta_bundle_7.json','eta-bundle-7.json']]){
  try { await cp(resolve(root,'evidence',source),resolve(dist,'replay',target)); }
  catch(error){if(error.code!=='ENOENT')throw error;}
}
async function count(folder) {
  let n=0;
  for (const name of await readdir(folder)) {
    const path=resolve(folder,name);
    n+=(await stat(path)).isDirectory()?await count(path):1;
  }
  return n;
}
console.log(`Static bundle ready: ${dist} (${await count(dist)} files)`);

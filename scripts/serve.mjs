// Local development only. Does not load keys or enable paid services.
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, extname, sep } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const web = resolve(root, 'web');
const port = Number(process.env.PORT || 4188);
const mime = { '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.css':'text/css; charset=utf-8', '.json':'application/json; charset=utf-8', '.jsonl':'application/x-ndjson; charset=utf-8', '.md':'text/plain; charset=utf-8', '.svg':'image/svg+xml' };
const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://127.0.0.1:${port}`);
    if (url.pathname.startsWith('/api/')) {
      const { handleRequest } = await import('../worker/src/core.js');
      const chunks = []; let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 32768) { res.writeHead(413).end('Request too large'); return; }
        chunks.push(chunk);
      }
      const request = new Request(url, {method:req.method,headers:req.headers,
        ...(req.method !== 'GET' && req.method !== 'HEAD' ? {body:Buffer.concat(chunks)} : {})});
      const env = {ASSETS:{async fetch(assetRequest){
        if (new URL(assetRequest.url).pathname !== '/replay/eta-bundle.json') return new Response('Not found',{status:404});
        try {return new Response(await readFile(resolve(root,'evidence/eta_bundle.json')), {headers:{'content-type':'application/json'}});}
        catch {return new Response('Not found',{status:404});}
      }}};
      const response = await handleRequest(request, env);
      res.writeHead(response.status, Object.fromEntries(response.headers));
      res.end(Buffer.from(await response.arrayBuffer()));
      return;
    }
    if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405).end(); return; }
    const pathname = decodeURIComponent(url.pathname);
    if (pathname === '/replay/eta-bundle.json') {
      const body = await readFile(resolve(root, 'evidence/eta_bundle.json'));
      res.writeHead(200, {'Content-Type':mime['.json'],'Cache-Control':'no-store'}).end(req.method === 'HEAD' ? '' : body);
      return;
    }
    const isDoc = pathname.startsWith('/docs/');
    const base = isDoc ? resolve(root, 'docs') : web;
    const relative = isDoc ? pathname.slice('/docs'.length) : pathname === '/' ? '/index.html' : pathname;
    const target = resolve(base, '.' + relative);
    if (!target.startsWith(base + sep) || target.split(sep).some(p=>p.startsWith('.'))) { res.writeHead(403).end(); return; }
    if (!(await stat(target)).isFile()) { res.writeHead(404).end(); return; }
    const body = await readFile(target);
    res.writeHead(200, {'Content-Type':mime[extname(target)] || 'application/octet-stream',
      'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin'});
    res.end(req.method === 'HEAD' ? '' : body);
  } catch (error) {
    if (error.code === 'ENOENT') res.writeHead(404).end('Not found');
    else res.writeHead(503, {'Content-Type':'application/json'}).end(JSON.stringify({mode:'replay-forced',model:null,usage:null,cost_usd:null,latency_ms:0,error:'Local API unavailable; use Replay.'}));
  }
});
server.listen(port, '127.0.0.1', () => console.log(`Last Sentence · Local: http://127.0.0.1:${port}`));
for (const signal of ['SIGINT','SIGTERM']) process.on(signal, () => server.close(() => process.exit(0)));

import { handleRequest } from './core.js';
export { UsageLimits } from './limits.js';

export default {
  async fetch(request, env, ctx) {
    const response = await handleRequest(request, env, { fetch: (url, init) => globalThis.fetch(url, init), cache: caches.default });
    if (response) return response;
    if (env.ASSETS) return env.ASSETS.fetch(request);
    return Response.json({ error: 'Not found' }, { status: 404 });
  },
};

import { expect, it } from 'vitest';
import { buildApp } from './server.js';
it('health endpoint', async () => {
  const app = await buildApp();
  const r = await app.inject('/health');
  expect(r.json()).toEqual({ status: 'ok' });
  await app.close();
});

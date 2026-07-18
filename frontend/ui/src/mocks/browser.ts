import { setupWorker } from 'msw/browser';

import { db } from './db';
import { handlers } from './handlers';

// Browser MSW worker — used ONLY for the Playwright E2E (gated behind VITE_E2E_MOCK in dev).
// Never bundled into a production build. Starts logged-out so the E2E drives the real login flow.
export async function startMockWorker(): Promise<void> {
  db.principal = null;
  const worker = setupWorker(...handlers);
  await worker.start({ onUnhandledRequest: 'bypass', quiet: true });
}

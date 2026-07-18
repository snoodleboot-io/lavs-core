import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from '@/app';

import '@/styles/tokens.css';

async function bootstrap(): Promise<void> {
  // E2E-only: intercept the API in-browser. The flag is unset in normal builds, so this
  // branch (and the mocks chunk) is dead-code-eliminated from production output.
  if (import.meta.env.VITE_E2E_MOCK === '1') {
    const { startMockWorker } = await import('@/mocks/browser');
    await startMockWorker();
  }

  const container = document.getElementById('root');
  if (!container) {
    throw new Error('Root element #root not found');
  }

  createRoot(container).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void bootstrap();

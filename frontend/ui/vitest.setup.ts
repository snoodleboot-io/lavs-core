import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';

import { resetDb } from '@/mocks/db';
import { server } from '@/mocks/server';

// Start the MSW mock API for the whole unit/component suite.
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  resetDb();
});

afterAll(() => {
  server.close();
});

// jsdom / Node 20 lack EventSource; provide an inert stub so components that open an SSE
// stream (useProductEvents) don't crash in tests. R3's own tests inject a FakeEventSource.
if (!('EventSource' in globalThis)) {
  class InertEventSource {
    readonly url: string;
    readonly withCredentials = false;
    readonly readyState = 0;
    constructor(url: string) {
      this.url = url;
    }
    addEventListener(): void {}
    removeEventListener(): void {}
    close(): void {}
    onopen: ((event: Event) => void) | null = null;
    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
  }
  (globalThis as { EventSource?: unknown }).EventSource = InertEventSource;
}

// jsdom lacks matchMedia; default to "no reduced-motion" so components render normally.
if (!window.matchMedia) {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    });
}

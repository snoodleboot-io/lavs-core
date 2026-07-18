import { setupServer } from 'msw/node';

import { handlers } from './handlers';

// The MSW server for the vitest (node) unit/component suite.
export const server = setupServer(...handlers);

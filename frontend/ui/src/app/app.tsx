import type { ReactNode } from 'react';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';

import { Providers } from './providers';
import { routes } from './routes';

const router = createBrowserRouter(routes);

/** Application root: cross-cutting providers wrapping the router. */
export function App(): ReactNode {
  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
}

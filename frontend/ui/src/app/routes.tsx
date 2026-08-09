import type { RouteObject } from 'react-router-dom';

import { ConstellationPage, LoginPage, NotFoundPage } from '@/pages';

import { RequireAuth } from './require-auth';

/** The route table. Foundation owns this so lanes slot pages in without conflicts. */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: (
      <RequireAuth>
        <ConstellationPage />
      </RequireAuth>
    ),
  },
  { path: '/login', element: <LoginPage /> },
  { path: '*', element: <NotFoundPage /> },
];

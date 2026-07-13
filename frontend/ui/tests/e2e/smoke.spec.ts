import { expect, test } from '@playwright/test';

// Trivial E2E to prove the toolchain (E7). The full login→scrub→cut→live flow is the
// Gate C ATDD spec, added once the lanes land and a seeded backend is running.
test('app boots and redirects an unauthenticated visitor to login', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('heading', { name: /LAVS/ })).toBeVisible();
});

import { expect, test } from '@playwright/test';

// The P5 exit criterion made executable: login → scrub → cut, driven in a real browser against
// the in-browser MSW API (VITE_E2E_MOCK). Live-SSE is covered by the R3 unit/integration tests.
test('login → scrub the meridian → cut a release', async ({ page }) => {
  // Unauthenticated visitors are gated to the login screen.
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/);

  // Log in (the mock accepts any non-"wrong" password for an allowed email).
  await page.getByLabel('Email').fill('astronomer@snoodleboot.com');
  await page.getByLabel('Password').fill('supernova');
  await page.getByRole('button', { name: /sign in/i }).click();

  // The constellation loads for the seeded product.
  await expect(page.getByText(/Aurora Platform · 4 components/)).toBeVisible();

  // Scrub the meridian earlier with the keyboard; the tick readout moves.
  const meridian = page.getByRole('slider', { name: /release meridian/i });
  await meridian.focus();
  const before = await meridian.getAttribute('aria-valuenow');
  await page.keyboard.press('ArrowLeft');
  await expect(meridian).not.toHaveAttribute('aria-valuenow', before ?? '');

  // Return to "now" so every component is pinned, then cut a release.
  await page.keyboard.press('End');
  await page.getByRole('button', { name: /cut release/i }).click();

  // The new release (server-assigned product version 5.1.0) appears in the ledger.
  await expect(page.getByText(/5\.1\.0/).first()).toBeVisible();
});

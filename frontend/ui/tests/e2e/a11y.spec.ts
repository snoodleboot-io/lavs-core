import { expect, test, type Page } from '@playwright/test';

interface AxeResult {
  readonly violations: readonly { readonly id: string; readonly impact: string | null }[];
}

// Run axe-core in-page and return serious/critical violations only.
async function seriousViolations(page: Page): Promise<AxeResult['violations']> {
  await page.addScriptTag({ path: 'node_modules/axe-core/axe.min.js' });
  const result = await page.evaluate(async () => {
    // axe is attached to window by the injected script.
    const axe = (window as unknown as { axe: { run: () => Promise<AxeResult> } }).axe;
    return axe.run();
  });
  return result.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
}

test('login screen has no serious accessibility violations', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
  const violations = await seriousViolations(page);
  expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
});

test('constellation view has no serious accessibility violations', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Email').fill('astronomer@snoodleboot.com');
  await page.getByLabel('Password').fill('supernova');
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page.getByText(/Aurora Platform · 4 components/)).toBeVisible();

  const violations = await seriousViolations(page);
  expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
});

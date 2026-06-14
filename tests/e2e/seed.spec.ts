// seed.spec.ts — quality lever for corobimy E2E tests
// Every new spec must follow these four patterns demonstrated here:
//   1. Role-based locators (getByRole, getByLabel, getByText)
//   2. Test independence (unique data, full setup+action+assertion+cleanup in one test)
//   3. Wait for state, not time (waitForURL, toBeVisible — never waitForTimeout)
//   4. Risk-tied name (describes the failure that would make the test red)
//
// Risk: test-plan.md — saved attraction data persists across sessions
// Source: references/seed-test.md

import { test, expect } from '@playwright/test';

test('saved attraction persists after page reload', async ({ page }) => {
  const username = `testuser${Date.now()}`;
  const password = 'testpass123!';

  // Register a unique test user so parallel runs never collide
  await page.goto('/accounts/register/');
  await page.getByLabel('Username:').fill(username);
  await page.getByLabel('Password:', { exact: true }).fill(password);
  await page.getByLabel('Password confirmation:').fill(password);
  await page.getByRole('button', { name: 'Register' }).click();

  // Navigate to the attraction list (registration auto-logs in)
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Discover Kraków' })).toBeVisible();

  // Save the first attraction in the list
  await page.getByRole('button', { name: 'Save' }).first().click();
  await page.waitForURL('/');

  // Saved badge must appear immediately — server confirmed the write
  await expect(page.getByText('Saved ✓').first()).toBeVisible();

  // Reload and confirm the save persisted server-side
  await page.reload();
  await expect(page.getByText('Saved ✓').first()).toBeVisible();

  // Cleanup: Django 6+ requires POST to log out — click the Logout button in the header
  await page.getByRole('button', { name: 'Logout' }).click();
  await expect(
    page.getByRole('heading', { name: 'You have been logged out.' })
  ).toBeVisible();
});

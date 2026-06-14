// Risk: test-plan.md #1 — saved attraction lost at auth redirect
//
// Scenario: anonymous user clicks Save → @login_required redirects to login
// with ?next=/attractions/<pk>/save/ → user navigates to register page
// (link preserves ?next=) → registers → auto-login → redirect follows ?next=
// → save_attraction runs get_or_create → redirects to / → "Saved ✓" visible.
//
// What would make this test red: save_attraction not handling GET after auth
// redirect, register view not preserving ?next=, or the post-login redirect
// bypassing the save URL entirely.
//
// Seed: seed.spec.ts

import { test, expect } from '@playwright/test';

test('saved attraction present in new account after anonymous save → register → auth redirect', async ({ page }) => {
  const username = `e2euser${Date.now()}`;
  const password = 'testpass123!';

  // Step 1: Visit the attraction list as an anonymous user
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Discover Kraków' })).toBeVisible();

  // Precondition: at least one Save button is visible (attractions exist and user is not logged in)
  await expect(page.getByRole('button', { name: 'Save' }).first()).toBeVisible();

  // Step 2: Click Save on the first attraction
  // @login_required intercepts the POST and redirects to login with ?next= set to the save URL
  await page.getByRole('button', { name: 'Save' }).first().click();
  await page.waitForURL(/\/accounts\/login\//);
  await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible();

  // Step 3: Navigate to the register page via the link on the login page
  // The login page renders: <a href="/accounts/register/?next=/attractions/<pk>/save/">Register</a>
  // so the ?next= parameter is carried forward to registration
  await page.getByRole('link', { name: 'Register' }).click();
  await page.waitForURL(/\/accounts\/register\//);
  await expect(page.getByRole('heading', { name: 'Create an account' })).toBeVisible();

  // Step 4: Register a new user
  // The register template includes <input type="hidden" name="next" value="...">
  // so the POST body carries the ?next= value through to the view
  await page.getByLabel('Username:').fill(username);
  await page.getByLabel('Password:', { exact: true }).fill(password);
  await page.getByLabel('Password confirmation:').fill(password);
  await page.getByRole('button', { name: 'Register' }).click();

  // Step 5: After register → auto-login → redirect to save URL → get_or_create → redirect to /
  // The entire redirect chain resolves to the attraction list
  await page.waitForURL('/');

  // KEY ASSERTION: the save persisted across the auth redirect boundary
  // A new user with zero prior saves must have exactly the attraction they attempted
  // to save as anonymous now showing "Saved ✓" — proving the ?next= chain completed
  await expect(page.getByText('Saved ✓')).toBeVisible();

  // Cleanup: Django 6+ requires POST to log out — click the Logout button in the header
  await page.getByRole('button', { name: 'Logout' }).click();
  await expect(
    page.getByRole('heading', { name: 'You have been logged out.' })
  ).toBeVisible();
});

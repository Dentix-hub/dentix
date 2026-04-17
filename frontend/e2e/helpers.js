/**
 * Test Helpers - Utility functions for E2E tests
 */

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

// Login as a specific role
export async function loginAs(page, username, password) {
  await page.goto(`${BASE_URL}/login`);
  await page.locator('input[type="text"]').fill(username);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
}

// Login as admin (default)
export async function loginAsAdmin(page) {
  return loginAs(page, 'admin', 'admin123');
}

// Login as doctor
export async function loginAsDoctor(page) {
  return loginAs(page, 'doctor1', 'doc123');
}

// Login as nurse
export async function loginAsNurse(page) {
  return loginAs(page, 'nurse1', 'nurse123');
}

// Login as receptionist
export async function loginAsReceptionist(page) {
  return loginAs(page, 'reception1', 'rec123');
}

// Login as accountant
export async function loginAsAccountant(page) {
  return loginAs(page, 'account1', 'acc123');
}

// Logout
export async function logout(page) {
  // Try to find logout button
  const logoutBtn = page.getByRole('button').filter({ hasText: /خروج|Logout|تسجيل الخروج/i }).first();
  if (await logoutBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await logoutBtn.click();
  } else {
    // Try profile menu
    await page.locator('[data-testid="user-menu"], header button').first().click();
    await logoutBtn.click();
  }
  await page.waitForURL(`${BASE_URL}/login`);
}

// Generate random test data
export function generateRandomName(prefix = 'Test') {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substring(7)}`;
}

export function generateRandomPhone() {
  return '010' + Math.floor(Math.random() * 100000000).toString().padStart(8, '0');
}

export function generateRandomEmail() {
  return `test_${Date.now()}@example.com`;
}

// Wait for page to be fully loaded
export async function waitForPageLoad(page) {
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);
}

// Navigate to a route and wait for it to load
export async function navigateTo(page, route) {
  await page.goto(`${BASE_URL}${route}`);
  await waitForPageLoad(page);
}

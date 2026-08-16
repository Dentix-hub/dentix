/**
 * E2E Test Setup - Creates the isolated CI clinic/admin required by the
 * production critical-path browser flow.
 */

import { test as setup, expect } from '@playwright/test';

const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const ADMIN_USER = 'e2e_admin';
const ADMIN_PASS = 'Dentix-E2E_Admin!2026_X9';

setup('E2E Test Setup: Create test data', async ({ request, page }) => {
  console.log('\nSetting up isolated Dentix E2E environment...');

  const baseUrl = API_URL.replace('/api/v1', '');

  const healthRes = await request.get(`${API_URL}/health`, { timeout: 10000 });
  expect(healthRes.ok()).toBeTruthy();
  console.log(`Backend is healthy at ${baseUrl}`);

  let adminToken: string | null = null;

  const initialLogin = await request.post(`${API_URL}/auth/token`, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    data: new URLSearchParams({ username: ADMIN_USER, password: ADMIN_PASS }).toString(),
  });

  if (initialLogin.ok()) {
    const loginBody = await initialLogin.json();
    adminToken = loginBody.access_token;
    console.log('E2E admin already exists.');
  } else {
    console.log('Creating isolated E2E clinic and admin...');

    const registerRes = await request.post(`${API_URL}/auth/register_clinic`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: new URLSearchParams({
        clinic_name: 'Dentix E2E Clinic',
        admin_username: ADMIN_USER,
        admin_email: 'admin.e2e@dentix.local',
        admin_password: ADMIN_PASS,
        contact_phone: '01000000000',
      }).toString(),
    });

    if (!registerRes.ok()) {
      throw new Error(
        `Could not create E2E clinic (${registerRes.status()}): ${await registerRes.text()}`
      );
    }

    const registerBody = await registerRes.json();
    adminToken = registerBody?.data?.access_token ?? registerBody?.access_token ?? null;

    if (!adminToken) {
      const loginRes = await request.post(`${API_URL}/auth/token`, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        data: new URLSearchParams({ username: ADMIN_USER, password: ADMIN_PASS }).toString(),
      });
      if (!loginRes.ok()) {
        throw new Error(`E2E admin login failed after registration: ${await loginRes.text()}`);
      }
      const loginBody = await loginRes.json();
      adminToken = loginBody.access_token;
    }
  }

  expect(adminToken).toBeTruthy();

  // The production critical-path suite only needs the clinic admin. A newly
  // registered trial tenant currently allows one user, so creating extra role
  // fixtures here would test subscription limits rather than the clinical flow.
  // Role-specific legacy E2E tests should provision their own plan/fixtures.

  await page.goto(`${BASE_URL}/login`);
  await page.locator('input[type="text"]').fill(ADMIN_USER);
  await page.locator('input[type="password"]').fill(ADMIN_PASS);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
  console.log('E2E admin browser login verified.');
});

/**
 * E2E Test Setup - Creates the isolated CI clinic and users before all browser flows.
 */

import { test as setup, expect } from '@playwright/test';

const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const ADMIN_USER = 'admin';
const ADMIN_PASS = 'Dentix-E2E_Admin!2026_X9';

const TEST_USERS = [
  { username: 'doctor1', role: 'doctor', password: 'Dentix-E2E_Doctor!2026_X9' },
  { username: 'nurse1', role: 'nurse', password: 'Dentix-E2E_Nurse!2026_X9' },
  { username: 'reception1', role: 'receptionist', password: 'Dentix-E2E_Reception!2026_X9' },
  { username: 'account1', role: 'accountant', password: 'Dentix-E2E_Account!2026_X9' },
];

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

    // The registration response shape is StandardResponse today, but use a real
    // login as the final source of truth so this setup survives response wrapping.
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

  console.log('Creating role-specific E2E users...');
  for (const user of TEST_USERS) {
    const params = new URLSearchParams({
      username: user.username,
      password: user.password,
      full_name: `E2E ${user.role}`,
      role: user.role,
    });

    const createRes = await request.post(`${API_URL}/users/register?${params.toString()}`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    });

    if (createRes.ok() || createRes.status() === 201) {
      console.log(`Created ${user.username} (${user.role}).`);
      continue;
    }

    const body = await createRes.text();
    if (/already registered|already exists|username/i.test(body) && createRes.status() === 400) {
      console.log(`${user.username} already exists.`);
      continue;
    }

    throw new Error(
      `Could not create ${user.username} (${createRes.status()}): ${body}`
    );
  }

  // Verify browser authentication too. This catches frontend/backend auth contract
  // drift before the feature E2E suites start.
  await page.goto(`${BASE_URL}/login`);
  await page.locator('input[type="text"]').fill(ADMIN_USER);
  await page.locator('input[type="password"]').fill(ADMIN_PASS);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
  console.log('E2E admin browser login verified.');
});

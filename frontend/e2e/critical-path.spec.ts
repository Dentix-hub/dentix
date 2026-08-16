import { test, expect } from '@playwright/test';
import { E2E_CREDENTIALS } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const TEST_USER = E2E_CREDENTIALS.admin.username;
const TEST_PASS = E2E_CREDENTIALS.admin.password;

test.describe('Dentix Critical Path', () => {
  test('authenticated clinical + finance core routes work', async ({ page }) => {
    // 1. Authenticate through the real browser UI.
    await page.goto(`${BASE_URL}/`);
    await page.locator('input[type="text"]').fill(TEST_USER);
    await page.locator('input[type="password"]').fill(TEST_PASS);
    await page.locator('button[type="submit"]').click();
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 15000 });
    await expect(page).toHaveURL(`${BASE_URL}/`);

    // 2. Create a deterministic fixture through the same authenticated browser
    // context. This keeps the production gate independent from presentation-only
    // details of the add-patient modal while still exercising the real API/auth.
    const patientName = `E2E Patient ${Date.now()}`;
    const patientPhone = `010${String(Date.now()).slice(-8)}`;
    const createRes = await page.request.post(`${API_URL}/patients`, {
      data: {
        name: patientName,
        age: 30,
        phone: patientPhone,
        address: 'E2E',
        medical_history: '',
        assigned_doctor_id: null,
      },
    });

    expect(createRes.ok(), await createRes.text()).toBeTruthy();
    const createBody = await createRes.json();
    const patient = createBody?.data ?? createBody;
    expect(patient?.id).toBeTruthy();

    // 3. Verify the current patient-card UI and navigation to patient details.
    await page.goto(`${BASE_URL}/patients`);
    const patientNameEl = page.getByText(patientName, { exact: true }).first();
    await expect(patientNameEl).toBeVisible({ timeout: 10000 });
    await patientNameEl.click();
    await expect(page).toHaveURL(`${BASE_URL}/patients/${patient.id}`, { timeout: 10000 });
    await expect(page.getByText(patientName, { exact: true }).first()).toBeVisible({ timeout: 10000 });

    // 4. Finance is part of the production recovery gate. Verify the clinic
    // admin can enter the current protected Finance/Billing route without a 404.
    await page.goto(`${BASE_URL}/billing`);
    await expect(page).toHaveURL(`${BASE_URL}/billing`);
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/404|page not found|الصفحة غير موجودة/i)).toHaveCount(0);
  });
});

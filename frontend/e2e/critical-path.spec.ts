import { test, expect } from '@playwright/test';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const TEST_USER = process.env.E2E_USERNAME || 'e2e_admin';
const TEST_PASS = process.env.E2E_PASSWORD || 'E2eAdmin123!';

test.describe('Dentix Critical Path', () => {
  test('login and persist a patient from the clinical UI', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="text"]').fill(TEST_USER);
    await page.locator('input[type="password"]').fill(TEST_PASS);
    await page.locator('button[type="submit"]').click();

    await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
    await expect(page.locator('nav').first()).toBeVisible();

    await page.goto(`${BASE_URL}/patients`);
    await expect(page).toHaveURL(/\/patients$/);

    const suffix = Date.now().toString().slice(-8);
    const patientName = `E2E Patient ${suffix}`;
    const patientPhone = `010${suffix}`;

    await page
      .getByRole('button', { name: /إضافة مريض جديد|Add New Patient/i })
      .click();
    await page.getByLabel(/الاسم بالكامل|Full Name/i).fill(patientName);
    await page.getByLabel(/رقم الهاتف|Phone Number/i).fill(patientPhone);

    const createPatientResponse = page.waitForResponse((response) =>
      response.url().endsWith('/api/v1/patients')
      && response.request().method() === 'POST',
    );
    await page
      .getByRole('button', { name: /حفظ وإضافة|Save & Add/i })
      .click();

    const response = await createPatientResponse;
    expect(response.ok()).toBeTruthy();
    const responseBody = await response.json();
    const createdPatient = responseBody.data ?? responseBody;
    expect(createdPatient.id).toBeTruthy();

    const persistedResponse = await page.request.get(
      `${process.env.E2E_API_URL || 'http://localhost:8000/api/v1'}/patients/${createdPatient.id}`,
    );
    expect(persistedResponse.ok()).toBeTruthy();
    const persistedBody = await persistedResponse.json();
    const persistedPatient = persistedBody.data ?? persistedBody;
    expect(persistedPatient.name).toBe(patientName);
    expect(persistedPatient.phone).toBe(patientPhone);
  });
});

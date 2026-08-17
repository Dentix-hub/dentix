import { test, expect } from '@playwright/test';
import { E2E_CREDENTIALS } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const TEST_USER = E2E_CREDENTIALS.admin.username;
const TEST_PASS = E2E_CREDENTIALS.admin.password;

function egyptInternationalPhone(localPhone: string) {
  return localPhone.startsWith('0') ? `+20${localPhone.slice(1)}` : localPhone;
}

test.describe('Dentix Critical Path', () => {
  test('authenticated patient workspace + clinical + finance core routes work', async ({ page }) => {
    // 1. Authenticate through the real browser UI.
    await page.goto(`${BASE_URL}/`);
    await page.locator('input[type="text"]').fill(TEST_USER);
    await page.locator('input[type="password"]').fill(TEST_PASS);
    await page.locator('button[type="submit"]').click();
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 15000 });
    await expect(page).toHaveURL(`${BASE_URL}/`);

    // 2. Create a deterministic patient fixture through the authenticated browser
    // context. Mirror the application's CSRF contract rather than bypassing it.
    const csrfCookie = (await page.context().cookies()).find(cookie => cookie.name === 'csrf_token');
    expect(csrfCookie?.value).toBeTruthy();

    const suffix = String(Date.now()).slice(-7);
    const patientName = `أحمد E2E ${suffix}`;
    const patientPhone = `010${String(Date.now()).slice(-8)}`;
    const createRes = await page.request.post(`${API_URL}/patients`, {
      headers: {
        'X-CSRF-Token': csrfCookie!.value,
      },
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

    // 3. Patient Workspace V2 is a semantic directory, not a card-only client filter.
    await page.goto(`${BASE_URL}/patients`);
    await expect(page.locator('table')).toBeVisible({ timeout: 10000 });

    const searchBox = page.getByRole('searchbox', {
      name: /Search patients|البحث في المرضى/i,
    });
    await expect(searchBox).toBeVisible();

    // Arabic normalization: stored "أحمد" must be discoverable as "احمد".
    await searchBox.fill(`احمد E2E ${suffix}`);
    await expect(page.getByText(patientName, { exact: true }).first()).toBeVisible({ timeout: 10000 });

    // File number search is exact and server-backed.
    await searchBox.fill(`#${patient.id}`);
    await expect(page.getByText(patientName, { exact: true }).first()).toBeVisible({ timeout: 10000 });

    // Egyptian local and international phone forms resolve to the same record.
    await searchBox.fill(egyptInternationalPhone(patientPhone));
    const patientNameEl = page.getByText(patientName, { exact: true }).first();
    await expect(patientNameEl).toBeVisible({ timeout: 10000 });

    // 4. Patient details remains reachable through a real semantic link.
    await patientNameEl.click();
    await expect(page).toHaveURL(`${BASE_URL}/patients/${patient.id}`, { timeout: 10000 });
    await expect(page.getByText(patientName, { exact: true }).first()).toBeVisible({ timeout: 10000 });

    // 5. Distinguish a true search miss from an empty clinic.
    await page.goto(`${BASE_URL}/patients`);
    const directorySearch = page.getByRole('searchbox', {
      name: /Search patients|البحث في المرضى/i,
    });
    await directorySearch.fill(`no-patient-${Date.now()}`);
    await expect(page.getByText(/No matching patient|لا يوجد مريض مطابق/i)).toBeVisible({ timeout: 10000 });

    // 6. Archive uses the normal patient-directory action and removes the record
    // from the active workspace without a hard delete.
    await directorySearch.fill(`#${patient.id}`);
    await expect(page.getByText(patientName, { exact: true }).first()).toBeVisible({ timeout: 10000 });
    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('confirm');
      await dialog.accept();
    });
    await page.getByRole('button', { name: /Archive patient|أرشفة المريض/i }).first().click();
    await expect(page.getByText(patientName, { exact: true })).toHaveCount(0, { timeout: 10000 });

    // 7. Finance is part of the production recovery gate. Verify the clinic admin
    // can enter the protected Finance/Billing route without a 404.
    await page.goto(`${BASE_URL}/billing`);
    await expect(page).toHaveURL(`${BASE_URL}/billing`);
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/404|page not found|الصفحة غير موجودة/i)).toHaveCount(0);
  });
});

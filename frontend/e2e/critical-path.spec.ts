import { test, expect } from '@playwright/test';
import { E2E_CREDENTIALS } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const TEST_USER = E2E_CREDENTIALS.admin.username;
const TEST_PASS = E2E_CREDENTIALS.admin.password;
const SUPER_ADMIN_USER = process.env.E2E_SUPER_ADMIN_USERNAME || 'admin';
const SUPER_ADMIN_PASS = process.env.E2E_SUPER_ADMIN_PASSWORD || 'admin123';

function egyptInternationalPhone(localPhone: string) {
  return localPhone.startsWith('0') ? `+20${localPhone.slice(1)}` : localPhone;
}

async function loginWithUi(page, username: string, password: string) {
  await page.goto(`${BASE_URL}/`);
  await page.locator('input[type="text"]').fill(username);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  await expect(page.locator('nav').first()).toBeVisible({ timeout: 15000 });
}

test.describe('Dentix Critical Path', () => {
  test('authenticated patient workspace + clinical + finance core routes work', async ({ page }) => {
    await loginWithUi(page, TEST_USER, TEST_PASS);
    await expect(page).toHaveURL(`${BASE_URL}/`);

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

    await page.goto(`${BASE_URL}/patients`);
    await expect(page.locator('table')).toBeVisible({ timeout: 10000 });

    const searchBox = page.getByRole('searchbox', {
      name: /Search patients|البحث في المرضى/i,
    });
    await expect(searchBox).toBeVisible();

    await searchBox.fill(`احمد E2E ${suffix}`);
    await expect(page.getByText(patientName, { exact: true }).first()).toBeVisible({ timeout: 10000 });

    await searchBox.fill(`#${patient.id}`);
    await expect(page.getByText(patientName, { exact: true }).first()).toBeVisible({ timeout: 10000 });

    await searchBox.fill(egyptInternationalPhone(patientPhone));
    const patientNameEl = page.getByText(patientName, { exact: true }).first();
    await expect(patientNameEl).toBeVisible({ timeout: 10000 });

    await patientNameEl.click();
    await expect(page).toHaveURL(`${BASE_URL}/patients/${patient.id}`, { timeout: 10000 });
    await expect(page.getByText(patientName, { exact: true }).first()).toBeVisible({ timeout: 10000 });

    await page.goto(`${BASE_URL}/patients`);
    const directorySearch = page.getByRole('searchbox', {
      name: /Search patients|البحث في المرضى/i,
    });
    await directorySearch.fill(`no-patient-${Date.now()}`);
    await expect(page.getByText(/No matching patient|لا يوجد مريض مطابق/i)).toBeVisible({ timeout: 10000 });

    await directorySearch.fill(`#${patient.id}`);
    await expect(page.getByText(patientName, { exact: true }).first()).toBeVisible({ timeout: 10000 });
    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('confirm');
      await dialog.accept();
    });
    await page.getByRole('button', { name: /Archive patient|أرشفة المريض/i }).first().click();
    await expect(page.getByText(patientName, { exact: true })).toHaveCount(0, { timeout: 10000 });

    await page.goto(`${BASE_URL}/billing`);
    await expect(page).toHaveURL(`${BASE_URL}/billing`);
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/404|page not found|الصفحة غير موجودة/i)).toHaveCount(0);
  });

  test('super admin impersonation is read-only and returns to the original admin session', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('i18nextLng', 'ar');
    });

    await loginWithUi(page, SUPER_ADMIN_USER, SUPER_ADMIN_PASS);
    await page.goto(`${BASE_URL}/admin/tenants`);
    await expect(page).toHaveURL(`${BASE_URL}/admin/tenants`);

    const tenantRow = page.locator('tbody tr').filter({ hasText: 'Dentix E2E Clinic' }).first();
    await expect(tenantRow).toBeVisible({ timeout: 10000 });
    await tenantRow.getByRole('button').first().click();

    const reasonInput = page.getByLabel(/سبب الدخول|Reason for access/i);
    await expect(reasonInput).toBeVisible({ timeout: 10000 });
    await reasonInput.fill('E2E read-only support verification');

    const startButton = page.getByRole('button', { name: /دخول مؤقت للنظام|Start temporary access/i });
    await expect(startButton).toBeEnabled();
    await startButton.click();

    await expect.poll(
      () => page.evaluate(() => window.sessionStorage.getItem('dentix_impersonation_token')),
      { timeout: 10000 },
    ).not.toBeNull();

    const impersonationToken = await page.evaluate(
      () => window.sessionStorage.getItem('dentix_impersonation_token'),
    );
    expect(impersonationToken).toBeTruthy();

    await expect(page.getByRole('button', { name: /العودة للوحة الإشراف|Return to Super Admin/i })).toBeVisible({ timeout: 10000 });

    const readResponse = await page.request.get(`${API_URL}/patients?limit=1`, {
      headers: { Authorization: `Bearer ${impersonationToken}` },
    });
    expect(readResponse.ok(), await readResponse.text()).toBeTruthy();

    const blockedWrite = await page.request.post(`${API_URL}/patients`, {
      headers: { Authorization: `Bearer ${impersonationToken}` },
      data: {
        name: `Blocked Impersonation ${Date.now()}`,
        age: 30,
        phone: `011${String(Date.now()).slice(-8)}`,
        address: 'Must not be created',
        medical_history: '',
        assigned_doctor_id: null,
      },
    });
    expect(blockedWrite.status()).toBe(403);
    expect(await blockedWrite.text()).toContain('Read-only impersonation cannot modify clinic data');

    await page.getByRole('button', { name: /العودة للوحة الإشراف|Return to Super Admin/i }).click();
    await expect(page).toHaveURL(`${BASE_URL}/admin/tenants`, { timeout: 10000 });
    await expect.poll(
      () => page.evaluate(() => window.sessionStorage.getItem('dentix_impersonation_token')),
      { timeout: 5000 },
    ).toBeNull();

    await expect(page.locator('tbody tr').filter({ hasText: 'Dentix E2E Clinic' }).first()).toBeVisible({ timeout: 10000 });
  });
});

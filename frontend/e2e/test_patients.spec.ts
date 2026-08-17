import { test, expect, type Page } from '@playwright/test';
import { loginAsAdmin, generateRandomName, generateRandomPhone } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function createPatientFixture(
  page: Page,
  overrides: Partial<{ name: string; phone: string; age: number }> = {},
) {
  const csrfCookie = (await page.context().cookies()).find((cookie) => cookie.name === 'csrf_token');
  expect(csrfCookie?.value).toBeTruthy();

  const fixture = {
    name: overrides.name || generateRandomName('Patient'),
    phone: overrides.phone || generateRandomPhone(),
    age: overrides.age ?? 30,
  };

  const response = await page.request.post(`${API_URL}/patients`, {
    headers: { 'X-CSRF-Token': csrfCookie!.value },
    data: {
      ...fixture,
      address: '',
      medical_history: '',
      assigned_doctor_id: null,
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  const body = await response.json();
  return { ...fixture, ...(body?.data ?? body) };
}

async function openPatients(page: Page) {
  await page.goto(`${BASE_URL}/patients`);
  await expect(page).toHaveURL(/\/patients(?:\?|$)/);
  await expect(page.getByRole('searchbox', { name: /Search patients|البحث في المرضى/i })).toBeVisible();
}

async function searchFor(page: Page, query: string) {
  const search = page.getByRole('searchbox', { name: /Search patients|البحث في المرضى/i });
  await search.fill(query);
  return search;
}

test.describe('Patient Workspace V2', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('PAT-V2-001: renders a semantic patient directory', async ({ page }) => {
    await openPatients(page);
    await expect(page.locator('table')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('th')).toContainText([/Patient|المريض/i]);
  });

  test('PAT-V2-002: Arabic normalized name search finds the correct patient', async ({ page }) => {
    const suffix = String(Date.now()).slice(-7);
    const patient = await createPatientFixture(page, {
      name: `أحمد إي تو إي ${suffix}`,
      phone: `010${suffix.padStart(8, '0').slice(-8)}`,
    });

    await openPatients(page);
    await searchFor(page, `احمد اي تو اي ${suffix}`);
    await expect(page.getByRole('link', { name: patient.name, exact: true })).toBeVisible({ timeout: 10000 });
  });

  test('PAT-V2-003: file number search is exact', async ({ page }) => {
    const patient = await createPatientFixture(page);
    await openPatients(page);
    await searchFor(page, `#${patient.id}`);
    await expect(page.getByRole('link', { name: patient.name, exact: true })).toBeVisible({ timeout: 10000 });
  });

  test('PAT-V2-004: Egyptian international phone format finds a local-format record', async ({ page }) => {
    const suffix = String(Date.now()).slice(-8);
    const localPhone = `010${suffix}`;
    const patient = await createPatientFixture(page, { phone: localPhone });

    await openPatients(page);
    await searchFor(page, `+20${localPhone.slice(1)}`);
    await expect(page.getByRole('link', { name: patient.name, exact: true })).toBeVisible({ timeout: 10000 });
  });

  test('PAT-V2-005: opens patient details through the semantic patient link', async ({ page }) => {
    const patient = await createPatientFixture(page);
    await openPatients(page);
    await searchFor(page, `#${patient.id}`);

    const patientLink = page.getByRole('link', { name: patient.name, exact: true });
    await expect(patientLink).toBeVisible({ timeout: 10000 });
    await patientLink.click();

    await expect(page).toHaveURL(new RegExp(`/patients/${patient.id}(?:\\?|$)`));
    await expect(page.getByText(patient.name, { exact: true }).first()).toBeVisible({ timeout: 10000 });
  });

  test('PAT-V2-006: age-first registration creates one patient without requiring DOB', async ({ page }) => {
    const name = generateRandomName('AgeFirst');
    const phone = generateRandomPhone();

    await openPatients(page);
    await page.getByRole('button', { name: /Add Patient|إضافة مريض/i }).first().click();

    const nameInput = page.getByLabel(/Patient Name|اسم المريض/i).first();
    const phoneInput = page.getByLabel(/Phone|الهاتف|الموبايل/i).first();
    const ageInput = page.getByLabel(/Age|العمر|السن/i).first();
    await nameInput.fill(name);
    await phoneInput.fill(phone);
    await ageInput.fill('34');

    const exactDobCheckbox = page.getByRole('checkbox', {
      name: /Exact date of birth is known|تاريخ الميلاد الدقيق معروف/i,
    });
    await expect(exactDobCheckbox).not.toBeChecked();

    await page.locator('form').getByRole('button', { name: /Save|حفظ|إضافة|Add/i }).last().click();
    await expect(page.getByText(name, { exact: true }).first()).toBeVisible({ timeout: 10000 });
  });

  test('PAT-V2-007: archive removes the patient from the active directory', async ({ page }) => {
    const patient = await createPatientFixture(page);
    await openPatients(page);
    await searchFor(page, `#${patient.id}`);
    await expect(page.getByRole('link', { name: patient.name, exact: true })).toBeVisible({ timeout: 10000 });

    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('confirm');
      await dialog.accept();
    });
    await page.getByRole('button', { name: /Archive patient|أرشفة المريض/i }).first().click();

    await expect(page.getByRole('link', { name: patient.name, exact: true })).toHaveCount(0, { timeout: 10000 });
  });

  test('PAT-V2-008: no-result state does not silently look like an empty clinic', async ({ page }) => {
    await openPatients(page);
    await searchFor(page, `no-patient-${Date.now()}`);
    await expect(page.getByText(/No matching patient|لا يوجد مريض مطابق/i)).toBeVisible({ timeout: 10000 });
  });
});

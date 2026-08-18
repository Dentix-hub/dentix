import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers.js';

const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function installPreferences(page, language: 'ar' | 'en', theme: 'light' | 'dark') {
  await page.addInitScript(({ language, theme }) => {
    window.localStorage.setItem('i18nextLng', language);
    window.localStorage.setItem('theme', theme);
  }, { language, theme });
}

function fixtureFor(projectName: string, language: 'ar' | 'en') {
  const mobile = projectName === 'visual-mobile';

  if (language === 'en') {
    return {
      name: 'Visual Patient Desktop',
      phone: '01090000003',
    };
  }

  return mobile
    ? { name: 'مريض بصري موبايل', phone: '01090000002' }
    : { name: 'مريض بصري سطح المكتب', phone: '01090000001' };
}

async function ensurePatientFixture(page, fixture: { name: string; phone: string }) {
  const searchRes = await page.request.get(
    `${API_URL}/patients/search?q=${encodeURIComponent(fixture.name)}`,
  );

  if (searchRes.ok()) {
    const searchBody = await searchRes.json();
    const patients = searchBody?.data ?? searchBody;
    if (Array.isArray(patients) && patients.some(patient => patient?.name === fixture.name)) {
      return;
    }
  }

  const csrfCookie = (await page.context().cookies()).find(cookie => cookie.name === 'csrf_token');
  expect(csrfCookie?.value).toBeTruthy();

  const createRes = await page.request.post(`${API_URL}/patients`, {
    headers: {
      'X-CSRF-Token': csrfCookie!.value,
    },
    data: {
      name: fixture.name,
      age: 30,
      phone: fixture.phone,
      address: 'Visual regression fixture',
      medical_history: '',
      assigned_doctor_id: null,
    },
  });

  expect(createRes.ok(), await createRes.text()).toBeTruthy();
}

async function openPatientWorkspace(page, fixture: { name: string; phone: string }) {
  await loginAsAdmin(page);
  await ensurePatientFixture(page, fixture);
  await page.goto('/patients');

  const heading = page.getByRole('heading', {
    level: 1,
    name: /Patient records|سجلات المرضى/i,
  });
  await expect(heading).toBeVisible({ timeout: 15000 });

  const searchBox = page.getByRole('searchbox', {
    name: /Search patients|البحث في المرضى/i,
  });
  await searchBox.fill(fixture.name);

  const visiblePatientLink = page.getByRole('link', { name: fixture.name, exact: true }).first();
  await expect(visiblePatientLink).toBeVisible({ timeout: 10000 });
}

async function expectWorkspaceScreenshot(page, name: string) {
  const dynamicClock = page.locator('time');
  await expect(page).toHaveScreenshot(name, {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    mask: [dynamicClock],
    maskColor: '#E5E7EB',
    maxDiffPixelRatio: 0.01,
  });
}

test.describe('Dentix visual regression baseline', () => {
  test('patient workspace — Arabic light', async ({ page }, testInfo) => {
    const fixture = fixtureFor(testInfo.project.name, 'ar');
    await installPreferences(page, 'ar', 'light');
    await openPatientWorkspace(page, fixture);
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
    await expectWorkspaceScreenshot(page, 'patients-ar-light.png');
  });

  test('patient workspace — English dark', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'visual-mobile', 'Strategic mobile baseline uses Arabic/light; avoid combinatorial matrix.');

    const fixture = fixtureFor(testInfo.project.name, 'en');
    await installPreferences(page, 'en', 'dark');
    await openPatientWorkspace(page, fixture);
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
    await expect(page.locator('html')).toHaveClass(/dark/);
    await expectWorkspaceScreenshot(page, 'patients-en-dark.png');
  });
});

test.describe('Dentix overlay interaction regression', () => {
  test('patient modal traps focus and restores trigger/scroll state', async ({ page }) => {
    await installPreferences(page, 'ar', 'light');
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await loginAsAdmin(page);
    await page.goto('/patients');

    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
    const heading = page.getByRole('heading', { level: 1, name: /Patient records|سجلات المرضى/i });
    await expect(heading).toBeVisible({ timeout: 15000 });

    const trigger = page.getByRole('button', { name: /Add New Patient|إضافة مريض جديد/i }).first();
    await expect(trigger).toBeVisible();
    const overflowBefore = await page.evaluate(() => document.body.style.overflow);

    await trigger.focus();
    await trigger.press('Enter');

    const dialog = page.locator('[data-dentix-overlay="dialog"]');
    await expect(dialog).toBeVisible();
    const dialogBackground = await dialog.evaluate(node => getComputedStyle(node).backgroundColor);
    expect(dialogBackground).not.toBe('transparent');
    expect(dialogBackground).not.toBe('rgba(0, 0, 0, 0)');

    await page.keyboard.press('Tab');
    expect(await dialog.evaluate(node => node.contains(document.activeElement))).toBeTruthy();
    await page.keyboard.press('Shift+Tab');
    expect(await dialog.evaluate(node => node.contains(document.activeElement))).toBeTruthy();

    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
    await expect(trigger).toBeFocused();
    expect(await page.evaluate(() => document.body.style.overflow)).toBe(overflowBefore);

    await trigger.press('Space');
    await expect(dialog).toBeVisible();
    const backdrop = page.locator('[data-dentix-overlay="backdrop"]');
    await backdrop.click({ position: { x: 4, y: 4 } });
    await expect(dialog).toBeHidden();
    await expect(trigger).toBeFocused();
  });
});

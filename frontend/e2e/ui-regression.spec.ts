import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers.js';

async function installPreferences(page, language: 'ar' | 'en', theme: 'light' | 'dark') {
  await page.addInitScript(({ language, theme }) => {
    window.localStorage.setItem('i18nextLng', language);
    window.localStorage.setItem('theme', theme);
  }, { language, theme });
}

async function openPatientWorkspace(page) {
  await loginAsAdmin(page);
  await page.goto('/patients');
  await expect(page.locator('table')).toBeVisible({ timeout: 15000 });
}

async function expectWorkspaceScreenshot(page, name: string) {
  const dynamicClock = page.locator('time');
  await expect(page).toHaveScreenshot(name, {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    mask: [dynamicClock],
    maxDiffPixelRatio: 0.01,
  });
}

test.describe('Dentix visual regression baseline', () => {
  test('patient workspace — Arabic light', async ({ page }) => {
    await installPreferences(page, 'ar', 'light');
    await openPatientWorkspace(page);
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
    await expectWorkspaceScreenshot(page, 'patients-ar-light.png');
  });

  test('patient workspace — English dark', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'visual-mobile', 'Strategic mobile baseline uses Arabic/light; avoid combinatorial matrix.');

    await installPreferences(page, 'en', 'dark');
    await openPatientWorkspace(page);
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
    await expect(page.locator('html')).toHaveClass(/dark/);
    await expectWorkspaceScreenshot(page, 'patients-en-dark.png');
  });
});

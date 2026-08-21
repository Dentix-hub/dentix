import { test, expect, type Page } from '@playwright/test';
import { loginAsAdmin } from './helpers.js';

const REPRESENTATIVE_ROUTES = [
  '/',
  '/appointments',
  '/patients',
  '/inventory',
  '/finance/expenses',
  '/labs',
  '/settings',
];

function preferencesForProject(projectName: string) {
  if (projectName === 'mobile-en') return { language: 'en', theme: 'dark' } as const;
  if (projectName === 'tablet') return { language: 'en', theme: 'light' } as const;
  return { language: 'ar', theme: 'light' } as const;
}

async function installPreferences(page: Page, language: 'ar' | 'en', theme: 'light' | 'dark') {
  await page.addInitScript(({ language, theme }) => {
    window.localStorage.setItem('i18nextLng', language);
    window.localStorage.setItem('theme', theme);
  }, { language, theme });
}

async function expectNoDocumentOverflow(page: Page, tolerance = 2) {
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
  }));

  expect(
    dimensions.scrollWidth,
    `document overflow: scrollWidth=${dimensions.scrollWidth}, clientWidth=${dimensions.clientWidth}, bodyScrollWidth=${dimensions.bodyScrollWidth}`,
  ).toBeLessThanOrEqual(dimensions.clientWidth + tolerance);
}

async function getVisibleViewport(page: Page) {
  return page.evaluate(() => {
    const visualViewport = window.visualViewport;
    return {
      x: visualViewport?.offsetLeft ?? 0,
      y: visualViewport?.offsetTop ?? 0,
      width: visualViewport?.width ?? window.innerWidth,
      height: visualViewport?.height ?? window.innerHeight,
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      clientWidth: document.documentElement.clientWidth,
      clientHeight: document.documentElement.clientHeight,
    };
  });
}

async function expectLocatorInsideViewport(page: Page, locator) {
  await expect(locator).toBeVisible();
  const tolerance = 2;

  // Headless UI may expose the entering panel one frame before its translate-y
  // transition reaches the final position. Verify the settled geometry rather
  // than sampling the transient enterFrom state.
  await expect.poll(async () => {
    const bounds = await locator.boundingBox();
    const viewport = await getVisibleViewport(page);
    if (!bounds) return false;

    const viewportRight = viewport.x + viewport.width;
    const viewportBottom = viewport.y + viewport.height;
    return bounds.x >= viewport.x - tolerance
      && bounds.y >= viewport.y - tolerance
      && bounds.x + bounds.width <= viewportRight + tolerance
      && bounds.y + bounds.height <= viewportBottom + tolerance;
  }, { timeout: 2000 }).toBe(true);

  const bounds = await locator.boundingBox();
  const viewport = await getVisibleViewport(page);
  expect(bounds).not.toBeNull();
  if (!bounds) return;

  const viewportRight = viewport.x + viewport.width;
  const viewportBottom = viewport.y + viewport.height;
  const diagnostic = `bounds=${JSON.stringify(bounds)}, visualViewport=${JSON.stringify(viewport)}`;

  expect(bounds.x, diagnostic).toBeGreaterThanOrEqual(viewport.x - tolerance);
  expect(bounds.y, diagnostic).toBeGreaterThanOrEqual(viewport.y - tolerance);
  expect(bounds.x + bounds.width, diagnostic).toBeLessThanOrEqual(viewportRight + tolerance);
  expect(bounds.y + bounds.height, diagnostic).toBeLessThanOrEqual(viewportBottom + tolerance);
}

async function expectOverlayInsideViewport(page: Page, selector: string) {
  const overlay = page.locator(selector).last();
  await expectLocatorInsideViewport(page, overlay);
  const background = await overlay.evaluate(node => getComputedStyle(node).backgroundColor);
  expect(background).not.toBe('transparent');
  expect(background).not.toBe('rgba(0, 0, 0, 0)');
}

test.describe('Dentix responsive shell regression', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    const preferences = preferencesForProject(testInfo.project.name);
    await installPreferences(page, preferences.language, preferences.theme);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await loginAsAdmin(page);
  });

  test('representative routes do not create document-level horizontal overflow', async ({ page }, testInfo) => {
    test.setTimeout(120000);

    for (const route of REPRESENTATIVE_ROUTES) {
      await test.step(`${route} stays inside ${testInfo.project.name}`, async () => {
        await page.goto(route);
        await page.locator('#main-content').waitFor({ state: 'visible', timeout: 15000 });
        await page.waitForTimeout(250);
        await expectNoDocumentOverflow(page);
      });
    }
  });

  test('mobile shell menu contains interaction and restores the page', async ({ page }) => {
    const viewport = page.viewportSize();
    test.skip(!viewport || viewport.width >= 1024, 'Mobile sidebar behavior is only applicable below desktop shell breakpoint.');

    await page.goto('/');
    const menuButton = page.getByRole('button', { name: /Open Menu|فتح القائمة/i }).first();
    await expect(menuButton).toBeVisible();
    await menuButton.click();

    const sidebar = page.locator('[data-sidebar]');
    await expect(sidebar).toBeVisible();
    await expectNoDocumentOverflow(page);
    expect(await page.evaluate(() => document.body.style.overflow)).toBe('hidden');

    const backdrop = page.getByRole('button', { name: /Close menu|إغلاق القائمة/i }).first();
    await expect(backdrop).toBeVisible();

    // Wait for the drawer's CSS transition before deriving an exposed backdrop
    // point. A raw page.mouse click can race the RTL translate animation between
    // bounding-box measurement and dispatch, so use locator.click for normal
    // Playwright stability/actionability checks at the verified exposed point.
    await sidebar.evaluate(async node => {
      await Promise.all(node.getAnimations().map(animation => animation.finished.catch(() => undefined)));
    });

    const sidebarBounds = await sidebar.boundingBox();
    const backdropBounds = await backdrop.boundingBox();
    expect(sidebarBounds).not.toBeNull();
    expect(backdropBounds).not.toBeNull();
    if (sidebarBounds && backdropBounds) {
      const backdropRight = backdropBounds.x + backdropBounds.width;
      const sidebarRight = sidebarBounds.x + sidebarBounds.width;
      const leftGap = Math.max(0, sidebarBounds.x - backdropBounds.x);
      const rightGap = Math.max(0, backdropRight - sidebarRight);
      expect(Math.max(leftGap, rightGap), 'mobile drawer must leave an exposed backdrop strip').toBeGreaterThan(0);

      const globalX = leftGap >= rightGap
        ? backdropBounds.x + leftGap / 2
        : sidebarRight + rightGap / 2;
      const globalY = Math.min(
        backdropBounds.y + backdropBounds.height - 4,
        Math.max(backdropBounds.y + 4, sidebarBounds.y + 8),
      );

      await backdrop.click({
        position: {
          x: globalX - backdropBounds.x,
          y: globalY - backdropBounds.y,
        },
      });
    }

    await expect(sidebar).toHaveAttribute('aria-hidden', 'true');
    await expect(menuButton).toHaveAttribute('aria-expanded', 'false');
    await expect(menuButton).toBeFocused();
    await expectNoDocumentOverflow(page);
  });
});

test.describe('Dentix responsive overlay regression', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    const preferences = preferencesForProject(testInfo.project.name);
    await installPreferences(page, preferences.language, preferences.theme);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await loginAsAdmin(page);
  });

  test('patient create overlay remains inside the visible viewport', async ({ page }) => {
    await page.goto('/patients');
    const trigger = page.getByRole('button', { name: /Add New Patient|إضافة مريض جديد/i }).first();
    await expect(trigger).toBeVisible({ timeout: 15000 });
    await trigger.click();

    const viewport = page.viewportSize();
    const selector = viewport && viewport.width < 640
      ? '[data-dentix-overlay="bottom-sheet"]'
      : '[data-dentix-overlay="dialog"]';
    await expectOverlayInsideViewport(page, selector);
    await expectNoDocumentOverflow(page);

    await page.keyboard.press('Escape');
    await expect(page.locator(selector)).toBeHidden();
  });

  test('appointment creation and date picker stay touch-safe', async ({ page }) => {
    await page.goto('/appointments');
    const newBooking = page.getByRole('button', { name: /New Booking|حجز جديد|موعد جديد/i }).first();
    await expect(newBooking).toBeVisible({ timeout: 15000 });
    await newBooking.click();

    const viewport = page.viewportSize();
    const modalSelector = viewport && viewport.width < 640
      ? '[data-dentix-overlay="bottom-sheet"]'
      : '[data-dentix-overlay="dialog"]';
    await expectOverlayInsideViewport(page, modalSelector);

    const pickerTrigger = page.locator(`${modalSelector} [data-date-time-picker-trigger]`).first();
    await expect(pickerTrigger).toBeVisible();
    await pickerTrigger.click();

    const dateDialog = page.locator('[data-date-time-picker-dialog]').last();
    const datePanel = dateDialog;
    await expectLocatorInsideViewport(page, datePanel);
    await expectNoDocumentOverflow(page);

    const selectedDay = dateDialog.locator('[data-picker-option="day"][aria-pressed="true"]');
    const alternativeDay = dateDialog.locator('[data-picker-option="day"][aria-pressed="false"].text-text-primary').first();
    const alternativeHour = dateDialog.locator('[data-picker-option="hour"][aria-pressed="false"]').first();

    await expect(selectedDay).toHaveCount(1);
    await alternativeDay.click();
    await alternativeHour.click();
    await expect(alternativeDay).toHaveAttribute('aria-pressed', 'true');
    await expect(alternativeHour).toHaveAttribute('aria-pressed', 'true');
  });
});

test.describe('Dentix mobile operational fallbacks', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    const preferences = preferencesForProject(testInfo.project.name);
    await installPreferences(page, preferences.language, preferences.theme);
    await loginAsAdmin(page);
  });

  test('appointments expose a non-drag status control', async ({ page }) => {
    await page.goto('/appointments');
    await page.locator('#main-content').waitFor({ state: 'visible' });

    const statusSelect = page.locator('select:has(option[value="Scheduled"])').first();
    if (await statusSelect.count()) {
      await expect(statusSelect).toBeVisible();
      const box = await statusSelect.boundingBox();
      if (box) expect(box.height).toBeGreaterThanOrEqual(42);
    }
    await expectNoDocumentOverflow(page);
  });

  test('inventory uses cards below desktop table breakpoint', async ({ page }) => {
    await page.goto('/inventory');
    await page.locator('#main-content').waitFor({ state: 'visible' });
    await expectNoDocumentOverflow(page);

    const viewport = page.viewportSize();
    if (viewport && viewport.width < 1024) {
      const stockTable = page.locator('table').filter({ hasText: /Current Stock|المخزون الحالي/i }).first();
      if (await stockTable.count()) await expect(stockTable).toBeHidden();
    }
  });
});

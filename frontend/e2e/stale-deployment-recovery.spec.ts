import { expect, test } from '@playwright/test';

const RELOAD_KEY = 'dentix:pwa:chunk-reload';

test('vite preload errors trigger one controlled reload per cooldown', async ({ page }) => {
  await page.goto('/');
  await page.evaluate((storageKey) => window.sessionStorage.removeItem(storageKey), RELOAD_KEY);

  const reload = page.waitForNavigation({ waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    window.dispatchEvent(new Event('vite:preloadError', { cancelable: true }));
  });
  await reload;

  const firstReloadTimestamp = await page.evaluate((storageKey) => {
    const value = window.sessionStorage.getItem(storageKey);
    return value === null ? null : Number(value);
  }, RELOAD_KEY);
  expect(firstReloadTimestamp).not.toBeNull();
  expect(firstReloadTimestamp).toBeGreaterThan(0);

  await page.evaluate(() => {
    (window as typeof window & { __DENTIX_PHASE5_NO_SECOND_RELOAD__?: string }).__DENTIX_PHASE5_NO_SECOND_RELOAD__ = 'present';
    window.dispatchEvent(new Event('vite:preloadError', { cancelable: true }));
  });

  await page.waitForTimeout(750);

  const secondDispatchState = await page.evaluate((storageKey) => ({
    sentinel: (window as typeof window & { __DENTIX_PHASE5_NO_SECOND_RELOAD__?: string }).__DENTIX_PHASE5_NO_SECOND_RELOAD__,
    timestamp: window.sessionStorage.getItem(storageKey),
  }), RELOAD_KEY);

  expect(secondDispatchState.sentinel).toBe('present');
  expect(Number(secondDispatchState.timestamp)).toBe(firstReloadTimestamp);
});

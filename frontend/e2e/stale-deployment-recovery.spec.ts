import { expect, test, type Page } from '@playwright/test';

const RELOAD_KEY = 'dentix:pwa:chunk-reload';

async function clearReloadCooldown(page: Page) {
  await page.evaluate((storageKey) => window.sessionStorage.removeItem(storageKey), RELOAD_KEY);
}

async function reloadTimestamp(page: Page) {
  return page.evaluate((storageKey) => {
    const value = window.sessionStorage.getItem(storageKey);
    return value === null ? null : Number(value);
  }, RELOAD_KEY);
}

async function triggerPreloadRecovery(page: Page) {
  const navigation = page.waitForNavigation({ waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    window.dispatchEvent(new Event('vite:preloadError', { cancelable: true }));
  });
  await navigation;
}

test('vite preload errors trigger one controlled reload per cooldown', async ({ page }) => {
  await page.goto('/');
  await clearReloadCooldown(page);

  await triggerPreloadRecovery(page);

  const firstReloadTimestamp = await reloadTimestamp(page);
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

test('stale preload recovery survives soft navigation before the chunk failure', async ({ page }) => {
  await page.goto('/?phase5=soft-start');
  await clearReloadCooldown(page);

  // BrowserRouter-style navigation: change history without a document request.
  await page.evaluate(() => window.history.pushState({ phase5: true }, '', '/?phase5=soft-navigation'));
  expect(page.url()).toContain('phase5=soft-navigation');

  await triggerPreloadRecovery(page);

  expect(page.url()).toContain('phase5=soft-navigation');
  expect(await reloadTimestamp(page)).toBeGreaterThan(0);
});

test('stale preload recovery survives a hard navigation before the chunk failure', async ({ page }) => {
  await page.goto('/?phase5=hard-start');
  await clearReloadCooldown(page);

  // A second goto is a new document navigation, matching a user hard-navigation lifecycle.
  await page.goto('/?phase5=hard-navigation');
  await clearReloadCooldown(page);

  await triggerPreloadRecovery(page);

  expect(page.url()).toContain('phase5=hard-navigation');
  expect(await reloadTimestamp(page)).toBeGreaterThan(0);
});

test('stale preload recovery still works after a manual browser refresh', async ({ page }) => {
  await page.goto('/?phase5=manual-refresh');
  await clearReloadCooldown(page);

  await page.reload({ waitUntil: 'domcontentloaded' });
  await clearReloadCooldown(page);

  await triggerPreloadRecovery(page);

  expect(page.url()).toContain('phase5=manual-refresh');
  expect(await reloadTimestamp(page)).toBeGreaterThan(0);
});

test('closing and reopening the app gets a fresh recovery cooldown scope', async ({ context }) => {
  const firstPage = await context.newPage();
  await firstPage.goto('/?phase5=close-before-reopen');
  await clearReloadCooldown(firstPage);
  await triggerPreloadRecovery(firstPage);
  expect(await reloadTimestamp(firstPage)).toBeGreaterThan(0);
  await firstPage.close();

  const reopenedPage = await context.newPage();
  await reopenedPage.goto('/?phase5=reopened');

  // sessionStorage is tab-scoped. Closing the old app window must not suppress
  // recovery in a newly opened app window.
  expect(await reloadTimestamp(reopenedPage)).toBeNull();

  await triggerPreloadRecovery(reopenedPage);
  expect(reopenedPage.url()).toContain('phase5=reopened');
  expect(await reloadTimestamp(reopenedPage)).toBeGreaterThan(0);
  await reopenedPage.close();
});

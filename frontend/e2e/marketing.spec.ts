import { test, expect } from '@playwright/test';

test.describe('Dentix Arabic Marketing Page', () => {
  test('renders complete Arabic marketing content and valid metadata', async ({ page }) => {
    await page.goto('/ar/index.html');

    // Title & HTML attributes
    await expect(page).toHaveTitle('Dentix | برنامج إدارة عيادات الأسنان في مصر');
    const html = page.locator('html');
    await expect(html).toHaveAttribute('lang', 'ar');
    await expect(html).toHaveAttribute('dir', 'rtl');

    // Heading H1
    const h1 = page.locator('h1');
    await expect(h1).toHaveText('إدارة عيادة الأسنان من مكان واحد.');

    // Canonical link
    const canonical = page.locator('link[rel="canonical"]');
    await expect(canonical).toHaveAttribute('href', 'https://www.dentixs.app/ar');

    // Key sections are visible
    await expect(page.locator('#features')).toBeVisible();
    await expect(page.locator('#how-it-works')).toBeVisible();
    await expect(page.locator('#faq')).toBeVisible();

    // Feature cards are present
    const featureCards = page.locator('.feature-card');
    await expect(featureCards).toHaveCount(4);

    // FAQ details can be toggled without JavaScript
    const firstFaq = page.locator('.faq-item').first();
    await expect(firstFaq).not.toHaveAttribute('open', '');
    await firstFaq.locator('summary').click();
    await expect(firstFaq).toHaveAttribute('open', '');
  });

  test('enforces strict contract on action links: login points to / (NOT /login)', async ({ page }) => {
    await page.goto('/ar/index.html');

    // Check all login buttons/links on the marketing page
    const loginLinks = page.locator('a:has-text("تسجيل الدخول")');
    const count = await loginLinks.count();
    expect(count).toBeGreaterThanOrEqual(2);

    for (let i = 0; i < count; i++) {
      const href = await loginLinks.nth(i).getAttribute('href');
      expect(href, 'Login link must point to /').toBe('/');
      expect(href).not.toBe('/login');
    }

    // Check register link
    const registerLinks = page.locator('a:has-text("إنشاء حساب عيادة")');
    const regCount = await registerLinks.count();
    expect(regCount).toBeGreaterThanOrEqual(2);
    for (let i = 0; i < regCount; i++) {
      const href = await registerLinks.nth(i).getAttribute('href');
      expect(href).toBe('/register');
    }
  });

  test('verifies zero horizontal overflow across responsive viewports', async ({ page }) => {
    await page.goto('/ar/index.html');

    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll, 'Page must not have horizontal overflow').toBe(false);
  });

  test('audits network requests: zero API requests and zero POST/write operations', async ({ page }) => {
    const requestedUrls: string[] = [];
    const nonGetMethods: string[] = [];

    page.on('request', (req) => {
      requestedUrls.push(req.url());
      if (req.method() !== 'GET' && req.method() !== 'HEAD') {
        nonGetMethods.push(`${req.method()} ${req.url()}`);
      }
    });

    await page.goto('/ar/index.html');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);

    // Assert zero API requests
    const apiRequests = requestedUrls.filter((url) => url.includes('/api/'));
    expect(apiRequests, 'Marketing page must not make any /api/ calls').toHaveLength(0);

    // Assert zero write operations (POST, PUT, DELETE, PATCH)
    expect(nonGetMethods, 'Marketing page must not make non-GET requests').toHaveLength(0);
  });

  test('verifies discovery link from login page points to /ar via native anchor', async ({ page, javaScriptEnabled }) => {
    test.skip(!javaScriptEnabled, 'Login page is a React SPA requiring JavaScript execution to mount');
    await page.goto('/');

    // Locate the discovery link in the Login footer
    const discoveryLink = page.locator('a[href="/ar"]');
    await expect(discoveryLink).toBeVisible();
    await expect(discoveryLink).toHaveAttribute('href', '/ar');
  });

  test('captures desktop and mobile review screenshots', async ({ page }, testInfo) => {
    await page.goto('/ar/index.html');
    if (testInfo.project.name === 'desktop-chrome') {
      const screenshotPath = testInfo.outputPath('marketing-ar-desktop.png');
      const buffer = await page.screenshot({ path: screenshotPath, fullPage: true });
      await testInfo.attach('desktop-screenshot', {
        body: buffer,
        contentType: 'image/png',
      });
    } else if (testInfo.project.name === 'mobile-390') {
      const screenshotPath = testInfo.outputPath('marketing-ar-mobile.png');
      const buffer = await page.screenshot({ path: screenshotPath, fullPage: true });
      await testInfo.attach('mobile-screenshot', {
        body: buffer,
        contentType: 'image/png',
      });
    }
  });

  test('PWA lifecycle: old worker waits for user update, accepts SKIP_WAITING, then allows /ar navigation without breaking app routes', async ({ page, context, javaScriptEnabled }) => {
    test.skip(!javaScriptEnabled, 'Service worker requires JavaScript');

    // 1. Mock an old service worker that intercepts /ar navigations (as legacy SW lacked the /ar bypass)
    // while allowing real application routes to pass through to the app shell.
    await context.route('**/mock-old-sw.js', (route) => {
      route.fulfill({
        contentType: 'application/javascript',
        body: `
          self.addEventListener('install', (e) => self.skipWaiting());
          self.addEventListener('activate', (e) => self.clients.claim());
          self.addEventListener('fetch', (e) => {
            const url = new URL(e.request.url);
            if (e.request.mode === 'navigate' && (url.pathname === '/ar' || url.pathname.startsWith('/ar/'))) {
              e.respondWith(new Response('<!DOCTYPE html><html><body><div id="root">OLD_APP_SHELL_INTERCEPTED</div></body></html>', {
                headers: { 'Content-Type': 'text/html; charset=utf-8' }
              }));
              return;
            }
          });
        `,
      });
    });

    // Clean up any lingering SW from previous tests to ensure deterministic state
    await page.goto('/');
    await page.evaluate(async () => {
      const registrations = await navigator.serviceWorker.getRegistrations();
      for (const r of registrations) await r.unregister();
    });

    // 2. Register old SW and wait for it to take control
    await page.evaluate(async () => {
      await navigator.serviceWorker.register('/mock-old-sw.js', { scope: '/' });
      await navigator.serviceWorker.ready;
      if (!navigator.serviceWorker.controller) {
        await new Promise((resolve) => {
          navigator.serviceWorker.addEventListener('controllerchange', resolve, { once: true });
        });
      }
    });

    // Old SW intercepts /ar/index.html because it lacks the bypass
    await page.goto('/ar/index.html');
    await expect(page.locator('#root')).toHaveText('OLD_APP_SHELL_INTERCEPTED');

    // 3. Navigate to the real app shell at /
    await page.goto('/');
    await expect(page.locator('#root')).toBeVisible();

    // 4. Register the new production service worker /sw.js
    await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
      await new Promise((resolve) => {
        if (reg.waiting || (reg.installing && reg.installing.state === 'installed')) {
          resolve(true);
          return;
        }
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          newWorker?.addEventListener('statechange', () => {
            if (newWorker.state === 'installed') resolve(true);
          });
        });
        setTimeout(resolve, 3500);
      });
    });

    // 4. Strict Assertion: Verify the new worker is waiting and did NOT take over automatically
    await page.waitForFunction(async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      return !!reg && !!reg.waiting;
    }, { timeout: 10000 });

    const swState = await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      return {
        hasWaiting: !!reg?.waiting,
        activeScript: reg?.active?.scriptURL || '',
        waitingScript: reg?.waiting?.scriptURL || '',
      };
    });
    expect(swState.hasWaiting).toBe(true);
    expect(swState.activeScript).toContain('mock-old-sw.js');
    expect(swState.waitingScript).toContain('sw.js');

    // 5. User accepts update via UI:
    // Look for the actual update confirmation button in the application UI
    const updateButton = page.getByRole('button', { name: /حدّث الآن|Update now/i });
    if (await updateButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Click the actual user-facing acceptance button in the app UI
      await updateButton.click();
    } else {
      // Direct user acceptance signal to the waiting worker
      await page.evaluate(async () => {
        const reg = await navigator.serviceWorker.getRegistration();
        if (reg?.waiting) {
          reg.waiting.postMessage({ type: 'SKIP_WAITING' });
        }
      });
    }

    // 6. Explicit Activation Wait: Must reject/fail on timeout rather than silently passing
    await page.evaluate(async () => {
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          reject(new Error('Timed out waiting for new service worker controller to activate via controllerchange'));
        }, 8000);
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          clearTimeout(timer);
          resolve(true);
        }, { once: true });
      });
    });

    // Verify the new production worker has activated and taken control
    await page.waitForFunction(async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      return !!reg && !!reg.active && reg.active.scriptURL.includes('sw.js') && !reg.waiting;
    }, { timeout: 8000 });

    const postUpdateSw = await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      return {
        activeScript: reg?.active?.scriptURL || '',
        hasWaiting: !!reg?.waiting,
      };
    });
    expect(postUpdateSw.activeScript).toContain('sw.js');
    expect(postUpdateSw.hasWaiting).toBe(false);

    // 7. Verify public marketing page after update:
    // /ar/index.html reaches the static marketing page directly (bypasses SW network)
    await page.goto('/ar/index.html');
    await expect(page.locator('h1')).toHaveText('إدارة عيادة الأسنان من مكان واحد.');
    await expect(page.locator('#root')).toHaveCount(0); // Pure marketing HTML, NOT old app shell

    // 8. Verify known application route after update:
    // / continues to load the React app shell with login form and discovery link
    await page.goto('/');
    await expect(page.locator('#root')).toBeVisible();
    const discoveryLink = page.locator('a[href="/ar"]');
    await expect(discoveryLink).toBeVisible();

    // Clean up SW registration after test
    await page.evaluate(async () => {
      const registrations = await navigator.serviceWorker.getRegistrations();
      for (const r of registrations) await r.unregister();
    });
  });
});

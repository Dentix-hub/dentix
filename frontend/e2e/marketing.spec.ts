import { test, expect } from '@playwright/test';

for (const language of ['ar', 'en']) {
  test(`product screenshots load with correct dimensions and no external assets (${language})`, async ({ page, baseURL }) => {
    const externalRequests: string[] = [];
    const expectedOrigin = new URL(baseURL!).origin;
    page.on('request', request => {
      if (new URL(request.url()).origin !== expectedOrigin) externalRequests.push(request.url());
    });
    await page.goto(`/${language}/index.html`);
    const screenshots = page.locator('img[src^="/marketing/screens/"]');
    await expect(screenshots).toHaveCount(4);
    for (const screenshot of await screenshots.all()) {
      await screenshot.scrollIntoViewIfNeeded();
      await expect(screenshot).toBeVisible();
      await expect.poll(() => screenshot.evaluate((image: HTMLImageElement) => image.complete && image.naturalWidth > 0)).toBe(true);
      const dimensions = await screenshot.evaluate((image: HTMLImageElement) => ({
        width: image.naturalWidth, height: image.naturalHeight,
        declaredWidth: Number(image.getAttribute('width')), declaredHeight: Number(image.getAttribute('height')),
      }));
      expect(dimensions.width).toBe(dimensions.declaredWidth);
      expect(dimensions.height).toBe(dimensions.declaredHeight);
      await expect(screenshot).toHaveAttribute('alt', /\S/);
    }
    await expect(page.locator('.demo-note').first()).toContainText(language === 'ar' ? 'بيانات تجريبية' : 'Fictional');
    expect(externalRequests).toEqual([]);
  });
}

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
    await expect(h1).toHaveText('من أول حجز لآخر حساب.');

    // Canonical link
    const canonical = page.locator('link[rel="canonical"]');
    await expect(canonical).toHaveAttribute('href', 'https://www.dentixs.app/ar');

    // Bidirectional hreflang links
    await expect(page.locator('link[rel="alternate"][hreflang="ar"]')).toHaveAttribute('href', 'https://www.dentixs.app/ar');
    await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveAttribute('href', 'https://www.dentixs.app/en');
    await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveAttribute('href', 'https://www.dentixs.app/ar');

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

  test('enforces strict contract on action links: login points to / (NOT /login) and switcher points to /en', async ({ page }) => {
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

    // Language switcher link points to /en
    const langSwitcher = page.locator('a.btn-lang');
    await expect(langSwitcher).toHaveAttribute('href', '/en');
    await expect(langSwitcher).toHaveText('English');
  });

  test('verifies zero horizontal overflow across responsive viewports on Arabic page', async ({ page }) => {
    await page.goto('/ar/index.html');

    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll, 'Page must not have horizontal overflow').toBe(false);
  });

  test('audits network requests on Arabic page: zero API requests and zero POST/write operations', async ({ page }) => {
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

    const apiRequests = requestedUrls.filter((url) => url.includes('/api/'));
    expect(apiRequests, 'Marketing page must not make any /api/ calls').toHaveLength(0);
    expect(nonGetMethods, 'Marketing page must not make non-GET requests').toHaveLength(0);
  });
});

test.describe('Dentix English Marketing Page', () => {
  test('renders complete English marketing content and valid metadata', async ({ page }) => {
    await page.goto('/en/index.html');

    // Title & HTML attributes
    await expect(page).toHaveTitle('Dentix | Dental Clinic Management Software in Egypt');
    const html = page.locator('html');
    await expect(html).toHaveAttribute('lang', 'en');
    await expect(html).toHaveAttribute('dir', 'ltr');

    // Heading H1
    const h1 = page.locator('h1');
    await expect(h1).toHaveText('From the first booking to the final balance.');

    // Canonical link
    const canonical = page.locator('link[rel="canonical"]');
    await expect(canonical).toHaveAttribute('href', 'https://www.dentixs.app/en');

    // Bidirectional hreflang links
    await expect(page.locator('link[rel="alternate"][hreflang="ar"]')).toHaveAttribute('href', 'https://www.dentixs.app/ar');
    await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveAttribute('href', 'https://www.dentixs.app/en');
    await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveAttribute('href', 'https://www.dentixs.app/ar');

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

  test('enforces strict contract on action links: login points to / (NOT /login) and switcher points to /ar', async ({ page }) => {
    await page.goto('/en/index.html');

    // Check all login buttons/links on the marketing page
    const loginLinks = page.locator('a:has-text("Log in")');
    const count = await loginLinks.count();
    expect(count).toBeGreaterThanOrEqual(2);

    for (let i = 0; i < count; i++) {
      const href = await loginLinks.nth(i).getAttribute('href');
      expect(href, 'Login link must point to /').toBe('/');
      expect(href).not.toBe('/login');
    }

    // Check register link
    const registerLinks = page.locator('a:has-text("Create Clinic Account")');
    const regCount = await registerLinks.count();
    expect(regCount).toBeGreaterThanOrEqual(2);
    for (let i = 0; i < regCount; i++) {
      const href = await registerLinks.nth(i).getAttribute('href');
      expect(href).toBe('/register');
    }

    // Language switcher link points to /ar
    const langSwitcher = page.locator('a.btn-lang');
    await expect(langSwitcher).toHaveAttribute('href', '/ar');
    await expect(langSwitcher).toHaveText('العربية');
  });

  test('verifies zero horizontal overflow across responsive viewports on English page', async ({ page }) => {
    await page.goto('/en/index.html');

    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll, 'Page must not have horizontal overflow').toBe(false);
  });

  test('audits network requests on English page: zero API requests and zero POST/write operations', async ({ page }) => {
    const requestedUrls: string[] = [];
    const nonGetMethods: string[] = [];

    page.on('request', (req) => {
      requestedUrls.push(req.url());
      if (req.method() !== 'GET' && req.method() !== 'HEAD') {
        nonGetMethods.push(`${req.method()} ${req.url()}`);
      }
    });

    await page.goto('/en/index.html');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);

    const apiRequests = requestedUrls.filter((url) => url.includes('/api/'));
    expect(apiRequests, 'Marketing page must not make any /api/ calls').toHaveLength(0);
    expect(nonGetMethods, 'Marketing page must not make non-GET requests').toHaveLength(0);
  });
});

test.describe('Dentix Marketing Discovery & PWA Lifecycle', () => {
  test('verifies bidirectional discovery link on login page dynamically adapts to active language', async ({ page, javaScriptEnabled }) => {
    test.skip(!javaScriptEnabled, 'Login page is a React SPA requiring JavaScript execution to mount');
    await page.goto('/');

    // Initially in Arabic, discovery link points to /ar
    const arDiscoveryLink = page.locator('a[href="/ar"]');
    await expect(arDiscoveryLink).toBeVisible();
    await expect(arDiscoveryLink).toHaveAttribute('href', '/ar');

    // Switch language to English
    const langToggleButton = page.locator('button[title*="English"]');
    await expect(langToggleButton).toBeVisible();
    await langToggleButton.click();

    // Now discovery link dynamically points to /en
    const enDiscoveryLink = page.locator('a[href="/en"]');
    await expect(enDiscoveryLink).toBeVisible();
    await expect(enDiscoveryLink).toHaveAttribute('href', '/en');
  });

  test('captures desktop and mobile review screenshots for Arabic and English', async ({ page }, testInfo) => {
    // 1. Arabic Screenshots
    await page.goto('/ar/index.html');
    if (testInfo.project.name === 'desktop-chrome') {
      const arDesktopPath = testInfo.outputPath('marketing-ar-desktop.png');
      const buffer = await page.screenshot({ path: arDesktopPath, fullPage: true });
      await testInfo.attach('desktop-ar-screenshot', {
        body: buffer,
        contentType: 'image/png',
      });
    } else if (testInfo.project.name === 'mobile-390') {
      const arMobilePath = testInfo.outputPath('marketing-ar-mobile.png');
      const buffer = await page.screenshot({ path: arMobilePath, fullPage: true });
      await testInfo.attach('mobile-ar-screenshot', {
        body: buffer,
        contentType: 'image/png',
      });
    }

    // 2. English Screenshots
    await page.goto('/en/index.html');
    if (testInfo.project.name === 'desktop-chrome') {
      const enDesktopPath = testInfo.outputPath('marketing-en-desktop.png');
      const buffer = await page.screenshot({ path: enDesktopPath, fullPage: true });
      await testInfo.attach('desktop-en-screenshot', {
        body: buffer,
        contentType: 'image/png',
      });
    } else if (testInfo.project.name === 'mobile-390') {
      const enMobilePath = testInfo.outputPath('marketing-en-mobile.png');
      const buffer = await page.screenshot({ path: enMobilePath, fullPage: true });
      await testInfo.attach('mobile-en-screenshot', {
        body: buffer,
        contentType: 'image/png',
      });
    }
  });

  test('PWA lifecycle: old worker waits for user update, accepts SKIP_WAITING via UI, then allows /ar and /en navigation without breaking app routes', async ({ page, context, javaScriptEnabled }) => {
    test.skip(!javaScriptEnabled, 'Service worker requires JavaScript');
    // Allocate 90s budget for the multi-step lifecycle (SW registrations, UI update prompt, reloads, and navigation assertions)
    test.setTimeout(90000);

    // 1. Mock an old service worker that intercepts /ar and /en navigations (as legacy SW lacked the bypass)
    await context.route('**/mock-old-sw.js', (route) => {
      route.fulfill({
        contentType: 'application/javascript',
        body: `
          self.addEventListener('install', (e) => self.skipWaiting());
          self.addEventListener('activate', (e) => self.clients.claim());
          self.addEventListener('fetch', (e) => {
            const url = new URL(e.request.url);
            if (e.request.mode === 'navigate' && (url.pathname === '/ar' || url.pathname.startsWith('/ar/') || url.pathname === '/en' || url.pathname.startsWith('/en/'))) {
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

    // Old SW intercepts /ar/index.html and /en/index.html because it lacks the bypass
    await page.goto('/ar/index.html');
    await expect(page.locator('#root')).toHaveText('OLD_APP_SHELL_INTERCEPTED');

    await page.goto('/en/index.html');
    await expect(page.locator('#root')).toHaveText('OLD_APP_SHELL_INTERCEPTED');

    // 3. Register the new production service worker /sw.js while old SW is controlling
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
    }, undefined, { timeout: 15000 });

    const swState = await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      return {
        hasWaiting: !!reg?.waiting,
        activePath: reg?.active ? new URL(reg.active.scriptURL).pathname : '',
        waitingPath: reg?.waiting ? new URL(reg.waiting.scriptURL).pathname : '',
      };
    });
    expect(swState.hasWaiting).toBe(true);
    expect(swState.activePath).toBe('/mock-old-sw.js');
    expect(swState.waitingPath).toBe('/sw.js');

    // 5. Navigate to the application shell at /
    await page.goto('/');
    await expect(page.locator('#root')).toBeVisible();

    // 6. User accepts update via UI (NO fallback)
    const updateButton = page.getByRole('button', { name: /حدّث الآن|Update now/i });
    await expect(updateButton).toBeVisible({ timeout: 15000 });

    // 7. Ensure activation listener is attached BEFORE clicking:
    await page.evaluate(() => {
      window.__swControllerChanged = false;
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        window.__swControllerChanged = true;
      }, { once: true });
    });

    await updateButton.click();
    await page.waitForLoadState('domcontentloaded');

    // 8. Strict Verification: New production worker MUST be active and controlling, with no waiting worker
    try {
      await page.waitForFunction(async () => {
        const reg = await navigator.serviceWorker.getRegistration();
        if (!reg || !reg.active || reg.waiting) return false;
        try {
          return new URL(reg.active.scriptURL).pathname === '/sw.js';
        } catch {
          return false;
        }
      }, undefined, { timeout: 15000 });
    } catch (err) {
      const diag = await page.evaluate(async () => {
        const reg = await navigator.serviceWorker.getRegistration();
        return {
          controller: navigator.serviceWorker.controller ? {
            scriptURL: navigator.serviceWorker.controller.scriptURL,
            pathname: new URL(navigator.serviceWorker.controller.scriptURL).pathname,
            state: navigator.serviceWorker.controller.state,
          } : null,
          active: reg?.active ? {
            scriptURL: reg.active.scriptURL,
            pathname: new URL(reg.active.scriptURL).pathname,
            state: reg.active.state,
          } : null,
          waiting: reg?.waiting ? {
            scriptURL: reg.waiting.scriptURL,
            pathname: new URL(reg.waiting.scriptURL).pathname,
            state: reg.waiting.state,
          } : null,
        };
      }).catch((e) => ({ diagnosticError: e.message }));
      console.error('PWA Update Failure Diagnostics:', JSON.stringify(diag, null, 2));
      throw new Error(`Failed waiting for /sw.js activation: ${err.message}. State diagnostics: ${JSON.stringify(diag)}`);
    }

    const postUpdateSw = await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      return {
        activePath: reg?.active ? new URL(reg.active.scriptURL).pathname : '',
        controllerPath: navigator.serviceWorker.controller ? new URL(navigator.serviceWorker.controller.scriptURL).pathname : '',
        hasWaiting: !!reg?.waiting,
      };
    });
    expect(postUpdateSw.activePath).toBe('/sw.js');
    expect(postUpdateSw.hasWaiting).toBe(false);

    // 9. Verify public marketing pages after update:
    // /ar/index.html reaches the static marketing page directly
    await page.goto('/ar/index.html');
    await expect(page.locator('h1')).toHaveText('من أول حجز لآخر حساب.');
    await expect(page.locator('#root')).toHaveCount(0);

    // /en/index.html reaches the English marketing page directly
    await page.goto('/en/index.html');
    await expect(page.locator('h1')).toHaveText('From the first booking to the final balance.');
    await expect(page.locator('#root')).toHaveCount(0);

    // 10. Verify known application route after update:
    await page.goto('/');
    await expect(page.locator('#root')).toBeVisible();

    // Clean up SW registration after test
    await page.evaluate(async () => {
      const registrations = await navigator.serviceWorker.getRegistrations();
      for (const r of registrations) await r.unregister();
    });
  });
});

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
    const artifactDir = '/home/ubuntu/.gemini/antigravity-cli/brain/79a6d752-3dd6-4244-8bcf-c30c855c115c';
    await page.goto('/ar/index.html');
    if (testInfo.project.name === 'desktop-chrome') {
      await page.screenshot({ path: `${artifactDir}/marketing-ar-desktop.png`, fullPage: true });
    } else if (testInfo.project.name === 'mobile-390') {
      await page.screenshot({ path: `${artifactDir}/marketing-ar-mobile.png`, fullPage: true });
    }
  });
});

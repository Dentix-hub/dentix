import { test, expect } from '@playwright/test';

for (const language of ['ar', 'en']) {
  test(`landing motion: real screens, journey and pause control (${language})`, async ({ page }) => {
    const scripts: string[] = [];
    page.on('request', request => {
      if (request.resourceType() === 'script') scripts.push(request.url());
    });
    await page.goto(`/${language}/index.html`);
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator('.patient-journey li')).toHaveCount(3);
    for (const [time, screen] of [[1000, 'dashboard'], [5000, 'patients'], [9000, 'chart']] as const) {
      // Seek browser animations to the middle of each authored scene instead of
      // relying on load time or arbitrary multi-second sleeps.
      await page.locator('.motion-stage').evaluate((stage, milliseconds) => {
        for (const animation of stage.getAnimations({ subtree: true })) {
          animation.pause();
          animation.currentTime = milliseconds;
        }
      }, time);
      const activeLink = page.locator(`.motion-scene[href*="/${screen}-${language}.webp"]`);
      await expect(activeLink).toBeVisible();
      await expect(activeLink).toHaveCSS('opacity', '1');
      await expect(page.locator('.motion-scene:visible')).toHaveCount(1);
      await activeLink.focus();
      await expect(activeLink).toBeFocused();
    }
    // Reset the test's timeline seeking before exercising the real native input.
    await page.reload();
    await page.locator('.motion-control').click();
    await expect(page.locator('#pause-motion')).toBeChecked();
    for (const scene of await page.locator('.motion-scene').all()) {
      await expect(scene).toHaveCSS('animation-play-state', 'paused');
    }
    await page.locator('#pause-motion').press('Space');
    await page.locator('#pause-motion').evaluate((input: HTMLInputElement) => input.blur());
    await expect(page.locator('#pause-motion')).not.toBeChecked();
    await expect(page.locator('.motion-scene-1')).toHaveCSS('animation-play-state', 'running');
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    expect(scripts).toEqual([]);
  });

  test(`landing motion: reduced motion keeps readable static content (${language})`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`/${language}/index.html`);
    await expect(page.locator('.motion-scene-1')).toBeVisible();
    await expect(page.locator('.motion-scene-2')).toBeHidden();
    await expect(page.locator('.motion-scene-3')).toBeHidden();
    await expect(page.locator('.hero-title')).toHaveCSS('opacity', '1');
    await expect(page.locator('.motion-control')).toBeHidden();
    await expect(page.locator('.patient-journey li')).toHaveCount(3);
    expect(await page.locator('main').evaluate(main => main.getAnimations({ subtree: true }).length)).toBe(0);
  });
}

import { test, expect } from '@playwright/test';

const VIEWS = ['chart', 'appointments', 'patients', 'dashboard', 'finance'] as const;

for (const language of ['ar', 'en']) {
  test(`hero slideshow cycles real screens and supports accessible pause/resume (${language})`, async ({ page }) => {
    await page.goto(`/${language}/index.html`);
    const reel = page.locator('.hero-reel');
    await expect(reel).toBeVisible();

    for (const [milliseconds, activeIndex] of [[2000, 1], [6000, 2], [10000, 3], [14000, 4]] as const) {
      await reel.evaluate((el, ms) => {
        for (const anim of el.getAnimations({ subtree: true })) {
          anim.pause();
          anim.currentTime = ms;
        }
      }, milliseconds);
      await expect(page.locator(`.reel-slide-${activeIndex}`)).toHaveCSS('opacity', '1');
      for (let higher = activeIndex + 1; higher <= 4; higher++) {
        await expect(page.locator(`.reel-slide-${higher}`)).toHaveCSS('opacity', '0');
      }
    }

    await page.reload();
    const pauseToggle = page.locator('.reel-toggle');
    await expect(pauseToggle).toBeVisible();
    await pauseToggle.click();
    await expect(page.locator('#reel-pause')).toBeChecked();
    for (const idx of [2, 3, 4]) {
      await expect(page.locator(`.reel-slide-${idx}`)).toHaveCSS('animation-play-state', 'paused');
    }
    await page.locator('#reel-pause').press('Space');
    await page.mouse.move(0, 0);
    await expect(page.locator('#reel-pause')).not.toBeChecked();
    await expect(page.locator('.reel-slide-2')).toHaveCSS('animation-play-state', 'running');
  });

  test(`workspace selection by keyboard opens the correct full-size view (${language})`, async ({ page }) => {
    const scripts: string[] = [];
    page.on('request', request => {
      if (request.resourceType() === 'script') scripts.push(request.url());
    });
    await page.goto(`/${language}/index.html`);
    const forward = language === 'ar' ? 'ArrowLeft' : 'ArrowRight';
    await page.locator('#view-chart').focus();
    for (const [index, view] of VIEWS.entries()) {
      if (index > 0) await page.keyboard.press(forward);
      await expect(page.locator(`#view-${view}`)).toBeChecked();
      await expect(page.locator('.screen:visible')).toHaveCount(1);
      const preview = page.locator(`#screen-${view} .inspection`);
      await expect(preview).toBeVisible();
      await expect(preview).toHaveAttribute('aria-label', /.+/);
      await preview.press('Enter');
      const viewer = page.locator(`#zoom-${view}`);
      await expect(viewer).toBeVisible();
      await expect(viewer.locator('img')).toHaveAttribute('src', `/marketing/screens/${view}-${language}.webp`);
      await viewer.getByRole('checkbox').check();
      await expect(viewer.locator('img')).toHaveCSS('width', '1440px');
      await page.keyboard.press('Escape');
      await expect(viewer).toBeHidden();
      await page.locator(`#view-${view}`).focus();
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
    expect(scripts).toEqual([]);
  });

  test(`reduced motion keeps every manually selected screen readable (${language})`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`/${language}/index.html`);
    await expect(page.locator('.screen-chart')).toBeVisible();
    await expect(page.locator('.hero-title')).toHaveCSS('opacity', '1');
    await expect(page.locator('.reel-toggle')).toBeHidden();
    for (const view of VIEWS) {
      await page.locator(`label[for="view-${view}"]`).click();
      await expect(page.locator(`#screen-${view}`)).toBeVisible();
      expect(await page.locator('main').evaluate(main => main.getAnimations({ subtree: true }).length)).toBe(0);
    }
  });
}

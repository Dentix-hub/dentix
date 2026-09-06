import { expect, test, type Page } from '@playwright/test';

const CHART_URL = process.env.ODONTOGRAM_URL
  ?? 'http://127.0.0.1:5174/clinical-chart/demo';
const EVIDENCE_DIR = '../docs/odontogram-foundation/evidence';

async function expectNoDocumentOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
  }));

  expect(dimensions.scrollWidth, JSON.stringify(dimensions))
    .toBeLessThanOrEqual(dimensions.clientWidth + 2);
}

async function expectDesktopChartsFullyVisible(page: Page) {
  const clippedCharts = await page.locator('[data-testid="clinical-chart-instance"]')
    .evaluateAll((cards) => cards.flatMap((card) => {
      const viewport = card.querySelector('[data-chart-scroll-viewport]');
      if (!(viewport instanceof HTMLElement)) return ['missing-scroll-viewport'];

      const viewportRect = viewport.getBoundingClientRect();
      const clippedTeeth = Array.from(card.querySelectorAll('[data-layer="crown"]'))
        .filter((tooth) => {
          const toothRect = tooth.getBoundingClientRect();
          return toothRect.left < viewportRect.left - 1
            || toothRect.right > viewportRect.right + 1;
        })
        .map((tooth) => tooth.getAttribute('data-tooth-key'));

      return viewport.scrollWidth > viewport.clientWidth + 2
        ? ['internal-overflow:' + viewport.scrollWidth + ':' + viewport.clientWidth, ...clippedTeeth]
        : clippedTeeth;
    }));

  expect(clippedCharts).toEqual([]);
}

test.describe('Odontogram Part I responsive and directional evidence', () => {
  test('desktop Arabic RTL comparison is usable', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(CHART_URL);

    const workspace = page.getByTestId('clinical-chart-workspace');
    await expect(workspace).toHaveAttribute('dir', 'rtl');
    await expect(workspace).toHaveAttribute('lang', 'ar');
    await expect(page.getByTestId('clinical-chart-instance')).toHaveCount(2);
    await expect(page.getByRole('heading', { name: 'مقارنة مخطط الأسنان' })).toBeVisible();
    await expectNoDocumentOverflow(page);
    await expectDesktopChartsFullyVisible(page);

    await page.screenshot({
      fullPage: true,
      path: EVIDENCE_DIR + '/A15-desktop-ar-rtl.png',
    });
  });

  test('tablet English LTR comparison is usable', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(CHART_URL);
    await page.getByRole('button', { name: 'English' }).click();

    const workspace = page.getByTestId('clinical-chart-workspace');
    await expect(workspace).toHaveAttribute('dir', 'ltr');
    await expect(workspace).toHaveAttribute('lang', 'en');
    await expect(page.getByRole('heading', { name: 'Odontogram comparison' })).toBeVisible();
    await expectNoDocumentOverflow(page);

    await page.screenshot({
      fullPage: true,
      path: EVIDENCE_DIR + '/A15-tablet-en-ltr.png',
    });
  });

  test('mobile Arabic layout exposes quadrant navigation and keyboard focus', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(CHART_URL);

    const currentChart = page.locator('[data-chart-instance="odontogram-current"]');
    const quadrantNavigation = currentChart.getByRole('navigation', {
      name: 'انتقال سريع بين الأرباع',
    });
    await expect(quadrantNavigation).toBeVisible();
    await quadrantNavigation.getByRole('button', {
      name: 'الربع العلوي الأيمن',
    }).click();

    const chartViewport = currentChart.locator('[data-chart-scroll-viewport]');
    const targetTooth = currentChart.locator('[data-layer="crown"][data-tooth-key="14"]');
    await expect(targetTooth).toBeInViewport();
    await expect(chartViewport).toBeVisible();
    await expect(currentChart.getByRole('heading', { name: 'مخطط الأسنان (بالغين)' })).toBeVisible();

    await page.getByRole('button', { name: 'العربية' }).focus();
    await expect(page.getByRole('button', { name: 'العربية' })).toBeFocused();
    await expectNoDocumentOverflow(page);

    await page.screenshot({
      fullPage: true,
      path: EVIDENCE_DIR + '/A15-mobile-ar-rtl.png',
    });
  });
});

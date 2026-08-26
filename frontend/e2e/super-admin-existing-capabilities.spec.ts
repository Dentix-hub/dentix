import { test, expect } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

test.describe('Super Admin Existing Capabilities E2E (MS-37)', () => {
    test.beforeEach(async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('i18nextLng', 'ar');
        });
        await loginAsSuperAdmin(page);
    });

    test('navigates through core Super Admin pages without unhandled crashes or overflow', async ({ page }) => {
        const superAdminRoutes = [
            '/admin',
            '/admin/tenants',
            '/admin/users',
            '/admin/finance',
            '/admin/system/logs',
            '/admin/settings',
            '/ai/stats',
        ];

        for (const route of superAdminRoutes) {
            await page.goto(`${BASE_URL}${route}`);
            await page.waitForLoadState('networkidle');
            await expect(page.locator('body')).not.toContainText(/Something went wrong|Cannot read properties of undefined/i);

            const dimensions = await page.evaluate(() => ({
                scrollWidth: document.documentElement.scrollWidth,
                clientWidth: document.documentElement.clientWidth,
            }));
            expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 5);
        }
    });

    test('tenant impersonation requires a minimum five-character reason', async ({ page }) => {
        await page.goto(`${BASE_URL}/admin/tenants`);
        const tenantRow = page.locator('tbody tr').filter({ hasText: 'Dentix E2E Clinic' }).first();
        await expect(tenantRow).toBeVisible({ timeout: 10000 });
        await tenantRow.getByRole('button').first().click();

        const reasonInput = page.getByLabel(/سبب الدخول|Reason for access/i);
        await expect(reasonInput).toBeVisible({ timeout: 10000 });
        const enterButton = page.getByRole('button', { name: /دخول مؤقت للنظام|Start temporary access/i });

        await reasonInput.fill('test');
        await expect(enterButton).toBeDisabled();

        await reasonInput.fill('Supervision and support inspection');
        await expect(enterButton).toBeEnabled();
    });
});

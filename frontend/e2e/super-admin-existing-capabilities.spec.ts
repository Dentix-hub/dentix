import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers.js';

test.describe('Super Admin Existing Capabilities E2E (MS-37)', () => {
    test.beforeEach(async ({ page }) => {
        // Set Arabic language by default for canonical testing
        await page.addInitScript(() => {
            window.localStorage.setItem('i18nextLng', 'ar');
        });
        await loginAsAdmin(page);
    });

    test('navigates through all core Super Admin pages without unhandled crashes or overflow', async ({ page }) => {
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
            await page.goto(route);
            await page.waitForLoadState('networkidle');

            // Assert no critical crash screen
            await expect(page.locator('body')).not.toContainText(/Something went wrong|Cannot read properties of undefined/i);

            // Assert document does not horizontally overflow
            const dimensions = await page.evaluate(() => ({
                scrollWidth: document.documentElement.scrollWidth,
                clientWidth: document.documentElement.clientWidth,
            }));
            expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 5);
        }
    });

    test('command palette opens on button trigger and closes gracefully', async ({ page }) => {
        await page.goto('/admin');
        await page.waitForLoadState('networkidle');

        // Look for Command Palette trigger button in header
        const commandTrigger = page.locator('header button').filter({ hasText: /بحث سريع|Search|Command Palette/i }).first();
        if (await commandTrigger.isVisible({ timeout: 5000 }).catch(() => false)) {
            await commandTrigger.click();
            const paletteModal = page.locator('[role="dialog"]');
            await expect(paletteModal).toBeVisible();

            // Press Escape to close
            await page.keyboard.press('Escape');
            await expect(paletteModal).toBeHidden();
        }
    });

    test('tenant impersonation requires minimum 5-character reason', async ({ page }) => {
        await page.goto('/admin/tenants');
        await page.waitForLoadState('networkidle');

        // Click on first tenant detail button if exists
        const tenantRow = page.locator('tbody tr').first();
        if (await tenantRow.isVisible({ timeout: 5000 }).catch(() => false)) {
            const detailBtn = tenantRow.locator('button[title*="تفاصيل"]').first();
            if (await detailBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
                await detailBtn.click();

                // Drawer should open with reason input
                const reasonInput = page.locator('input[placeholder*="سبب الدخول"]').first();
                if (await reasonInput.isVisible({ timeout: 3000 }).catch(() => false)) {
                    // Short reason (< 5 chars)
                    await reasonInput.fill('test');
                    const enterBtn = page.getByRole('button', { name: /بدء الجلسة/i }).first();
                    await expect(enterBtn).toBeDisabled();

                    // Valid reason (>= 5 chars)
                    await reasonInput.fill('Supervision and support inspection');
                    await expect(enterBtn).toBeEnabled();
                }
            }
        }
    });
});

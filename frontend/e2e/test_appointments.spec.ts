import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

async function openAppointments(page) {
  await page.goto(`${BASE_URL}/appointments`);
  await expect(page).toHaveURL(/.*appointments/);
  await expect(page.locator('h1').first()).toBeVisible({ timeout: 15000 });
}

test.describe('Appointments Management', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('APPT-01: Appointments workspace loads on an empty or populated clinic', async ({ page }) => {
    await openAppointments(page);
    await expect(page.locator('body')).not.toContainText(/Application Error|Something went wrong/i);

    // Current page always exposes three view controls plus the new-booking action,
    // even when the data area is an EmptyState instead of a calendar/table.
    const titledViewButtons = page.locator('button[title]');
    expect(await titledViewButtons.count()).toBeGreaterThanOrEqual(3);
  });

  test('APPT-02: New booking modal opens with the current form', async ({ page }) => {
    await openAppointments(page);

    const newBooking = page
      .getByRole('button')
      .filter({ hasText: /حجز|موعد|Booking|Appointment/i })
      .first();
    await expect(newBooking).toBeVisible({ timeout: 10000 });
    await newBooking.click();

    await expect(page.locator('input[type="datetime-local"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('APPT-03: Calendar, list and board view controls are available', async ({ page }) => {
    await openAppointments(page);

    const viewButtons = page.locator('button[title]');
    expect(await viewButtons.count()).toBeGreaterThanOrEqual(3);

    // Exercise each view toggle. Empty clinics may continue showing EmptyState,
    // but changing the view must not crash the page.
    for (const button of await viewButtons.all()) {
      await button.click();
      await expect(page.locator('body')).not.toContainText(/Application Error|Something went wrong/i);
    }
  });

  test('APPT-04: Empty-state booking action remains usable when there are no appointments', async ({ page }) => {
    await openAppointments(page);

    const dataRows = page.locator('table tbody tr');
    if ((await dataRows.count()) === 0) {
      const bookingActions = page
        .getByRole('button')
        .filter({ hasText: /إضافة.*موعد|موعد|Appointment|Booking/i });
      expect(await bookingActions.count()).toBeGreaterThan(0);
    }
  });
});

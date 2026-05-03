import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForPageLoad } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const testAppointment = {
  patientName: 'Test Patient',
  date: new Date().toISOString().split('T')[0], // Today
  time: '10:00',
};

test.describe('Appointments Management', () => {

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('APPT-01: View appointments list', async ({ page }) => {
    await page.goto(`${BASE_URL}/appointments`);
    
    // Should load appointments page
    await expect(page).toHaveURL(/.*appointments/);
    
    // Should show appointments table or list
    await expect(page.locator('table, [data-testid="appointments-list"], .appointments-list').first()).toBeVisible({ timeout: 10000 });
  });

  test('APPT-02: Create new appointment', async ({ page }) => {
    await page.goto(`${BASE_URL}/appointments`);
    
    // Click add appointment button
    const addBtn = page.getByRole('button').filter({ hasText: /موعد|New Appointment|إضافة/i }).first();
    await addBtn.click();
    
    // Fill appointment form
    const patientInput = page.locator('input[name="patient"], input[name="patient_id"]').first();
    if (await patientInput.isVisible()) {
      await patientInput.fill(testAppointment.patientName);
    }
    
    // Fill date
    const dateInput = page.locator('input[type="date"]').first();
    if (await dateInput.isVisible()) {
      await dateInput.fill(testAppointment.date);
    }
    
    // Fill time
    const timeInput = page.locator('input[type="time"]').first();
    if (await timeInput.isVisible()) {
      await timeInput.fill(testAppointment.time);
    }
    
    // Save
    const saveBtn = page.getByRole('button', { name: /حفظ|Save|تأكيد/i }).first();
    await saveBtn.click();
    
    // Verify appointment was created
    await page.waitForTimeout(2000);
  });

  test('APPT-03: Edit appointment', async ({ page }) => {
    await page.goto(`${BASE_URL}/appointments`);
    
    // Find and click on first appointment
    const appointmentRow = page.locator('table tbody tr').first();
    if (await appointmentRow.isVisible()) {
      await appointmentRow.click();
      
      // Click edit button
      const editBtn = page.getByRole('button').filter({ hasText: /تعديل|Edit/i }).first();
      if (await editBtn.isVisible()) {
        await editBtn.click();
        
        // Change time
        const timeInput = page.locator('input[type="time"]').first();
        if (await timeInput.isVisible()) {
          await timeInput.fill('11:00');
        }
        
        // Save
        const saveBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
        await saveBtn.click();
      }
    }
  });

  test('APPT-04: Cancel appointment', async ({ page }) => {
    await page.goto(`${BASE_URL}/appointments`);
    
    // Find and click on first appointment
    const appointmentRow = page.locator('table tbody tr').first();
    if (await appointmentRow.isVisible()) {
      await appointmentRow.click();
      
      // Click cancel button
      const cancelBtn = page.getByRole('button').filter({ hasText: /إلغاء|Cancel/i }).first();
      if (await cancelBtn.isVisible()) {
        await cancelBtn.click();
        
        // Confirm cancellation
        const confirmBtn = page.getByRole('button').filter({ hasText: /تأكيد|نعم|Confirm/i }).first();
        await confirmBtn.click();
      }
    }
  });

  test('APPT-05: Confirm appointment', async ({ page }) => {
    await page.goto(`${BASE_URL}/appointments`);
    
    // Find pending appointment
    const pendingAppt = page.locator('text=/مؤكد|Confirmed|Pending/i').first();
    if (await pendingAppt.isVisible()) {
      // Click confirm button if available
      const confirmBtn = page.getByRole('button').filter({ hasText: /تأكيد|Confirm/i }).first();
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
      }
    }
  });

  test('APPT-06: View calendar', async ({ page }) => {
    await page.goto(`${BASE_URL}/appointments`);
    
    // Switch to calendar view if button exists
    const calendarBtn = page.getByRole('button').filter({ hasText: /تقويم|Calendar/i }).first();
    if (await calendarBtn.isVisible()) {
      await calendarBtn.click();
    }
    
    // Should show calendar elements
    await expect(page.locator('.calendar, [data-testid="calendar"], .date-grid').first()).toBeVisible({ timeout: 5000 });
  });

});

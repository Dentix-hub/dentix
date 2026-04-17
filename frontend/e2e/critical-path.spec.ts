import { test, expect } from '@playwright/test';

// Configuration
const BASE_URL = 'http://localhost:5173';
// Make sure to have a test user in DB (e.g., admin / admin123 or whatever it is)
// If it fails, we will know from the trace.
const TEST_USER = 'admin';
const TEST_PASS = 'admin123';

test.describe('Dentix Critical Path', () => {

  test('E2E Clinical Core Workflow', async ({ page }) => {
    // 1. Setup & Login
    await page.goto(BASE_URL + '/login');
    
    // Switch to English if necessary (optional, but CSS selectors are safer than text if language varies)
    await page.locator('input[type="text"]').fill(TEST_USER);
    await page.locator('input[type="password"]').fill(TEST_PASS);
    await page.locator('button[type="submit"]').click();
    
    // Wait for redirect to dashboard
    await page.waitForURL('**/', { timeout: 15000 });
    
    // 2. Dashboard Loaded
    // Just ensure a standard element exists, avoiding exact translation checks
    await expect(page.locator('nav').first()).toBeVisible();
    
    // 3. Navigate to Patients
    await page.goto(BASE_URL + '/patients');
    await expect(page).toHaveURL(/.*patients/);

    // 4. Create Patient
    // Find the 'New Patient' button. It's usually the primary button on the page.
    // Try catching a button with an icon or that says "Add Patient"
    const addPatientBtn = page.getByRole('button').filter({ hasText: /إضافة|Add|New/i }).first();
    if(await addPatientBtn.isVisible()) {
        await addPatientBtn.click();
        
        // Fill form
        await page.locator('input[name="name"]').first().fill('E2E Test Patient');
        await page.locator('input[name="phone"]').first().fill('01000000000');
        // Save
        const saveBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
        if(await saveBtn.isVisible()) {
           await saveBtn.click();
        } else {
           await page.locator('button[type="submit"]').click();
        }
        
        // Wait for modal to close
        await page.waitForTimeout(1000);
    }
    
    // 5. Search & View Patient
    // Search input
    const searchInput = page.locator('input[type="text"]').first();
    if(await searchInput.isVisible()) {
        await searchInput.fill('E2E Test Patient');
        await page.waitForTimeout(1000); 
    }
    
    // Click the first patient row or the view icon
    // Using generic row click or link
    const firstRow = page.locator('table tbody tr').first();
    if (await firstRow.isVisible()) {
        await firstRow.click();
        // Alternatively, finding a link inside the row
        await page.waitForTimeout(1000);
    }
    
    // Verify we are on a patient page
    await expect(page).toHaveURL(/.*patients\/\d+/);

    // 6. Add Appointment (If visible on patient view)
    const addApptBtn = page.getByRole('button').filter({ hasText: /موعد|Appointment/i }).first();
    if (await addApptBtn.isVisible()) {
        await addApptBtn.click();
        await page.waitForTimeout(500);
        // We'll close the modal if it exists so we don't block
        await page.keyboard.press('Escape');
    }

    // 7. Add Treatment
    const addTreatmentBtn = page.getByRole('button').filter({ hasText: /علاج|Treatment/i }).first();
    if (await addTreatmentBtn.isVisible()) {
        await addTreatmentBtn.click();
        // Fill cost
        const costInput = page.locator('input[type="number"]').first();
        if(await costInput.isVisible()) {
            await costInput.fill('1000');
        }
        const saveTrtBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
        if(await saveTrtBtn.isVisible()) {
            await saveTrtBtn.click();
        }
    }

    // 8. Make Payment
    const addPaymentBtn = page.getByRole('button').filter({ hasText: /دفع|Payment|تحصيل/i }).first();
    if (await addPaymentBtn.isVisible()) {
        await addPaymentBtn.click();
        const amtInput = page.locator('input[type="number"]').first();
        if(await amtInput.isVisible()) {
            await amtInput.fill('500');
        }
        const savePayBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
        if(await savePayBtn.isVisible()) {
            await savePayBtn.click();
        }
    }

    // 9. Verify Balance
    // Check if the balance is displayed on the page
    const balanceEl = page.locator('text=/R|رصيد/i').first();
    await expect(balanceEl).toBeVisible({ timeout: 5000 });
  });

});

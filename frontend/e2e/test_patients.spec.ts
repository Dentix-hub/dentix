import { test, expect } from '@playwright/test';
import { loginAsAdmin, generateRandomName, generateRandomPhone, waitForPageLoad } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const testPatient = {
  name: generateRandomName('Patient'),
  phone: generateRandomPhone(),
  age: 30,
};

test.describe('Patients Management', () => {

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('PAT-01: View patients list', async ({ page }) => {
    await page.goto(`${BASE_URL}/patients`);
    
    // Should load patients page
    await expect(page).toHaveURL(/.*patients/);
    
    // Should show patients table or list
    await expect(page.locator('table, [data-testid="patients-list"], .patients-list').first()).toBeVisible({ timeout: 10000 });
  });

  test('PAT-02: Create new patient', async ({ page }) => {
    await page.goto(`${BASE_URL}/patients`);
    
    // Click add patient button
    const addBtn = page.getByRole('button').filter({ hasText: /إضافة|Make Appointment|New Patient/i }).first();
    await addBtn.click();
    
    // Fill patient form
    await page.locator('input[name="name"]').first().fill(testPatient.name);
    await page.locator('input[name="phone"]').first().fill(testPatient.phone);
    
    // Try to find age field
    const ageField = page.locator('input[name="age"]');
    if (await ageField.isVisible()) {
      await ageField.fill(testPatient.age.toString());
    }
    
    // Save
    const saveBtn = page.getByRole('button', { name: /حفظ|Save|تأكيد/i }).first();
    if (await saveBtn.isVisible()) {
      await saveBtn.click();
    } else {
      await page.locator('button[type="submit"]').click();
    }
    
    // Verify patient was created
    await page.waitForTimeout(2000);
    
    // Should see the new patient in the list
    const patientRow = page.locator('text=' + testPatient.name);
    await expect(patientRow.first()).toBeVisible({ timeout: 5000 });
  });

  test('PAT-03: Edit patient information', async ({ page }) => {
    await page.goto(`${BASE_URL}/patients`);
    
    // Find and click on the test patient
    const patientRow = page.locator(`text=${testPatient.name}`);
    if (await patientRow.isVisible()) {
      await patientRow.first().click();
      
      // Click edit button
      const editBtn = page.getByRole('button').filter({ hasText: /تعديل|Edit/i }).first();
      await editBtn.click();
      
      // Change name
      const nameField = page.locator('input[name="name"]').first();
      await nameField.fill(testPatient.name + ' Updated');
      
      // Save
      const saveBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
      await saveBtn.click();
      
      // Verify update
      await expect(page.locator(`text=${testPatient.name} Updated`)).toBeVisible();
    }
  });

  test('PAT-04: Search patient by name', async ({ page }) => {
    await page.goto(`${BASE_URL}/patients`);
    
    // Find search input
    const searchInput = page.locator('input[placeholder*="بحث"], input[name="search"]').first();
    await searchInput.fill(testPatient.name);
    
    // Wait for results
    await page.waitForTimeout(1000);
    
    // Should show the patient in results
    const patientRow = page.locator(`text=${testPatient.name}`);
    await expect(patientRow.first()).toBeVisible();
  });

  test('PAT-05: Search patient by phone', async ({ page }) => {
    await page.goto(`${BASE_URL}/patients`);
    
    // Find search input
    const searchInput = page.locator('input[placeholder*="بحث"], input[name="search"]').first();
    await searchInput.fill(testPatient.phone);
    
    // Wait for results
    await page.waitForTimeout(1000);
    
    // Should show the patient in results
    const patientRow = page.locator(`text=${testPatient.name}`);
    await expect(patientRow.first()).toBeVisible();
  });

  test('PAT-06: View patient details', async ({ page }) => {
    await page.goto(`${BASE_URL}/patients`);
    
    // Click on patient
    const patientRow = page.locator(`text=${testPatient.name}`);
    if (await patientRow.isVisible()) {
      await patientRow.first().click();
      
      // Should show patient details
      await expect(page.locator('h1, h2, [data-testid="patient-name"]')).toBeVisible({ timeout: 5000 });
    }
  });

  test('PAT-07: Delete patient (soft delete)', async ({ page }) => {
    await page.goto(`${BASE_URL}/patients`);
    
    // Find and click on the test patient
    const patientRow = page.locator(`text=${testPatient.name}`);
    if (await patientRow.isVisible()) {
      await patientRow.first().click();
      
      // Click delete button
      const deleteBtn = page.getByRole('button').filter({ hasText: /حذف|Delete/i }).first();
      await deleteBtn.click();
      
      // Confirm deletion in modal
      const confirmBtn = page.getByRole('button').filter({ hasText: /تأكيد|نعم|Confirm/i }).first();
      await confirmBtn.click();
      
      // Verify patient is not visible
      await page.waitForTimeout(1000);
      await expect(page.locator(`text=${testPatient.name}`)).not.toBeVisible();
    }
  });

});

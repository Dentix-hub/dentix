# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: critical-path.spec.ts >> Dentix Critical Path >> E2E Clinical Core Workflow
- Location: e2e\critical-path.spec.ts:12:3

# Error details

```
TimeoutError: page.waitForURL: Timeout 15000ms exceeded.
=========================== logs ===========================
waiting for navigation to "**/" until "load"
============================================================
```

# Page snapshot

```yaml
- generic [ref=e4]:
  - generic [ref=e5]:
    - button "Switch to English" [ref=e6] [cursor=pointer]:
      - img [ref=e7]
    - img "DENTIX Logo" [ref=e11]
    - button [ref=e12] [cursor=pointer]:
      - img [ref=e13]
  - generic [ref=e15]: Method Not Allowed
  - generic [ref=e16]:
    - textbox "اسم المستخدم" [ref=e18]: admin
    - textbox "كلمة المرور" [ref=e20]: admin123
    - generic [ref=e21]:
      - link "نسيت كلمة المرور؟" [ref=e22] [cursor=pointer]:
        - /url: /forgot-password
      - generic [ref=e23]:
        - generic [ref=e24] [cursor=pointer]: تذكرني
        - checkbox "تذكرني" [ref=e25] [cursor=pointer]
    - button "تسجيل الدخول" [active] [ref=e26] [cursor=pointer]
    - link "تسجيل عيادة جديدة" [ref=e28] [cursor=pointer]:
      - /url: /register
  - generic [ref=e29]:
    - generic [ref=e30]:
      - link "شروط الاستخدام" [ref=e31] [cursor=pointer]:
        - /url: /terms
      - generic [ref=e32]: •
      - link "سياسة الخصوصية" [ref=e33] [cursor=pointer]:
        - /url: /privacy
    - paragraph [ref=e34]: © 2026 جميع الحقوق محفوظة Smart Clinic
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | // Configuration
  4   | const BASE_URL = 'http://localhost:5173';
  5   | // Make sure to have a test user in DB (e.g., admin / admin123 or whatever it is)
  6   | // If it fails, we will know from the trace.
  7   | const TEST_USER = 'admin';
  8   | const TEST_PASS = 'admin123';
  9   | 
  10  | test.describe('Dentix Critical Path', () => {
  11  | 
  12  |   test('E2E Clinical Core Workflow', async ({ page }) => {
  13  |     // 1. Setup & Login
  14  |     await page.goto(BASE_URL + '/login');
  15  |     
  16  |     // Switch to English if necessary (optional, but CSS selectors are safer than text if language varies)
  17  |     await page.locator('input[type="text"]').fill(TEST_USER);
  18  |     await page.locator('input[type="password"]').fill(TEST_PASS);
  19  |     await page.locator('button[type="submit"]').click();
  20  |     
  21  |     // Wait for redirect to dashboard
> 22  |     await page.waitForURL('**/', { timeout: 15000 });
      |                ^ TimeoutError: page.waitForURL: Timeout 15000ms exceeded.
  23  |     
  24  |     // 2. Dashboard Loaded
  25  |     // Just ensure a standard element exists, avoiding exact translation checks
  26  |     await expect(page.locator('nav').first()).toBeVisible();
  27  |     
  28  |     // 3. Navigate to Patients
  29  |     await page.goto(BASE_URL + '/patients');
  30  |     await expect(page).toHaveURL(/.*patients/);
  31  | 
  32  |     // 4. Create Patient
  33  |     // Find the 'New Patient' button. It's usually the primary button on the page.
  34  |     // Try catching a button with an icon or that says "Add Patient"
  35  |     const addPatientBtn = page.getByRole('button').filter({ hasText: /إضافة|Add|New/i }).first();
  36  |     if(await addPatientBtn.isVisible()) {
  37  |         await addPatientBtn.click();
  38  |         
  39  |         // Fill form
  40  |         await page.locator('input[name="name"]').first().fill('E2E Test Patient');
  41  |         await page.locator('input[name="phone"]').first().fill('01000000000');
  42  |         // Save
  43  |         const saveBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
  44  |         if(await saveBtn.isVisible()) {
  45  |            await saveBtn.click();
  46  |         } else {
  47  |            await page.locator('button[type="submit"]').click();
  48  |         }
  49  |         
  50  |         // Wait for modal to close
  51  |         await page.waitForTimeout(1000);
  52  |     }
  53  |     
  54  |     // 5. Search & View Patient
  55  |     // Search input
  56  |     const searchInput = page.locator('input[type="text"]').first();
  57  |     if(await searchInput.isVisible()) {
  58  |         await searchInput.fill('E2E Test Patient');
  59  |         await page.waitForTimeout(1000); 
  60  |     }
  61  |     
  62  |     // Click the first patient row or the view icon
  63  |     // Using generic row click or link
  64  |     const firstRow = page.locator('table tbody tr').first();
  65  |     if (await firstRow.isVisible()) {
  66  |         await firstRow.click();
  67  |         // Alternatively, finding a link inside the row
  68  |         await page.waitForTimeout(1000);
  69  |     }
  70  |     
  71  |     // Verify we are on a patient page
  72  |     await expect(page).toHaveURL(/.*patients\/\d+/);
  73  | 
  74  |     // 6. Add Appointment (If visible on patient view)
  75  |     const addApptBtn = page.getByRole('button').filter({ hasText: /موعد|Appointment/i }).first();
  76  |     if (await addApptBtn.isVisible()) {
  77  |         await addApptBtn.click();
  78  |         await page.waitForTimeout(500);
  79  |         // We'll close the modal if it exists so we don't block
  80  |         await page.keyboard.press('Escape');
  81  |     }
  82  | 
  83  |     // 7. Add Treatment
  84  |     const addTreatmentBtn = page.getByRole('button').filter({ hasText: /علاج|Treatment/i }).first();
  85  |     if (await addTreatmentBtn.isVisible()) {
  86  |         await addTreatmentBtn.click();
  87  |         // Fill cost
  88  |         const costInput = page.locator('input[type="number"]').first();
  89  |         if(await costInput.isVisible()) {
  90  |             await costInput.fill('1000');
  91  |         }
  92  |         const saveTrtBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
  93  |         if(await saveTrtBtn.isVisible()) {
  94  |             await saveTrtBtn.click();
  95  |         }
  96  |     }
  97  | 
  98  |     // 8. Make Payment
  99  |     const addPaymentBtn = page.getByRole('button').filter({ hasText: /دفع|Payment|تحصيل/i }).first();
  100 |     if (await addPaymentBtn.isVisible()) {
  101 |         await addPaymentBtn.click();
  102 |         const amtInput = page.locator('input[type="number"]').first();
  103 |         if(await amtInput.isVisible()) {
  104 |             await amtInput.fill('500');
  105 |         }
  106 |         const savePayBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
  107 |         if(await savePayBtn.isVisible()) {
  108 |             await savePayBtn.click();
  109 |         }
  110 |     }
  111 | 
  112 |     // 9. Verify Balance
  113 |     // Check if the balance is displayed on the page
  114 |     const balanceEl = page.locator('text=/R|رصيد/i').first();
  115 |     await expect(balanceEl).toBeVisible({ timeout: 5000 });
  116 |   });
  117 | 
  118 | });
  119 | 
```
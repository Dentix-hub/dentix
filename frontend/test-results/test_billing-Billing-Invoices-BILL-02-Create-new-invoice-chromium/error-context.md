# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_billing.spec.ts >> Billing & Invoices >> BILL-02: Create new invoice
- Location: e2e\test_billing.spec.ts:22:3

# Error details

```
TimeoutError: page.waitForURL: Timeout 15000ms exceeded.
=========================== logs ===========================
waiting for navigation to "http://localhost:5173/" until "load"
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
  1  | /**
  2  |  * Test Helpers - Utility functions for E2E tests
  3  |  */
  4  | 
  5  | const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
  6  | 
  7  | // Login as a specific role
  8  | export async function loginAs(page, username, password) {
  9  |   await page.goto(`${BASE_URL}/login`);
  10 |   await page.locator('input[type="text"]').fill(username);
  11 |   await page.locator('input[type="password"]').fill(password);
  12 |   await page.locator('button[type="submit"]').click();
> 13 |   await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
     |              ^ TimeoutError: page.waitForURL: Timeout 15000ms exceeded.
  14 | }
  15 | 
  16 | // Login as admin (default)
  17 | export async function loginAsAdmin(page) {
  18 |   return loginAs(page, 'admin', 'admin123');
  19 | }
  20 | 
  21 | // Login as doctor
  22 | export async function loginAsDoctor(page) {
  23 |   return loginAs(page, 'doctor1', 'doc123');
  24 | }
  25 | 
  26 | // Login as nurse
  27 | export async function loginAsNurse(page) {
  28 |   return loginAs(page, 'nurse1', 'nurse123');
  29 | }
  30 | 
  31 | // Login as receptionist
  32 | export async function loginAsReceptionist(page) {
  33 |   return loginAs(page, 'reception1', 'rec123');
  34 | }
  35 | 
  36 | // Login as accountant
  37 | export async function loginAsAccountant(page) {
  38 |   return loginAs(page, 'account1', 'acc123');
  39 | }
  40 | 
  41 | // Logout
  42 | export async function logout(page) {
  43 |   // Try to find logout button
  44 |   const logoutBtn = page.getByRole('button').filter({ hasText: /خروج|Logout|تسجيل الخروج/i }).first();
  45 |   if (await logoutBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
  46 |     await logoutBtn.click();
  47 |   } else {
  48 |     // Try profile menu
  49 |     await page.locator('[data-testid="user-menu"], header button').first().click();
  50 |     await logoutBtn.click();
  51 |   }
  52 |   await page.waitForURL(`${BASE_URL}/login`);
  53 | }
  54 | 
  55 | // Generate random test data
  56 | export function generateRandomName(prefix = 'Test') {
  57 |   return `${prefix}_${Date.now()}_${Math.random().toString(36).substring(7)}`;
  58 | }
  59 | 
  60 | export function generateRandomPhone() {
  61 |   return '010' + Math.floor(Math.random() * 100000000).toString().padStart(8, '0');
  62 | }
  63 | 
  64 | export function generateRandomEmail() {
  65 |   return `test_${Date.now()}@example.com`;
  66 | }
  67 | 
  68 | // Wait for page to be fully loaded
  69 | export async function waitForPageLoad(page) {
  70 |   await page.waitForLoadState('networkidle');
  71 |   await page.waitForTimeout(500);
  72 | }
  73 | 
  74 | // Navigate to a route and wait for it to load
  75 | export async function navigateTo(page, route) {
  76 |   await page.goto(`${BASE_URL}${route}`);
  77 |   await waitForPageLoad(page);
  78 | }
  79 | 
```
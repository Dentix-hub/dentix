# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: critical-path.spec.js >> Dentix Critical Path >> 5 — RBAC: unauthenticated access redirects to login
- Location: e2e\critical-path.spec.js:41:3

# Error details

```
Error: expect(page).toHaveURL(expected) failed

Expected pattern: /login/
Received string:  "http://localhost:5173/dashboard"
Timeout: 10000ms

Call log:
  - Expect "toHaveURL" with timeout 10000ms
    13 × unexpected value "http://localhost:5173/dashboard"

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
  - generic [ref=e15]:
    - textbox "اسم المستخدم" [ref=e17]
    - textbox "كلمة المرور" [ref=e19]
    - generic [ref=e20]:
      - link "نسيت كلمة المرور؟" [ref=e21] [cursor=pointer]:
        - /url: /forgot-password
      - generic [ref=e22]:
        - generic [ref=e23] [cursor=pointer]: تذكرني
        - checkbox "تذكرني" [ref=e24] [cursor=pointer]
    - button "تسجيل الدخول" [ref=e25] [cursor=pointer]
    - link "تسجيل عيادة جديدة" [ref=e27] [cursor=pointer]:
      - /url: /register
  - generic [ref=e28]:
    - generic [ref=e29]:
      - link "شروط الاستخدام" [ref=e30] [cursor=pointer]:
        - /url: /terms
      - generic [ref=e31]: •
      - link "سياسة الخصوصية" [ref=e32] [cursor=pointer]:
        - /url: /privacy
    - paragraph [ref=e33]: © 2026 جميع الحقوق محفوظة Smart Clinic
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | const BASE = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173';
  4  | const ADMIN = { email: 'admin@test.com', password: 'TestPass1!' };
  5  | 
  6  | test.describe('Dentix Critical Path', () => {
  7  | 
  8  |   test('1 — login and reach dashboard', async ({ page }) => {
  9  |     await page.goto(`${BASE}/login`);
  10 |     
  11 |     // Fill login form
  12 |     await page.fill('input[type="text"]', ADMIN.email);
  13 |     await page.fill('input[type="password"]', ADMIN.password);
  14 |     await page.click('button[type="submit"]');
  15 |     
  16 |     // Should redirect to dashboard
  17 |     await expect(page).toHaveURL(/(\/|dashboard)/);
  18 |   });
  19 | 
  20 |   test('2 — navigate to patients', async ({ page }) => {
  21 |     await page.goto(`${BASE}/patients`);
  22 |     
  23 |     // Should load patients page
  24 |     await expect(page.locator('h1, h2, [data-testid="patients-title"]')).toBeVisible();
  25 |   });
  26 | 
  27 |   test('3 — navigate to appointments', async ({ page }) => {
  28 |     await page.goto(`${BASE}/appointments`);
  29 |     
  30 |     // Should load appointments page
  31 |     await expect(page.locator('h1, h2, [data-testid="appointments-title"]')).toBeVisible();
  32 |   });
  33 | 
  34 |   test('4 — navigate to billing', async ({ page }) => {
  35 |     await page.goto(`${BASE}/billing`);
  36 |     
  37 |     // Should load billing page or redirect (RBAC)
  38 |     await expect(page.locator('h1, h2, [data-testid="billing-title"], body')).toBeVisible();
  39 |   });
  40 | 
  41 |   test('5 — RBAC: unauthenticated access redirects to login', async ({ page }) => {
  42 |     await page.goto(`${BASE}/dashboard`);
  43 |     
  44 |     // Should redirect to login
> 45 |     await expect(page).toHaveURL(/login/);
     |                        ^ Error: expect(page).toHaveURL(expected) failed
  46 |   });
  47 | 
  48 | });
  49 | 
```
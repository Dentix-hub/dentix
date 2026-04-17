# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_auth.spec.ts >> Authentication Flow >> AUTH-03: Failed Login with non-existent user
- Location: e2e\test_auth.spec.ts:41:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=/خطأ|Error|Invalid|Not Found/i')
Expected: visible
Timeout: 10000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 10000ms
  - waiting for locator('text=/خطأ|Error|Invalid|Not Found/i')

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
    - textbox "اسم المستخدم" [ref=e18]: nonexistent_user_12345
    - textbox "كلمة المرور" [ref=e20]: anypassword
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
  1  | import { test, expect } from '@playwright/test';
  2  | import { loginAs, loginAsAdmin, logout } from './helpers.js';
  3  | 
  4  | const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
  5  | const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';
  6  | 
  7  | test.describe('Authentication Flow', () => {
  8  | 
  9  |   test('AUTH-01: Successful Login with admin credentials', async ({ page }) => {
  10 |     await page.goto(`${BASE_URL}/login`);
  11 |     
  12 |     // Check for login page elements
  13 |     await expect(page.locator('input[type="text"]')).toBeVisible();
  14 |     await expect(page.locator('input[type="password"]')).toBeVisible();
  15 |     
  16 |     // Fill credentials
  17 |     await page.locator('input[type="text"]').fill(users.admin.username);
  18 |     await page.locator('input[type="password"]').fill(users.admin.password);
  19 |     await page.locator('button[type="submit"]').click();
  20 |     
  21 |     // Verify redirection to dashboard
  22 |     await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
  23 |     await expect(page.locator('nav')).toBeVisible();
  24 |   });
  25 | 
  26 |   test('AUTH-02: Failed Login with incorrect password', async ({ page }) => {
  27 |     await page.goto(`${BASE_URL}/login`);
  28 |     
  29 |     await page.locator('input[type="text"]').fill(users.admin.username);
  30 |     await page.locator('input[type="password"]').fill('wrongpassword');
  31 |     await page.locator('button[type="submit"]').click();
  32 |     
  33 |     // Expect error message
  34 |     const errorMsg = page.locator('text=/خطأ|Error|Invalid|Unauthorized/i');
  35 |     await expect(errorMsg).toBeVisible({ timeout: 10000 });
  36 |     
  37 |     // Should still be on login page
  38 |     await expect(page).toHaveURL(/login/);
  39 |   });
  40 | 
  41 |   test('AUTH-03: Failed Login with non-existent user', async ({ page }) => {
  42 |     await page.goto(`${BASE_URL}/login`);
  43 |     
  44 |     await page.locator('input[type="text"]').fill('nonexistent_user_12345');
  45 |     await page.locator('input[type="password"]').fill('anypassword');
  46 |     await page.locator('button[type="submit"]').click();
  47 |     
  48 |     // Expect error message
  49 |     const errorMsg = page.locator('text=/خطأ|Error|Invalid|Not Found/i');
> 50 |     await expect(errorMsg).toBeVisible({ timeout: 10000 });
     |                            ^ Error: expect(locator).toBeVisible() failed
  51 |   });
  52 | 
  53 |   test('AUTH-04: Logout and redirect to login', async ({ page }) => {
  54 |     // Login first
  55 |     await login(page, users.admin);
  56 |     
  57 |     // Click logout
  58 |     await logout(page);
  59 |     
  60 |     // Verify redirect back to login
  61 |     await page.waitForURL(`${BASE_URL}/login`);
  62 |     await expect(page.locator('button[type="submit"]')).toBeVisible();
  63 |   });
  64 | 
  65 |   test('AUTH-05: Unauthenticated access redirects to login', async ({ page }) => {
  66 |     // Try to access protected route without login
  67 |     await page.goto(`${BASE_URL}/dashboard`);
  68 |     
  69 |     // Should redirect to login
  70 |     await expect(page).toHaveURL(/login/);
  71 |   });
  72 | 
  73 |   test('AUTH-06: Remember me functionality', async ({ page }) => {
  74 |     await page.goto(`${BASE_URL}/login`);
  75 |     
  76 |     // Check remember me checkbox
  77 |     const rememberMe = page.locator('input[type="checkbox"]');
  78 |     if (await rememberMe.isVisible()) {
  79 |       await rememberMe.check();
  80 |     }
  81 |     
  82 |     await page.locator('input[type="text"]').fill(users.admin.username);
  83 |     await page.locator('input[type="password"]').fill(users.admin.password);
  84 |     await page.locator('button[type="submit"]').click();
  85 |     
  86 |     // Verify token is stored in localStorage (not sessionStorage)
  87 |     await page.waitForURL(`${BASE_URL}/`);
  88 |     const token = await page.evaluate(() => localStorage.getItem('token'));
  89 |     expect(token).toBeTruthy();
  90 |   });
  91 | 
  92 | });
  93 | 
```
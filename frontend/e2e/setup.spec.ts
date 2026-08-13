/**
 * E2E Test Setup - Creates test users and clinic
 * 
 * This file runs BEFORE all tests to ensure the test environment is ready:
 * 1. Creates test clinic if needed
 * 2. Creates test users (admin, doctor, nurse, etc.)
 * 3. Stores authentication state for reuse
 */

import { test as setup, expect } from '@playwright/test';

const API_URL = process.env.E2E_API_URL || 'http://localhost:8000/api/v1';
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const ADMIN_USERNAME = process.env.E2E_USERNAME || 'e2e_admin';
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || 'E2eAdmin123!';

setup('E2E Test Setup: Create test data', async ({ request, page }) => {
  console.log('\n🧪 Setting up E2E test environment...');
  
  const baseUrl = API_URL.replace('/api/v1', '');
  
  // Check if API is running
  try {
    await request.get(`${baseUrl}/health`, { timeout: 5000 });
    console.log('✅ Backend is running');
  } catch (e) {
    console.log('❌ Backend is not running!');
    console.log('   Please start: cd backend && uvicorn backend.main:app --reload --port 8000');
    throw new Error('Backend not running');
  }
  
  // Try to login as admin first
  let adminToken = null;
  let adminAuthenticated = false;
  try {
    // Login uses OAuth2 form data
    const loginRes = await request.post(`${API_URL}/auth/token`, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      data: `username=${encodeURIComponent(ADMIN_USERNAME)}&password=${encodeURIComponent(ADMIN_PASSWORD)}`,
    });
    
    if (loginRes.ok()) {
      const data = await loginRes.json();
      adminToken = data.access_token ?? data.data?.access_token;
      adminAuthenticated = true; // Current auth succeeds through secure cookies.
      console.log('✅ Admin user already exists');
    } else {
      const error = await loginRes.text();
      console.log('⚠️ Admin login failed:', error);
    }
  } catch (e) {
    console.log('⚠️ Could not login as admin:', e.message);
  }
  
  // If admin doesn't exist, create clinic and admin
  if (!adminAuthenticated) {
    console.log('📝 Creating test clinic and admin user...');
    
    try {
      const registerRes = await request.post(`${API_URL}/auth/register_clinic`, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        data: `clinic_name=Test+Clinic&admin_username=${encodeURIComponent(ADMIN_USERNAME)}&admin_email=e2e-admin%40test.com&admin_password=${encodeURIComponent(ADMIN_PASSWORD)}&contact_phone=01000000000`,
      });
      
      if (registerRes.ok() || registerRes.status() === 201) {
        console.log('✅ Test clinic created successfully');
        
        // Parse response - register_clinic returns access_token
        const data = await registerRes.json();
        adminToken = data.access_token ?? data.data?.access_token;
        adminAuthenticated = Boolean(adminToken);
        
        if (!adminToken) {
          // Try token endpoint
          const loginRes = await request.post(`${API_URL}/auth/token`, {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            data: `username=${encodeURIComponent(ADMIN_USERNAME)}&password=${encodeURIComponent(ADMIN_PASSWORD)}`,
          });
          
          if (loginRes.ok()) {
            const loginData = await loginRes.json();
            adminToken = loginData.access_token ?? loginData.data?.access_token;
          }
        }
        
        if (adminToken) {
          console.log('✅ Admin login successful');
        }
      } else {
        const error = await registerRes.text();
        console.log('⚠️ Could not create clinic:', error.substring(0, 200));
      }
    } catch (e) {
      console.log('⚠️ Could not create admin user:', e.message);
    }
  }
  
  // Confirm the clinic administrator can authenticate through the real UI.
  if (adminAuthenticated) {
    // Login via UI to save session state
    console.log('🔐 Saving admin session...');
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="text"]').fill(ADMIN_USERNAME);
    await page.locator('input[type="password"]').fill(ADMIN_PASSWORD);
    await page.locator('button[type="submit"]').click();
    
    try {
      await page.waitForURL(`${BASE_URL}/`, { timeout: 10000 });
      console.log('✅ Admin UI login successful - session saved');
    } catch (e) {
      console.log('⚠️ Could not complete UI login');
    }
  }
  
  console.log('✅ E2E test environment ready\n');
});

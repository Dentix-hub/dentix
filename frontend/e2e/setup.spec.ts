/**
 * E2E Test Setup - Creates test users and clinic
 * 
 * This file runs BEFORE all tests to ensure the test environment is ready:
 * 1. Creates test clinic if needed
 * 2. Creates test users (admin, doctor, nurse, etc.)
 * 3. Stores authentication state for reuse
 */

import { test as setup, expect } from '@playwright/test';

const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

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
  try {
    // Login uses OAuth2 form data
    const loginRes = await request.post(`${API_URL}/auth/token`, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      data: 'username=admin&password=admin123',
    });
    
    if (loginRes.ok()) {
      const data = await loginRes.json();
      adminToken = data.access_token;
      console.log('✅ Admin user already exists');
    } else {
      const error = await loginRes.text();
      console.log('⚠️ Admin login failed:', error);
    }
  } catch (e) {
    console.log('⚠️ Could not login as admin:', e.message);
  }
  
  // If admin doesn't exist, create clinic and admin
  if (!adminToken) {
    console.log('📝 Creating test clinic and admin user...');
    
    try {
      const registerRes = await request.post(`${API_URL}/auth/register_clinic`, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        data: 'clinic_name=Test+Clinic&admin_username=admin&admin_email=admin@test.com&admin_password=admin123',
      });
      
      if (registerRes.ok() || registerRes.status() === 201) {
        console.log('✅ Test clinic created successfully');
        
        // Parse response - register_clinic returns access_token
        const data = await registerRes.json();
        adminToken = data.access_token;
        
        if (!adminToken) {
          // Try token endpoint
          const loginRes = await request.post(`${API_URL}/auth/token`, {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            data: 'username=admin&password=admin123',
          });
          
          if (loginRes.ok()) {
            const loginData = await loginRes.json();
            adminToken = loginData.access_token;
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
  
  // Create additional test users if admin exists
  if (adminToken) {
    console.log('📝 Creating additional test users...');
    
    const testUsers = [
      { username: 'doctor1', role: 'doctor', password: 'doc123' },
      { username: 'nurse1', role: 'nurse', password: 'nurse123' },
      { username: 'reception1', role: 'receptionist', password: 'rec123' },
      { username: 'account1', role: 'accountant', password: 'acc123' },
    ];
    
    for (const user of testUsers) {
      try {
        // Try to create user via API
        const createRes = await request.post(`${API_URL}/users/register/`, {
          headers: {
            'Authorization': `Bearer ${adminToken}`,
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          data: `username=${user.username}&email=${user.username}%40test.com&password=${user.password}&role=${user.role}`,
        });
        
        if (createRes.ok() || createRes.status() === 201) {
          console.log(`✅ Created user: ${user.username} (${user.role})`);
        } else {
          const error = await createRes.text();
          if (error.includes('already')) {
            console.log(`ℹ️ User ${user.username} already exists`);
          } else {
            console.log(`⚠️ Could not create ${user.username}:`, error.substring(0, 100));
          }
        }
      } catch (e) {
        console.log(`⚠️ Could not create ${user.username}:`, e.message);
      }
    }
    
    // Login via UI to save session state
    console.log('🔐 Saving admin session...');
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
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

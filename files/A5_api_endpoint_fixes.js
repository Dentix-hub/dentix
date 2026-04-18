// ============================================================
// PATCH A.5 — API Endpoint Mismatch Fix
// ============================================================

// === الملف: frontend/src/stores/tenant.store.js ===
// (أو src/store/tenant.js أو src/zustand/tenantStore.js)
// ============================================================

// ابحث عن كل استخدام لـ /users/me وبدّله:

// ❌ قبل:
// const response = await api.get('/users/me');
// const response = await apiClient.get('/users/me');
// const response = await axios.get('/users/me');
// const response = await fetch('/users/me');

// ✅ بعد:
// const response = await api.get('/api/v1/users/me');

// مثال كامل للـ store action:
export const fetchCurrentUser = async () => {
  try {
    const response = await api.get('/api/v1/users/me');
    return response.data;
  } catch (error) {
    if (error.response?.status === 401) {
      // Token expired — redirect to login
      window.location.href = '/login';
    }
    throw error;
  }
};

// ============================================================
// === الملف: frontend/src/pages/SecuritySettings.jsx ===
// (أو src/components/settings/SecuritySettings.jsx)
// ============================================================

// ❌ قبل:
// const { data: userData } = await axios.get('/users/me');
// const response = await fetch('/users/me');

// ✅ بعد (مثال كامل للـ component):
import { useState, useEffect } from 'react';
import api from '@/lib/api'; // أو axios instance بتاعك

const SecuritySettings = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      try {
        // ✅ الـ endpoint الصح
        const { data } = await api.get('/api/v1/users/me');
        setUser(data);
      } catch (err) {
        console.error('Failed to load user:', err);
      } finally {
        setLoading(false);
      }
    };
    loadUser();
  }, []);

  // ... rest of component
};

export default SecuritySettings;

// ============================================================
// SCAN COMMAND — ابحث عن كل الـ endpoints الغلطة:
// grep -rn "'/users/me'\|\"\/users\/me\"" src/ --include="*.jsx" --include="*.js" --include="*.ts"
// ============================================================

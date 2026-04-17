# Dentix E2E Test Plan

> **الإصدار**: 1.0  
> **التاريخ**: 2026-04-16  
> **التغطية**: جميع صفحات الـ Frontend

---

## نظرة عامة

| الملف | عدد الاختبارات | الأولوية |
|-------|---------------|----------|
| `test_auth.spec.ts` | 3 | 🔴 حرج |
| `test_patients.spec.ts` | 8 | 🔴 حرج |
| `test_appointments.spec.ts` | 6 | 🔴 حرج |
| `test_billing.spec.ts` | 5 | 🔴 حرج |
| `test_dashboard.spec.ts` | 4 | 🟡 عالي |
| `test_inventory.spec.ts` | 7 | 🟡 عالي |
| `test_labs.spec.ts` | 5 | 🟡 عالي |
| `test_settings.spec.ts` | 6 | 🟡 عالي |
| `test_users.spec.ts` | 4 | 🟡 عالي |
| `test_expenses.spec.ts` | 4 | 🟢 متوسط |
| `test_rbac.spec.ts` | 8 | 🔴 حرج |
| **المجموع** | **60** | |

---

## 🔴 الاختبارات الحرجة (Critical)

### 1. Authentication — `test_auth.spec.ts`

```typescript
// الحالات:
// ✅ Login ناجح (admin)
// ❌ Login بكلمة مرور خطأ
// ❌ Login ببيانات غير موجودة
// 🔐 Logout
// 🔐 Password Reset Flow
```

| Test ID | السيناريو | الحالة |
|---------|-----------|--------|
| AUTH-01 | Login ناجح ببيانات صحيحة | ✅ |
| AUTH-02 | Login بكلمة مرور خطأ | ✅ |
| AUTH-03 | Login بمستخدم غير موجود | ✅ |
| AUTH-04 | Logout وإعادة التوجيه للـ login | ✅ |
| AUTH-05 | Password Reset — طلب الـ link | ✅ |
| AUTH-06 | Password Reset — تغيير الكلمة | ✅ |

---

### 2. Patients — `test_patients.spec.ts`

```typescript
// CRUD كامل للمرضى:
// 1. عرض قائمة المرضى
// 2. إنشاء مريض جديد
// 3. تعديل بيانات مريض
// 4. حذف مريض (soft delete)
// 5. البحث عن مريض
// 6. فلترة المرضى
// 7. تفاصيل المريض
// 8. إضافةtreatment لمريض
```

| Test ID | السيناريو | الحالة |
|---------|-----------|--------|
| PAT-01 | عرض قائمة المرضى | ✅ |
| PAT-02 | إنشاء مريض جديد | ✅ |
| PAT-03 | تعديل بيانات مريض | ✅ |
| PAT-04 | حذف مريض (تأكيد الـ soft delete) | ✅ |
| PAT-05 | البحث عن مريض بالاسم | ✅ |
| PAT-06 | البحث عن مريض بالرقم | ✅ |
| PAT-07 | عرض تفاصيل مريض | ✅ |
| PAT-08 | إضافة treatment لمريض | ✅ |

---

### 3. Appointments — `test_appointments.spec.ts`

```typescript
// إدارة المواعيد:
// 1. عرض قائمة المواعيد
// 2. إنشاء موعد جديد
// 3. تعديل موعد
// 4. إلغاء موعد
// 5. تأكيد موعد
// 6. عرض التقويم
```

| Test ID | السيناريو | الحالة |
|---------|-----------|--------|
| APPT-01 | عرض قائمة المواعيد | ✅ |
| APPT-02 | إنشاء موعد جديد | ✅ |
| APPT-03 | تعديل موعد | ✅ |
| APPT-04 | إلغاء موعد | ✅ |
| APPT-05 | تأكيد موعد | ✅ |
| APPT-06 | عرض التقويم (calendar view) | ✅ |

---

### 4. Billing — `test_billing.spec.ts`

```typescript
// الفواتير والمدفوعات:
// 1. عرض قائمة الفواتير
// 2. إنشاء فاتورة
// 3. إضافة دفعة
// 4. طباعة فاتورة
// 5. عرض الرصيد
```

| Test ID | السيناريو | الحالة |
|---------|-----------|--------|
| BILL-01 | عرض قائمة الفواتير | ✅ |
| BILL-02 | إنشاء فاتورة جديدة | ✅ |
| BILL-03 | إضافة دفعة للفاتورة | ✅ |
| BILL-04 | طباعة فاتورة (PrintInvoice) | ✅ |
| BILL-05 | عرض رصيد المريض | ✅ |

---

### 5. RBAC — `test_rbac.spec.ts`

```typescript
// اختبار صلاحيات الأدوار:
// 1. doctor لا يرى financials
// 2. nurse لا يcrate的患者
// 3. receptionist يرى patients فقط
// 4. accountant يرى financials فقط
// 5. admin يرى كل شيء
// 6. assistant يرى محدود
// 7. manager يرى reports
```

| Test ID | السيناريو | الدور | الحالة |
|---------|-----------|-------|--------|
| RBAC-01 | الوصول للـ billing | doctor | ❌ 403 |
| RBAC-02 | إنشاء patient | nurse | ❌ 403 |
| RBAC-03 | عرض patients | receptionist | ✅ |
| RBAC-04 | عرض financials | accountant | ✅ |
| RBAC-05 | الوصول للـ settings | doctor | ❌ 403 |
| RBAC-06 | الوصول للـ users | assistant | ❌ 403 |
| RBAC-07 | عرض analytics | manager | ✅ |
| RBAC-08 | الوصول للـ admin | admin | ✅ |

---

## 🟡 الاختبارات العالية (High Priority)

### 6. Dashboard — `test_dashboard.spec.ts`

```typescript
// لوحة التحكم:
// 1. عرض الإحصائيات
// 2. عرض today's appointments
// 3. عرض recent patients
// 4. عرض alerts/notifications
```

| Test ID | السيناريو | الحالة |
|---------|-----------|--------|
| DASH-01 | عرض الإحصائيات الرئيسية | ✅ |
| DASH-02 | عرض مواعيد اليوم | ✅ |
| DASH-03 | عرض أحدث المرضى | ✅ |
| DASH-04 | عرض الإشعارات | ✅ |

---

### 7. Inventory — `test_inventory.spec.ts`

```typescript
// المخزون:
// 1. عرض المخزون
// 2. إضافة مادة
// 3. تعديل مادة
// 4. حذف مادة
// 5. بحث في المخزون
// 6. تنبيه نقص المخزون
// 7. عرض حركة المخزون
```

| Test ID | السيناريو | الحالة |
|---------|-----------|--------|
| INV-01 | عرض المخزون | ✅ |
| INV-02 | إضافة مادة جديدة | ✅ |
| INV-03 | تعديل مادة | ✅ |
| INV-04 | حذف مادة | ✅ |
| INV-05 | البحث في المخزون | ✅ |
| INV-06 | عرض تنبيهات النقص | ✅ |
| INV-07 | عرض حركة المخزون | ✅ |

---

### 8. Labs — `test_labs.spec.ts`

```typescript
// المعامل:
// 1. عرض قائمة المعامل
// 2. إضافة معمل
// 3. عرض طلبات المعمل
// 4. إنشاء طلب معمل
// 5. تحديث حالة الطلب
```

| Test ID | السيناريو | الحالة |
|---------|-----------|--------|
| LAB-01 | عرض قائمة المعامل | ✅ |
| LAB-02 | إضافة معمل جديد | ✅ |
| LAB-03 | عرض طلبات المعمل | ✅ |
| LAB-04 | إنشاء طلب معمل | ✅ |
| LAB-05 | تحديث حالة الطلب | ✅ |

---

### 9. Settings — `test_settings.spec.ts`

```typescript
// الإعدادات:
// 1. عرض إعدادات العيادة
// 2. تحديث إعدادات العيادة
// 3. ربط Google Drive
// 4. عرض الاشتراك
// 5. تغيير اللغة
// 6. تغيير الـ theme
```

| Test ID | السيناريو | الحالة |
|---------|-----------|--------|
| SET-01 | عرض إعدادات العيادة | ✅ |
| SET-02 | تحديث إعدادات العيادة | ✅ |
| SET-03 | ربط Google Drive | ✅ |
| SET-04 | عرض معلومات الاشتراك | ✅ |
| SET-05 | تغيير اللغة (عربي/إنجليزي) | ✅ |
| SET-06 | تغيير الـ theme (dark/light) | ✅ |

---

### 10. Users — `test_users.spec.ts`

```typescript
// إدارة المستخدمين:
// 1. عرض قائمة المستخدمين
// 2. إضافة مستخدم
// 3. تعديل مستخدم
// 4. حذف/إلغاء تفعيل مستخدم
```

| Test ID | السيناريو | الحالة |
|---------|-----------|--------|
| USER-01 | عرض قائمة المستخدمين | ✅ |
| USER-02 | إضافة مستخدم جديد | ✅ |
| USER-03 | تعديل مستخدم | ✅ |
| USER-04 | إلغاء تفعيل مستخدم | ✅ |

---

## 🟢 الاختبارات المتوسطة (Medium Priority)

### 11. Expenses — `test_expenses.spec.ts`

```typescript
// المصروفات:
// 1. عرض المصروفات
// 2. إضافة مصروف
// 3. تعديل مصروف
// 4. حذف مصروف
```

| Test ID | السيناريو | الحالة |
|---------|-----------|--------|
| EXP-01 | عرض المصروفات | ✅ |
| EXP-02 | إضافة مصروف جديد | ✅ |
| EXP-03 | تعديل مصروف | ✅ |
| EXP-04 | حذف مصروف | ✅ |

---

## 🔵 Pages الإضافية (Low Priority)

### 12. Landing & Auth Pages

```typescript
// الصفحات الثابتة:
// - LandingPage
// - Terms
// - Privacy
// - ForgotPassword
// - ResetPassword
// - RegisterClinic
// - NotFound
```

---

## ملخص الاختبارات المنشأة

| الملف | عدد الاختبارات | الحالة |
|-------|---------------|--------|
| `test_auth.spec.ts` | 6 | ✅ |
| `test_patients.spec.ts` | 8 | ✅ |
| `test_appointments.spec.ts` | 6 | ✅ |
| `test_billing.spec.ts` | 5 | ✅ |
| `test_dashboard.spec.ts` | 4 | ✅ |
| `test_inventory.spec.ts` | 7 | ✅ |
| `test_labs.spec.ts` | 5 | ✅ |
| `test_settings.spec.ts` | 6 | ✅ |
| `test_users.spec.ts` | 4 | ✅ |
| `test_expenses.spec.ts` | 4 | ✅ |
| `test_rbac.spec.ts` | 8 | ✅ |
| **المجموع** | **63** | ✅ |

---

## ⚙️ Test Environment

### الأسبوع 1 (الأولوية الحرجة)
1. `test_auth.spec.ts` — 6 اختبارات
2. `test_patients.spec.ts` — 8 اختبارات  
3. `test_appointments.spec.ts` — 6 اختبارات
4. `test_billing.spec.ts` — 5 اختبارات
5. `test_rbac.spec.ts` — 8 اختبارات

### الأسبوع 2 (الأولوية العالية)
6. `test_dashboard.spec.ts` — 4 اختبارات
7. `test_inventory.spec.ts` — 7 اختبارات
8. `test_labs.spec.ts` — 5 اختبارات
9. `test_settings.spec.ts` — 6 اختبارات
10. `test_users.spec.ts` — 4 اختبارات

### الأسبوع 3 (المتبقي)
11. `test_expenses.spec.ts` — 4 اختبارات
12. صفحات Landing والثابتة

---

## ⚙️ إعدادات Test Environment

```typescript
// playwright.config.ts
export default {
  baseURL: 'http://localhost:5173',
  timeout: 30000,
  retries: 2,
  
  // المستخدمين للاختبار
  users: {
    admin: { username: 'admin', password: 'admin123' },
    doctor: { username: 'doctor1', password: 'doc123' },
    nurse: { username: 'nurse1', password: 'nurse123' },
    receptionist: { username: 'reception1', password: 'rec123' },
    accountant: { username: 'account1', password: 'acc123' },
  },
  
  // API Base
  apiUrl: 'http://localhost:8000/api/v1',
};
```

---

## 🧪 تشغيل الاختبارات

```bash
# تشغيل جميع الاختبارات
cd frontend && npx playwright test

# تشغيل مجموعة محددة
npx playwright test --group=auth
npx playwright test --group=patients

# تشغيل ملف محدد
npx playwright test e2e/test_auth.spec.ts

# تشغيل مع HTML report
npx playwright test --reporter=html

# تشغيل على CI
CI=true npx playwright test
```

---

## 📊 التغطية المستهدفة

| الصفحة | الاختبارات | الحالة |
|--------|-----------|--------|
| Login/Logout | 6 | ✅ |
| Patients | 8 | 🟡 |
| Appointments | 6 | 🟡 |
| Billing | 5 | 🟡 |
| Dashboard | 4 | 🟡 |
| Inventory | 7 | 🟡 |
| Labs | 5 | 🟡 |
| Settings | 6 | 🟡 |
| Users | 4 | 🟡 |
| Expenses | 4 | 🟢 |
| RBAC | 8 | ✅ |
| **المجموع** | **63** | |

# 📋 Material Consumption Tracking — Task List

## ملخص المشروع

### المشكلة
الدكتور بيحتاج 4 شاشات عشان يسجل استهلاك المواد. مفيش ربط تلقائي بين الإجراء والمواد المستخدمة.

### الحل
- نظام تتبع مواد ذكي مدمج داخل شاشة العلاج
- 28 فئة مادة مسجلة بشكل افتراضي
- كل إجراء (34 إجراء) مربوط بالمواد اللي بيستهلكها + أوزان نسبية
- المواد القابلة للتجزئة (DIVISIBLE) تتبعها عبر Sessions — مش خصم مباشر
- المواد الغير قابلة للتجزئة (NON_DIVISIBLE) خصم فوري
- نظام تعلم ذاتي يحسن الأرقام مع الوقت

### ما لا يتغير
- شاشة إضافة المواد (AddMaterialModal) — بس حقلين جداد
- شاشة إضافة المخزون — نفسها زي ما هي
- الأسعار — الدكتور يعدلها يدوي

---

## Phase 1: Database & Models
> **الهدف:** إنشاء البنية التحتية للبيانات

### Task 1.1 — MaterialCategory Model
- [x] إنشاء موديل `MaterialCategory` في `models/inventory.py`
- **Fields:** `id`, `name_en`, `name_ar`, `default_type`, `default_unit`
- **File:** `backend/models/inventory.py`

### Task 1.2 — Material Model Update
- [x] إضافة `category_id` (FK → material_categories) على `Material`
- [x] إضافة `brand` (String, nullable) على `Material`
- [x] إضافة relationship `category`
- **File:** `backend/models/inventory.py`

### Task 1.3 — TreatmentMaterialUsage Model
- [x] إنشاء موديل جديد `TreatmentMaterialUsage`
- **Fields:** `id`, `treatment_id`, `material_id`, `session_id`, `weight_score`, `quantity_used`, `cost_calculated`, `is_manual_override`, `tenant_id`, `created_at`
- **File:** `backend/models/inventory.py`
- **Depends on:** Task 1.1

### Task 1.4 — ProcedureMaterialWeight Update
- [x] إضافة `category_id` (FK → material_categories, nullable)
- [x] تعديل `material_id` ليكون nullable (دعم category-level defaults)
- **File:** `backend/models/inventory.py`
- **Depends on:** Task 1.1

### Task 1.5 — Alembic Migration
- [x] إنشاء migration لكل التغييرات
- [x] اختبار على قاعدة بيانات التطوير
- **File:** `backend/alembic/versions/xxx_material_categories.py`
- **Depends on:** Tasks 1.1–1.4

### Task 1.6 — Schema Updates (Pydantic)
- [x] `MaterialCategoryOut` schema
- [x] `MaterialCreate` — إضافة `category_id` + `brand`
- [x] `MaterialUpdate` — إضافة `category_id` + `brand`
- [x] `TreatmentMaterialUsageCreate` + `TreatmentMaterialUsageOut`
- [x] `SuggestedMaterial` schema (for resolution engine response)
- **File:** `backend/schemas.py`
- **Depends on:** Tasks 1.1–1.4

---

## Phase 2: Seed Scripts
> **الهدف:** بيانات افتراضية جاهزة لأي عيادة جديدة

### Task 2.1 — Seed Material Categories
- [x] إنشاء `seed_material_categories.py`
- [x] إدخال 28 فئة مادة (Global, tenant_id=NULL)
- [x] Idempotent — لو موجودة ميعملش duplicate
- **File:** `backend/scripts/seed_material_categories.py`

### Task 2.2 — Seed Procedure-Material Defaults
- [x] إنشاء `seed_procedure_material_defaults.py`
- [x] ربط 34 إجراء × المواد المستهلكة (بالأوزان النسبية)
- [x] يستخدم `category_id` مش `material_id` (عشان Global)
- [x] Idempotent
- **File:** `backend/scripts/seed_procedure_material_defaults.py`
- **Depends on:** Task 2.1, Task 1.5

### Task 2.3 — Add Post & Core Buildup Procedure
- [x] إضافة "بوست وبناء لب – Post and Core Buildup" في `seed_procedures.py`
- **File:** `backend/scripts/seed_procedures.py`

### Task 2.4 — Run Seeds on Dev DB
- [x] تشغيل الثلاث scripts بالترتيب
- [x] التأكد من البيانات في DB
- **Depends on:** Tasks 2.1–2.3

---

## Phase 3: Backend APIs
> **الهدف:** Endpoints جاهزة للفرونت

### Task 3.1 — Material Categories Router
- [x] `GET /api/v1/material-categories` — كل الفئات
- [x] `GET /api/v1/material-categories/{id}/materials` — مواد العيادة في فئة محددة
- **File:** `backend/routers/inventory.py`
- **Depends on:** Task 1.5

### Task 3.2 — Material Resolution Engine
- [x] إنشاء `MaterialResolutionService`
- [x] Logic: Active Session → Doctor History → Clinic Default → Manual
- [x] يرجع `SuggestedMaterial[]` مع confidence level
- **File:** `backend/services/material_resolution_service.py`
- **Depends on:** Task 1.5, Task 2.4

### Task 3.3 — Suggested Materials Endpoint
- [x] `GET /api/v1/inventory/smart/suggestions-categories/{procedure_id}`
- [x] Query params: `doctor_id` (optional)
- [x] يستدعي Resolution Engine
- **File:** `backend/routers/inventory_smart.py`
- **Depends on:** Task 3.2

### Task 3.4 — Treatment Material Usage CRUD
- [x] `POST /api/v1/treatments/{id}/materials` — حفظ المواد المستخدمة
- [x] `GET /api/v1/treatments/{id}/materials` — استرجاع المواد المسجلة
- [x] Logic: DIVISIBLE → ربط بـ session + weight_score فقط
- [x] Logic: NON_DIVISIBLE → خصم فوري من المخزون
- **File:** `backend/routers/treatments.py`
- **Depends on:** Task 3.2

### Task 3.5 — Update Material CRUD
- [x] تعديل `create_material` ليقبل `category_id` + `brand`
- [x] تعديل `update_material` ليقبل `category_id` + `brand`
- **File:** `backend/services/inventory_service.py` (already uses model_dump)
- **Depends on:** Task 1.6

### Task 3.6 — API for Categories in Frontend
- [x] إضافة `getCategories()` في `frontend/src/api/inventory.js`
- [x] إضافة `getSuggestedMaterials(procedureId)` 
- [x] إضافة `saveTreatmentMaterials(treatmentId, materials)`
- [x] إضافة `getTreatmentMaterials(treatmentId)`
- **File:** `frontend/src/api/inventory.js`
- **Depends on:** Tasks 3.1–3.4

---

## Phase 4: Frontend
> **الهدف:** واجهة مستخدم ذكية وسريعة

### Task 4.1 — AddMaterialModal Enhancement
- [x] إضافة dropdown لـ `category` (يحمّل من API)
- [x] إضافة حقل `brand` (text)
- [x] Auto-fill `type` و `base_unit` من الـ category المختارة
- [x] الحقول الجديدة optional — المواد القديمة تفضل تشتغل
- **File:** `frontend/src/features/inventory/AddMaterialModal.jsx`
- **Depends on:** Task 3.6

### Task 4.2 — MaterialConsumptionPanel Component
- [x] إنشاء component جديد
- [x] يستقبل `procedureId` + `doctorId`
- [x] يعرض قائمة المواد المقترحة (من Resolution Engine)
- [x] لكل مادة:
  - DIVISIBLE: عرض active session + weight score
  - NON_DIVISIBLE: spinner [- qty +]
  - Multiple brands: radio buttons
- [x] زر "Manual Override" لتعديل يدوي
- [x] عرض التكلفة التقديرية (informational)
- **File:** `frontend/src/features/inventory/MaterialConsumptionPanel.jsx`
- **Depends on:** Task 3.6

### Task 4.3 — TreatmentModal Integration
- [x] تضمين `MaterialConsumptionPanel` داخل `TreatmentModal`
- [x] يظهر بعد اختيار الإجراء
- [x] عند حفظ Treatment → يحفظ المواد معاه
- **File:** `frontend/src/shared/ui/modals/TreatmentModal.jsx`
- **Depends on:** Task 4.2

### Task 4.4 — Translations
- [x] إضافة ترجمات عربي/إنجليزي للمفاتيح الجديدة
- [x] `material_consumption.*`, `categories.*`, `brand`, `suggested_materials`
- **Files:** `frontend/src/locales/ar/translation.json`, `frontend/src/locales/en/translation.json`
- **Depends on:** Task 4.2

---

## Phase 5: Learning Integration
> **الهدف:** النظام يتعلم ويحسّن الأرقام

### Task 5.1 — Update InventoryLearningService
- [x] بعد `close_session`: تحديث `TreatmentMaterialUsage.quantity_used`
- [x] حساب `cost_calculated` = quantity × unit_cost
- [x] تحديث `current_average_usage` في `ProcedureMaterialWeight`
- **File:** `backend/services/inventory_learning_service.py`
- **Depends on:** Task 1.3

### Task 5.2 — Link Learning to TreatmentMaterialUsage
- [x] `close_session` يدور على `TreatmentMaterialUsage` records المرتبطة
- [x] يوزع الاستهلاك بناءً على `weight_score`
- [x] يملأ `quantity_used` و `cost_calculated`
- **File:** `backend/services/inventory_learning_service.py`
- **Depends on:** Task 5.1

### Task 5.3 — CostEngine Update
- [x] `calculate_procedure_cost` يستخدم `TreatmentMaterialUsage` الفعلي (fallback)
- [x] Fallback لـ `ProcedureMaterialWeight.current_average_usage`
- [x] Added `source` field to indicate data origin (learning/actual_usage/estimated)
- **File:** `backend/services/cost_engine.py`
- **Depends on:** Task 5.2

---

## ملخص الأرقام

| البند | العدد |
|-------|-------|
| Models جديدة | 2 (`MaterialCategory`, `TreatmentMaterialUsage`) |
| Models معدّلة | 2 (`Material`, `ProcedureMaterialWeight`) |
| Seed scripts | 3 (categories, defaults, procedure) |
| API endpoints جديدة | 5 |
| Frontend components جديدة | 1 (`MaterialConsumptionPanel`) |
| Frontend components معدّلة | 2 (`AddMaterialModal`, `TreatmentModal`) |
| Backend services جديدة | 1 (`MaterialResolutionService`) |
| Backend services معدّلة | 2 (`InventoryLearningService`, `CostEngine`) |
| **إجمالي Tasks** | **22 task** |

---

## ترتيب التنفيذ

```
Phase 1 (Models)     ████████████████████████  [Tasks 1.1–1.6] ✅
Phase 2 (Seeds)      ████████████████████████  [Tasks 2.1–2.4] ✅
Phase 3 (APIs)       ████████████████████████  [Tasks 3.1–3.6] ✅
Phase 4 (Frontend)   ████████████████████████  [Tasks 4.1–4.4] ✅
Phase 5 (Learning)   ████████████████████████  [Tasks 5.1–5.3] ✅
```

> [!NOTE]
> ### تم الانتهاء بنجاح
> كل الـ 22 Task تم تنفيذها واختبارها. Migration شغال على DB والـ Seeds مملوءة (28 category + 34 procedure mapping).

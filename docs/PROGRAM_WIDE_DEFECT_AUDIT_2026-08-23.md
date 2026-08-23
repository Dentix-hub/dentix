# تدقيق أوسع لأعطال DENTIX

التاريخ: 2026-08-23  
الحالة: تدقيق read-only وخطة أولويات؛ لم تُعدّل شيفرة التطبيق.  
العلاقة بالخطة السابقة: هذا المستند ملحق مستقل لخطة `FINANCE_REPORTS_REPAIR_PLAN_2026-08-23.md`، وليس توسيعًا غير منضبط لنطاق Finance.

## 1. هل خطة المالية سطحية؟

لا. الخطة الحالية تتكون من نحو 315 سطرًا و2,888 كلمة، وتحتوي على:

- نتائج مثبتة وأسباب جذرية؛
- ست مراحل تنفيذ وبوابات خروج؛
- ثلاثة مستويات تحقق: Backend وFrontend وE2E؛
- 13 معيار قبول نهائي؛
- تقسيم التسليم إلى سبع دفعات PR قابلة للنشر والرجوع المستقل؛
- قرارات مالية وأمنية لا يجوز تغييرها بصمت.

لكنها **خطة إصلاح تنفيذية على مستوى المبادرات**، وليست Technical Design نهائيًا لكل PR. قبل تنفيذ كل دفعة يلزم إضافة:

- schemas الدقيقة للطلب والاستجابة؛
- قائمة الملفات والوظائف المتأثرة؛
- migrations عند الحاجة وخطة rollback؛
- test cases على مستوى كل endpoint ودور؛
- wireframes أو interaction spec للتغييرات البصرية؛
- تقدير واعتماد ومالك لكل تذكرة.

إذًا: الرد التنفيذي السابق كان مختصرًا، والخطة نفسها ليست سطحية، لكنها لا تدعي أنها تدقيق كامل لكل البرنامج.

## 2. حدود هذا التدقيق

تم فحص الشيفرة الحالية، route registry الفعلي، التغييرات الأخيرة، الاختبارات وCI، وإجراء reproductions محلية للأعطال القابلة للعزل. لا تتوفر سجلات خادم الإنتاج الكاملة أو بيانات منصة مراقبة الأخطاء؛ لذلك لا يصح الادعاء بأن القائمة تحتوي كل خطأ حدث في الإنتاج.

التصنيف أدناه يفرق بين:

- **CONFIRMED/REPRODUCED:** عيب تدفق أو عقد أُعيد إنتاجه أو ثبت من route table والحساب مباشرة.
- **CONFIRMED CODE / ENVIRONMENT-DEPENDENT IMPACT:** العيب موجود في التصميم التنفيذي، لكن معرفة أثره الحالي على الإنتاج تحتاج فحص إعداد خارجي مثل PostgreSQL role أو deployment secret.
- لا تُدرج فرضيات بحث نصي غير مثبتة كأخطاء.

## 3. أخطاء حرجة مؤكدة خارج خطة Finance

### CRITICAL-01 — تسريب Cookies وAuthorization في سجلات الإنتاج

- **المكان:** `backend/main.py:296-301`, `backend/core/logging.py:37-50`.
- **الدليل:** كل استجابة 405 تسجل `dict(request.headers)` كاملًا. مرشح السجلات يخفي البريد والبطاقات فقط، ولا يخفي `Authorization`, `Cookie`, access token أو refresh token.
- **الأثر:** أي طلب بطريقة HTTP غير مسموحة قد ينسخ رموز الجلسة إلى stdout/منصة السجلات، حيث يمكن لمطلع على السجلات إعادة استخدامها قبل انتهاء صلاحيتها.
- **الإصلاح:** تسجيل method/path/status/trace ID فقط، scrub مركزي للـheaders والأسرار، واختبار يرسل Cookie/Bearer وهميًا ويتأكد أن قيمته لا تظهر في أي formatter.

### CRITICAL-02 — الفاتورة المطبوعة قد تعرض مبلغًا وهوية عيادة خاطئين

- **المكان:** `frontend/src/pages/PrintInvoice.jsx:25-38,88-90`.
- **الدليل:** الإجمالي يجمع `cost` ويتجاهل `discount`، بينما حساب المريض يعتمد `cost - discount`. اسم العيادة وعنوانها وهاتفها ثابتة داخل React، ورقم الفاتورة يتغير باستخدام `Date.now()`.
- **الأثر:** مستند مالي غير مطابق لحساب المريض، وقد يحمل هوية tenant أخرى أو رقمًا مختلفًا عند إعادة الطباعة.
- **الإصلاح:** Invoice DTO ثابت من الخادم يحتوي tenant identity، البنود الصافية، المدفوعات، العملة، ورقم/تاريخ immutable؛ الواجهة تطبع ولا تعيد الحساب.

### CRITICAL-03 — فشل نسخة عيادة يحذف Google token العالمي للـSuper Admin

- **المكان:** `backend/routers/settings.py:244-268`, `backend/services/backup_service.py:235-263`.
- **الدليل:** النسخة اليدوية تمرر `Tenant.google_refresh_token` و`tenant_id`. عند `401/403/invalid_grant` يحذف العامل دائمًا `SystemSetting.GOOGLE_SUPER_ADMIN_TOKEN_KEY` بدل مسح توكن العيادة الفاشل.
- **الأثر:** Admin لعيادة بتوكن منتهي يمكنه، عبر تشغيل النسخة، فصل Google Drive الخاص بالمنصة كلها، بينما يظل توكن عيادته المعيب محفوظًا.
- **الإصلاح:** إذا كان `tenant_id` موجودًا، يُمسح توكن نفس tenant فقط. التوكن العالمي لا يُمس إلا في مهمة global صريحة. يلزم اختبار عيادتين + global setting.

## 4. أخطاء High مؤكدة

### HIGH-01 — إنشاء علاج مسعّر يفشل بعد تحديث Numeric

- **المكان:** `backend/services/pricing_service.py:66-104`, `backend/services/treatment_service.py:75-85`.
- **الدليل:** السعر أصبح `Decimal` ثم يدخل `json.dumps` العادي في price snapshot. إعادة الإنتاج أعطت `TypeError: Object of type Decimal is not JSON serializable`.
- **الأثر:** `POST /api/v1/treatments` قد يعيد 500 عند استخدام إجراء له سعر.
- **الإصلاح:** إبقاء القيمة Decimal واستخدام Pydantic/jsonable encoder أو money string canonical، مع PostgreSQL route regression.

### HIGH-02 — إغلاق جلسة تعلم المخزون يفشل لنفس سبب Decimal

- **المكان:** `backend/services/inventory_learning_service.py:176-201,257-266`.
- **الدليل:** `cost_calculated` أصبح Decimal ويدخل plain `json.dumps`. إعادة الإنتاج فشلت في line 266.
- **الأثر:** إغلاق جلسة مادة divisible/reusable قد يفشل قبل commit، فلا يثبت الاستهلاك أو التكلفة أو learning log.
- **الإصلاح:** serializer مالي موحد واختبار transaction كامل لإغلاق جلسة لها usage فعلي.

### HIGH-03 — تحذيرات نقص المخزون مخفية دائمًا في الواجهة

- **المكان:** `backend/routers/inventory_smart.py:184-199`, `frontend/src/api/apiClient.js:103-127`, `frontend/src/features/inventory/components/EnhancedMaterialConsumption.jsx:79-99`.
- **الدليل:** الخادم يعيد `success_response(data=results)` والـinterceptor يفك الغلاف، ثم المكوّن يطلب `res.data.data` مرة ثانية، فيحوّل النتيجة إلى `[]`.
- **الأثر:** CRITICAL/WARNING الخاصة بنفاد أو نقص مادة العلاج لا تظهر للطبيب/المستخدم.
- **الإصلاح:** قراءة `res.data` مرة واحدة وإضافة component contract test لحالات OK/WARNING/CRITICAL.

### HIGH-04 — إعداد وتعطيل 2FA يستدعيان مسارات غير موجودة

- **المكان:** `backend/routers/auth/security.py:15,40,68`, `backend/main.py:413`, `frontend/src/features/settings/Profile/SecuritySettings.jsx:39-58`, `frontend/src/features/admin/SuperAdmin/TwoFactorSetup.jsx:12-55`.
- **الدليل:** route registry الفعلي يحتوي `/api/v1/auth/auth/2fa/*` بسبب تكرار `/auth`، بينما الواجهة تستدعي `/api/v1/auth/2fa/*`. مكوّن الإدارة يرسل JSON بينما endpoint ينتظر query parameters.
- **الأثر:** setup/verify/disable تنتهي 404، ثم verify قد تنتهي 422 حتى بعد إصلاح prefix.
- **الإصلاح:** إزالة prefix المكرر، Pydantic body موحد، واختبار HTTP setup→verify→session revocation→disable.

### HIGH-05 — ماسح بطاقة المريض OCR يستدعي endpoint غير مسجل

- **المكان:** `frontend/src/api/ocr.js:3`, `frontend/src/features/patients/PatientScanner.jsx:77-127`, route registration في `backend/main.py`.
- **الدليل:** الواجهة تستدعي `POST /api/v1/ocr`، وroute registry لا يحتوي أي مسار OCR.
- **الأثر:** كل محاولة OCR تفشل؛ الواجهة تعرض ميزة غير موجودة في الخادم.
- **الإصلاح:** إخفاؤها خلف feature flag حتى وجود endpoint مؤمن وtenant-aware، أو تنفيذ العقد واختباره قبل إظهارها.

### HIGH-06 — وصفة الطباعة تستخدم PHI قديمة من sessionStorage

- **المكان:** `frontend/src/pages/PatientDetails.jsx:263-273`, `frontend/src/pages/PrintRx.jsx:29-43`, `frontend/src/utils.js:65-76`.
- **الدليل:** route يحمل `:id` لكنه لا يجلب وصفة بهذا المعرف؛ يقرأ آخر `print_rx_data` فقط. logout العادي لا يمسح المفتاح.
- **الأثر:** reload/direct link يعلق على Loading، وقد يرى مستخدم لاحق في نفس التبويب وصفة المريض السابق.
- **الإصلاح:** route بمعرف وصفة حقيقي + tenant-scoped print DTO، ومسح PHI عند كل logout/session teardown.

### HIGH-07 — تطبيق Flutter الحالي غير متصل ببيئة إنتاج وعقوده الأساسية مكسورة

- **المكان:** `dentix_mobile/lib/core/di/providers.dart:56-62`, `dentix_mobile/lib/core/constants/api_endpoints.dart:4-35`, auth/financial remotes.
- **الدليل:** base URL ثابت على localhost/emulator. route probe أكد أن `/api/v1/token`, `/logout`, `/refresh`, `/change-password`, `/financial/overview`, `/financial/record-payment` غير موجودة. Backend login يعيد cookies + user/session، بينما `TokenModel` يطلب access/refresh tokens وrole/username.
- **الأثر:** login/refresh/finance لا تعمل ضد الخادم الحالي، وبعض StandardResponse payloads لا تُفك قبل parsing.
- **الإصلاح:** build-time environment، client موحد لعقود API/cookies أو mobile token contract معتمد، وتوليد/اختبار endpoints من OpenAPI.

### HIGH-08 — لا توجد بوابة CI لتطبيق Flutter

- **المكان:** `.github/workflows/ci.yml`, `.github/workflows/mobile-responsive.yml`, `dentix_mobile/test/widget_test.dart`.
- **الدليل:** workflow المسماة mobile-responsive تختبر React responsive فقط. لا يوجد `flutter analyze` أو `flutter test`; الاختبار الموجود smoke واحد، وFlutter SDK غير متاح محليًا في جلسة التدقيق.
- **الأثر:** أخطاء HIGH-07 تمر بينما CI كلها خضراء.
- **الإصلاح:** job إلزامي لـanalyze/test/build وDio contract tests باستخدام mock server.

### HIGH-09 — health gate يمكن أن يعلن نجاح نشر لا تصل فيه قاعدة البيانات

- **المكان:** `backend/routers/health.py:237-248,306-325`, `Dockerfile` و`.github/workflows/cd.yml`.
- **الدليل:** `/api/v1/health` يعيد healthy دون DB، بينما `/health/ready` هو الذي ينفذ `SELECT 1`. بوابات النشر تستخدم المسار الأساسي.
- **الأثر:** container حي مع migration/schema/database معطلة يمكن أن يمر health gate.
- **الإصلاح:** liveness للمسار الأساسي، readiness للنشر والتوجيه، ثم canary مصادق لمسار أعمال منخفض المخاطر.

### HIGH-10 — أحداث outbox قد تبقى `processing` إلى الأبد بعد crash

- **المكان:** `backend/services/event_service.py:39-62`, `backend/workers/event_processor.py:39-70`, `backend/models/domain_event.py:31-39`.
- **الدليل:** العامل يحدد processing ويعمل commit قبل handler. الاستعلام التالي يقرأ pending فقط، ولا يوجد `locked_at`, lease أو recovery للأحداث القديمة.
- **الأثر:** crash بين commit والمعالجة يفقد الحدث عمليًا؛ قد تضيع إشعارات أو عمليات downstream دون retry.
- **الإصلاح:** lease/locked_by/locked_at، استرجاع stale processing، idempotent handlers، backlog alert، واختبار kill/re-delivery.

### HIGH-11 — CI لا يثبت ترقية قاعدة إنتاج قديمة إلى head

- **المكان:** `.github/workflows/ci.yml:117-123`, `backend/scripts/preflight_migrations.py`.
- **الدليل:** CI ينشئ قاعدة فارغة، ثم يعيد التشغيل وهي عند head. لا يبني snapshot عند revision N-1 ثم ينفذ `upgrade head`.
- **الأثر:** migration صحيحة على fresh DB لكنها مكسورة على schema الإنتاج القديمة قد لا تظهر إلا أثناء النشر.
- **الإصلاح:** upgrade matrix من آخر نسخ مدعومة + `alembic check` + data-shape fixtures للقيود والتحويلات.

### HIGH-12 — إعداد النسخ المجدولة لا يشغّل Scheduler

- **المكان:** `backend/routers/settings.py:275-290`, `backend/models/tenant.py:152`.
- **الدليل:** endpoint يحفظ `backup_frequency` فقط، ولا يوجد worker/scheduler يقرأه. النسخة اليدوية BackgroundTask غير دائمة.
- **الأثر:** الواجهة قد توحي بوجود نسخ تلقائية بينما لا تنفذ.
- **الإصلاح:** scheduler دائم مع due-at/status/heartbeat/audit، أو إزالة/تعطيل التحكم حتى تنفيذ الخدمة.

## 5. عيب RLS مؤكد في التصميم، وأثر الإنتاج يحتاج تحققًا خارجيًا

### HIGH-RLS-01 — bootstrap المصادقة لا يهيئ RLS للـcookie-only flow

- **المكان:** `backend/middleware/tenant.py:30-50`, `backend/routers/auth/dependencies.py:40-47,93-181`, `backend/database.py:347-356`, `backend/scripts/preflight_migrations.py:65-98,189-205`.
- **المؤكد في الشيفرة:** TenantMiddleware يقرأ Bearer فقط، بينما الواجهة تعتمد httpOnly cookie. جلسة DB تلتقط `tenant_id=None` قبل أن يقرأ `get_current_user` المستخدم. RLS على users هو ENABLE+FORCE ويعامل tenant الفارغ كعدم رؤية لأي صف.
- **الأثر المشروط:** إذا كان دور التطبيق PostgreSQL هو `NOBYPASSRLS` كما تفترض عقود العزل، login/cookie bootstrap/super-admin/password reset/registration تحتاج مسار bootstrap audited. إذا كان الإنتاج يعمل فقط لأن دور DB superuser/BYPASSRLS فـRLS ليست طبقة الحماية الفعلية المتوقعة.
- **التحقق المطلوب قبل وصف الأثر الحي:** فحص خصائص دور الإنتاج دون كشف credentials، ثم اختبار PostgreSQL HTTP كامل: login → cookie-only session → refresh، registration/reset، super-admin، على NOBYPASSRLS.
- **الإصلاح:** audited identity-bootstrap flow محدود، ثم إنشاء tenant-bound RLS session بعد تحقق الهوية؛ لا يُحل بإلغاء FORCE RLS أو استخدام superuser دائمًا.

## 6. أخطاء Medium مؤكدة

- **التنقل:** `/dashboard` و`/unauthorized` غير معرفين رغم استخدامهما في ErrorBoundary وNotFound وimpersonation وProtectedRoute. أوامر Command Palette ترسل query params لا تقرؤها الصفحات.
- **React Query:** عدة استدعاءات تستخدم صيغة v4 `invalidateQueries(['key'])` مع v5؛ الاختبار التنفيذي أثبت أنها قد تبطل كل الاستعلامات. وفي مواضع أخرى يُبطل مفتاح غير موجود فيظل Dashboard stale.
- **المرفقات:** `PatientFiles.jsx` يستخدم `.replace('//','/')` على URL كامل، فيحوّل `https://` إلى `https:/` عندما يكون API base مطلقًا.
- **رسائل الدعم:** `backend/tasks/email_flows.py` يسجل البريد والعنوان والجسم ثم يعيد sent دون إرسال؛ هذا claim وظيفي خاطئ ويزيد خطر تسجيل محتوى حساس.

## 7. لماذا الاختبارات الخضراء لم تمنع هذه الأخطاء؟

- اختبارات الأموال تستخدم floats بينما PostgreSQL يعيد Decimal.
- أغلب اختبارات backend المحلية تستخدم SQLite وتعطل RLS.
- اختبار PostgreSQL الموجود يبدأ بعد إعداد tenant context يدويًا ولا يغطي login/cookies.
- اختبارات المكونات mockت EnhancedMaterialConsumption بدل اختبار استجابة stock check.
- لا توجد contract tests للـ2FA/OCR/print DTOs أو route constants.
- E2E critical path تزور عددًا محدودًا من الصفحات ولا تنفذ كل العمليات.
- لا توجد Flutter CI.
- لا توجد worker crash/recovery أو migration N-1 upgrade tests.

## 8. نتيجة التحقق

- Full frontend baseline السابق: 48 ملفًا، 190 اختبارًا ناجحًا.
- Full backend baseline السابق: 444 ناجحًا، 4 skipped.
- مراجعة frontend الإضافية: 10 ملفات، 28 اختبارًا ناجحًا؛ عيوب العقود غير مغطاة.
- مراجعة worker/migration المستهدفة: 16 اختبارًا ناجحًا؛ worker coverage في هذا التشغيل 0%.
- npm audit الحالي: صفر ثغرات معروفة في dependencies المسجلة، بما فيها dev dependencies.
- route registry probes: أكدت مسارات 2FA المكررة، غياب OCR، وغياب مسارات Flutter القديمة.
- Decimal reproductions: treatment snapshot وinventory learning فشلا كما هو موضح.
- Flutter SDK: غير متاح محليًا، لذلك لم يُدع نجاح analyze/test.

## 9. ترتيب الإصلاح الموصى به

1. وقف تسجيل headers والأسرار فورًا، ثم تدوير/إبطال أي tokens يُشتبه أنها ظهرت في logs وفق سياسة التشغيل.
2. إصلاح الفاتورة وGoogle backup cross-scope mutation.
3. توسيع Numeric hotfix ليشمل treatment snapshot وinventory learning بالإضافة إلى مسارات Finance الثلاثة.
4. إصلاح Finance RBAC ثم التحقق من RLS bootstrap على دور PostgreSQL مقيد.
5. إصلاح 2FA، stock warnings، وصفة الطباعة، OCR feature gate، وروابط التعافي/الانتحال.
6. تقوية readiness، outbox recovery، migration-upgrade CI، وbackup scheduler.
7. اعتبار Flutter `PARTIAL / NOT RELEASE-READY` حتى إصلاح base URL والعقود وإضافة CI.
8. بعد إغلاق P0/P1 يبدأ تبسيط Finance/Reports طبقًا للخطة الأصلية.

## 10. الحكم النهائي

نجاح lint/build/unit tests يثبت سلامة ما تغطيه فقط، وليس سلامة كل النظام. توجد أخطاء أخرى مؤكدة خارج Finance، ولهذا يجب تحويل العمل من «إعادة تصميم صفحة» إلى برنامج إصلاح قصير الأولوية يبدأ بالأسرار وصحة المستندات المالية والعقود الحرجة، ثم يعود إلى تطوير تجربة المالية والتقارير.

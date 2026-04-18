// ============================================================
// PATCH A.3 — Lazy Import Fixes
// ============================================================
// الملف: frontend/src/App.jsx أو src/router/index.jsx
// ============================================================

// --- المشكلة: lazy() مع named export ---

// ❌ النمط الغلط:
// const TreatmentModal = lazy(() => import('./components/TreatmentModal'));
// لو TreatmentModal.jsx بيعمل:
//   export const TreatmentModal = () => <div>...</div>;  ← named فقط
//   // مفيش export default

// ✅ الإصلاح — اختار واحد من الاتنين:

// الخيار A: أضف default export في الملف نفسه
// في TreatmentModal.jsx:
export const TreatmentModal = () => {
  return <div>...</div>;
};
export default TreatmentModal; // ← أضف السطر ده

// الخيار B: تعديل الـ lazy() import (من غير تعديل الملف الأصلي)
const TreatmentModal = lazy(() =>
  import('./components/TreatmentModal').then((module) => ({
    default: module.TreatmentModal, // ← اسم الـ named export بالظبط
  }))
);

// ============================================================
// PATCH A.4 — فصل API imports عن UI Components
// ============================================================
// الملف: frontend/src/components/TreatmentModal.jsx (أو أي component)
// ============================================================

// ❌ النمط الغلط — استيراد function من api file كـ JSX component:
// import { InventoryItem } from '@/api/inventory'; 
// ثم في JSX:
// <InventoryItem />  ← InventoryItem ده function عادي مش React component!

// ✅ الإصلاح:
// الـ api files يجب أن تُستخدم للـ data fetching فقط:
import { fetchInventoryItems } from '@/api/inventory'; // ← function مش component

// في الـ component:
const [items, setItems] = useState([]);
useEffect(() => {
  fetchInventoryItems(tenantId).then(setItems);
}, [tenantId]);

// في الـ JSX — render الـ data مش الـ function:
// {items.map(item => <div key={item.id}>{item.name}</div>)}

// ============================================================
// SCAN COMMAND — شغّل في terminal لتحديد كل المشاكل:
// grep -rn "lazy(() => import" src/ --include="*.jsx" --include="*.js" | grep -v "default"
// ↑ أي import لـ named export مع lazy هيظهر هنا
// ============================================================

# 🚀 Week 2-3: Performance, TypeScript & UX

## Week 2: Frontend Performance & Code Quality

### الأهداف
- Migration إلى TypeScript
- تحسين أداء الصفحات
- تقسيم الكود (Code Splitting)
- تحسين جودة الكود

---

## الخطوات التفصيلية

### 1. TypeScript Setup (Day 1)

```bash
# Install dependencies
npm install -D typescript @types/react @types/react-dom
npm install -D @types/node

# Create tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### 2. Type Definitions (Day 1-2)

```typescript
// File: src/types/index.ts

// ============= Common Types =============
export type ID = number;

export interface Timestamps {
  createdAt: string;
  updatedAt: string;
  deletedAt?: string | null;
}

// ============= User & Auth =============
export interface User extends Timestamps {
  id: ID;
  email: string;
  name: string;
  role: UserRole;
  phone?: string;
  twoFactorEnabled: boolean;
  isActive: boolean;
  tenantId: ID;
}

export enum UserRole {
  SUPER_ADMIN = 'SUPER_ADMIN',
  CLINIC_ADMIN = 'CLINIC_ADMIN',
  DOCTOR = 'DOCTOR',
  RECEPTIONIST = 'RECEPTIONIST',
  INVENTORY_MANAGER = 'INVENTORY_MANAGER',
  VIEWER = 'VIEWER'
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  accessToken: string;
  user: User;
  requires2FA?: boolean;
  tempToken?: string;
}

// ============= Patient =============
export interface Patient extends Timestamps {
  id: ID;
  name: string;
  phone: string;
  email?: string;
  dateOfBirth: string;
  gender: 'male' | 'female';
  nationalId?: string;
  address?: string;
  notes?: string;
  tenantId: ID;
}

export interface PatientCreateRequest {
  name: string;
  phone: string;
  email?: string;
  dateOfBirth: string;
  gender: 'male' | 'female';
  nationalId?: string;
  address?: string;
}

// ============= Appointment =============
export interface Appointment extends Timestamps {
  id: ID;
  patientId: ID;
  patient?: Patient;
  doctorId: ID;
  doctor?: User;
  date: string;
  time: string;
  duration: number;
  status: AppointmentStatus;
  notes?: string;
  tenantId: ID;
}

export enum AppointmentStatus {
  SCHEDULED = 'scheduled',
  CONFIRMED = 'confirmed',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  NO_SHOW = 'no_show'
}

// ============= Treatment =============
export interface Treatment extends Timestamps {
  id: ID;
  patientId: ID;
  patient?: Patient;
  appointmentId?: ID;
  procedureId: ID;
  procedure?: Procedure;
  toothNumber?: string;
  diagnosis: string;
  notes?: string;
  status: TreatmentStatus;
  cost: number;
  discount: number;
  finalCost: number;
  materials: MaterialConsumption[];
  tenantId: ID;
}

export enum TreatmentStatus {
  PLANNED = 'planned',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled'
}

export interface Procedure extends Timestamps {
  id: ID;
  name: string;
  category: string;
  basePrice: number;
  duration: number;
  description?: string;
  tenantId: ID;
}

// ============= Inventory =============
export interface Material extends Timestamps {
  id: ID;
  name: string;
  type: MaterialType;
  baseUnit: string;
  alertThreshold: number;
  packagingRatio: number;
  category?: string;
  tenantId: ID;
}

export enum MaterialType {
  DIVISIBLE = 'DIVISIBLE',
  NON_DIVISIBLE = 'NON_DIVISIBLE'
}

export interface Warehouse extends Timestamps {
  id: ID;
  name: string;
  type: WarehouseType;
  tenantId: ID;
}

export enum WarehouseType {
  MAIN = 'MAIN',
  CLINIC = 'CLINIC'
}

export interface Batch extends Timestamps {
  id: ID;
  materialId: ID;
  material?: Material;
  batchNumber: string;
  expiryDate: string;
  supplier?: string;
  costPerUnit: number;
  tenantId: ID;
}

export interface StockItem {
  id: ID;
  warehouseId: ID;
  warehouse?: Warehouse;
  batchId: ID;
  batch?: Batch;
  quantity: number;
  tenantId: ID;
}

export interface MaterialConsumption {
  id?: ID;
  materialId: ID;
  materialName: string;
  quantity: number;
  unit: string;
  cost?: number;
  suggested?: boolean;
}

export interface MaterialStockSummary {
  materialId: ID;
  materialName: string;
  materialType: MaterialType;
  totalQuantity: number;
  unit: string;
  alertStatus: 'OK' | 'LOW' | 'CRITICAL';
  batchesCount: number;
  packagingRatio: number;
}

export interface StockAlert {
  materialId: ID;
  materialName: string;
  quantity: number;
  threshold: number;
  daysToExpiry?: number;
  severity: 'info' | 'warning' | 'critical';
}

// ============= API Response Types =============
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  perPage: number;
  totalPages: number;
}

export interface ApiError {
  detail: string;
  code?: string;
  field?: string;
}

// ============= Form Types =============
export interface FormState<T> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  isSubmitting: boolean;
  isDirty: boolean;
}

// ============= Component Props =============
export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
}

export interface ModalProps extends BaseComponentProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}
```

### 3. Code Splitting Implementation (Day 2-3)

```typescript
// File: src/routes/index.tsx

import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';

// Lazy load pages
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Patients = lazy(() => import('@/pages/Patients'));
const PatientDetails = lazy(() => import('@/pages/PatientDetails'));
const Appointments = lazy(() => import('@/pages/Appointments'));
const Inventory = lazy(() => import('@/pages/Inventory'));
const Settings = lazy(() => import('@/pages/Settings'));
const Reports = lazy(() => import('@/pages/Reports'));

// Wrapper component with error boundary
function LazyPage({ 
  Component 
}: { 
  Component: React.LazyExoticComponent<React.ComponentType<any>> 
}) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner fullScreen />}>
        <Component />
      </Suspense>
    </ErrorBoundary>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LazyPage Component={Dashboard} />} />
      <Route path="/patients" element={<LazyPage Component={Patients} />} />
      <Route path="/patients/:id" element={<LazyPage Component={PatientDetails} />} />
      <Route path="/appointments" element={<LazyPage Component={Appointments} />} />
      <Route path="/inventory" element={<LazyPage Component={Inventory} />} />
      <Route path="/settings" element={<LazyPage Component={Settings} />} />
      <Route path="/reports" element={<LazyPage Component={Reports} />} />
    </Routes>
  );
}
```

### 4. Virtual Scrolling (Day 3)

```typescript
// File: src/shared/ui/VirtualList.tsx

import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';

interface VirtualListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  estimateSize?: number;
  overscan?: number;
  className?: string;
}

export function VirtualList<T>({
  items,
  renderItem,
  estimateSize = 80,
  overscan = 5,
  className = ''
}: VirtualListProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan
  });

  return (
    <div 
      ref={parentRef} 
      className={`overflow-auto ${className}`}
    >
      <div 
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative'
        }}
      >
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`
            }}
          >
            {renderItem(items[virtualRow.index], virtualRow.index)}
          </div>
        ))}
      </div>
    </div>
  );
}

// Usage Example
function PatientList({ patients }: { patients: Patient[] }) {
  return (
    <VirtualList
      items={patients}
      renderItem={(patient) => (
        <PatientCard patient={patient} />
      )}
      estimateSize={100}
      className="h-[600px]"
    />
  );
}
```

### 5. Image Optimization (Day 4)

```typescript
// File: src/components/OptimizedImage.tsx

import { useState, useEffect } from 'react';
import { cn } from '@/utils/cn';

interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  className?: string;
  placeholder?: string;
  onLoad?: () => void;
}

export function OptimizedImage({
  src,
  alt,
  width,
  height,
  className,
  placeholder = '/placeholder.svg',
  onLoad
}: OptimizedImageProps) {
  const [imageSrc, setImageSrc] = useState(placeholder);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const img = new Image();
    img.src = src;
    
    img.onload = () => {
      setImageSrc(src);
      setIsLoading(false);
      onLoad?.();
    };
    
    img.onerror = () => {
      setIsLoading(false);
    };
  }, [src, onLoad]);

  return (
    <img
      src={imageSrc}
      alt={alt}
      width={width}
      height={height}
      loading="lazy"
      className={cn(
        'transition-all duration-300',
        isLoading && 'blur-sm',
        className
      )}
    />
  );
}

// File upload compression
import imageCompression from 'browser-image-compression';

export async function compressImage(file: File): Promise<File> {
  const options = {
    maxSizeMB: 1,
    maxWidthOrHeight: 1920,
    useWebWorker: true,
    fileType: 'image/jpeg'
  };

  try {
    const compressed = await imageCompression(file, options);
    return compressed;
  } catch (error) {
    console.error('Image compression failed:', error);
    return file;
  }
}
```

---

## Week 3: UX Improvements & Testing

### 1. Keyboard Shortcuts (Day 1)

```typescript
// File: src/hooks/useKeyboardShortcuts.ts

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface Shortcut {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  action: () => void;
  description: string;
}

export function useKeyboardShortcuts() {
  const navigate = useNavigate();

  const shortcuts: Shortcut[] = [
    {
      key: 'k',
      ctrl: true,
      action: () => openQuickSearch(),
      description: 'بحث سريع'
    },
    {
      key: 'n',
      ctrl: true,
      action: () => openNewPatientModal(),
      description: 'مريض جديد'
    },
    {
      key: 's',
      ctrl: true,
      action: (e) => {
        e.preventDefault();
        submitCurrentForm();
      },
      description: 'حفظ'
    },
    {
      key: '/',
      action: () => focusSearchInput(),
      description: 'التركيز على البحث'
    },
    {
      key: 'Escape',
      action: () => closeTopModal(),
      description: 'إغلاق'
    }
  ];

  useEffect(() => {
    function handleKeyPress(e: KeyboardEvent) {
      shortcuts.forEach(shortcut => {
        const ctrlMatch = shortcut.ctrl === undefined || shortcut.ctrl === e.ctrlKey;
        const shiftMatch = shortcut.shift === undefined || shortcut.shift === e.shiftKey;
        const altMatch = shortcut.alt === undefined || shortcut.alt === e.altKey;
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase();

        if (ctrlMatch && shiftMatch && altMatch && keyMatch) {
          e.preventDefault();
          shortcut.action();
        }
      });
    }

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  return shortcuts;
}

// Shortcuts Helper Modal
export function ShortcutsModal({ isOpen, onClose }: ModalProps) {
  const shortcuts = useKeyboardShortcuts();

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="اختصارات لوحة المفاتيح">
      <div className="space-y-3">
        {shortcuts.map((shortcut, i) => (
          <div key={i} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
            <span className="text-gray-700">{shortcut.description}</span>
            <kbd className="px-3 py-1.5 bg-white border border-gray-300 rounded shadow-sm font-mono text-sm">
              {shortcut.ctrl && 'Ctrl + '}
              {shortcut.shift && 'Shift + '}
              {shortcut.alt && 'Alt + '}
              {shortcut.key.toUpperCase()}
            </kbd>
          </div>
        ))}
      </div>
    </Modal>
  );
}
```

### 2. Command Palette (Day 1-2)

```typescript
// File: src/features/search/CommandPalette.tsx

import { useState, useMemo } from 'react';
import { Command } from 'cmdk';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  User, Calendar, Package, Settings,
  FileText, Plus, Search 
} from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');

  // Fetch data for search
  const { data: patients } = useQuery({
    queryKey: ['patients'],
    queryFn: fetchPatients,
    enabled: isOpen
  });

  const { data: appointments } = useQuery({
    queryKey: ['appointments'],
    queryFn: fetchAppointments,
    enabled: isOpen
  });

  // Filter results
  const filteredPatients = useMemo(() => {
    if (!search || !patients) return [];
    return patients
      .filter(p => 
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.phone.includes(search)
      )
      .slice(0, 5);
  }, [search, patients]);

  return (
    <Command.Dialog 
      open={isOpen} 
      onOpenChange={onClose}
      className="fixed top-1/4 left-1/2 -translate-x-1/2 w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden"
    >
      <div className="flex items-center border-b border-gray-200 px-4">
        <Search className="text-gray-400" size={20} />
        <Command.Input
          value={search}
          onValueChange={setSearch}
          placeholder="ابحث عن أي شيء..."
          className="w-full px-4 py-4 text-lg outline-none"
        />
      </div>

      <Command.List className="max-h-96 overflow-y-auto p-2">
        <Command.Empty className="py-8 text-center text-gray-500">
          لا توجد نتائج
        </Command.Empty>

        {/* Quick Actions */}
        <Command.Group heading="إجراءات سريعة">
          <Command.Item
            onSelect={() => {
              openNewPatientModal();
              onClose();
            }}
            className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 cursor-pointer"
          >
            <Plus size={18} />
            <span>مريض جديد</span>
          </Command.Item>
          
          <Command.Item
            onSelect={() => {
              openNewAppointmentModal();
              onClose();
            }}
            className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 cursor-pointer"
          >
            <Calendar size={18} />
            <span>موعد جديد</span>
          </Command.Item>
        </Command.Group>

        {/* Patients */}
        {filteredPatients.length > 0 && (
          <Command.Group heading="المرضى">
            {filteredPatients.map(patient => (
              <Command.Item
                key={patient.id}
                onSelect={() => {
                  navigate(`/patients/${patient.id}`);
                  onClose();
                }}
                className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 cursor-pointer"
              >
                <User size={18} className="text-gray-400" />
                <div className="flex-1">
                  <div className="font-medium">{patient.name}</div>
                  <div className="text-sm text-gray-500">{patient.phone}</div>
                </div>
              </Command.Item>
            ))}
          </Command.Group>
        )}

        {/* Navigation */}
        <Command.Group heading="الصفحات">
          <Command.Item
            onSelect={() => {
              navigate('/inventory');
              onClose();
            }}
            className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 cursor-pointer"
          >
            <Package size={18} />
            <span>المخزون</span>
          </Command.Item>
          
          <Command.Item
            onSelect={() => {
              navigate('/reports');
              onClose();
            }}
            className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 cursor-pointer"
          >
            <FileText size={18} />
            <span>التقارير</span>
          </Command.Item>
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}
```

### 3. Better Form Validation (Day 2-3)

```typescript
// File: src/hooks/useForm.ts

import { useState, useCallback } from 'react';

interface UseFormOptions<T> {
  initialValues: T;
  validate?: (values: T) => Partial<Record<keyof T, string>>;
  onSubmit: (values: T) => Promise<void> | void;
}

export function useForm<T extends Record<string, any>>({
  initialValues,
  validate,
  onSubmit
}: UseFormOptions<T>) {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isDirty = JSON.stringify(values) !== JSON.stringify(initialValues);

  const handleChange = useCallback((
    name: keyof T,
    value: any
  ) => {
    setValues(prev => ({ ...prev, [name]: value }));
    
    // Validate field if touched
    if (touched[name] && validate) {
      const newErrors = validate({ ...values, [name]: value });
      setErrors(prev => ({ ...prev, [name]: newErrors[name] }));
    }
  }, [values, touched, validate]);

  const handleBlur = useCallback((name: keyof T) => {
    setTouched(prev => ({ ...prev, [name]: true }));
    
    if (validate) {
      const newErrors = validate(values);
      setErrors(prev => ({ ...prev, [name]: newErrors[name] }));
    }
  }, [values, validate]);

  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault();
    
    // Mark all fields as touched
    const allTouched = Object.keys(values).reduce((acc, key) => {
      acc[key as keyof T] = true;
      return acc;
    }, {} as Partial<Record<keyof T, boolean>>);
    setTouched(allTouched);
    
    // Validate
    if (validate) {
      const newErrors = validate(values);
      setErrors(newErrors);
      
      if (Object.keys(newErrors).length > 0) {
        return;
      }
    }
    
    // Submit
    setIsSubmitting(true);
    try {
      await onSubmit(values);
    } finally {
      setIsSubmitting(false);
    }
  }, [values, validate, onSubmit]);

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);

  return {
    values,
    errors,
    touched,
    isSubmitting,
    isDirty,
    handleChange,
    handleBlur,
    handleSubmit,
    reset,
    setValues,
    setErrors
  };
}

// Usage Example
function PatientForm() {
  const form = useForm({
    initialValues: {
      name: '',
      phone: '',
      email: ''
    },
    validate: (values) => {
      const errors: any = {};
      
      if (!values.name || values.name.length < 2) {
        errors.name = 'الاسم يجب أن يكون حرفين على الأقل';
      }
      
      if (!values.phone.match(/^01[0-2,5]{1}[0-9]{8}$/)) {
        errors.phone = 'رقم هاتف غير صحيح';
      }
      
      if (values.email && !values.email.includes('@')) {
        errors.email = 'بريد إلكتروني غير صحيح';
      }
      
      return errors;
    },
    onSubmit: async (values) => {
      await createPatient(values);
      toast.success('تم إضافة المريض بنجاح');
    }
  });

  return (
    <form onSubmit={form.handleSubmit}>
      <Input
        label="الاسم"
        value={form.values.name}
        onChange={(e) => form.handleChange('name', e.target.value)}
        onBlur={() => form.handleBlur('name')}
        error={form.touched.name ? form.errors.name : undefined}
        required
      />
      
      <Button 
        type="submit" 
        isLoading={form.isSubmitting}
        disabled={!form.isDirty}
      >
        حفظ
      </Button>
    </form>
  );
}
```

---

## Testing Implementation

### Unit Tests Setup

```bash
# Install testing libraries
npm install -D vitest @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom
```

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/setupTests.ts',
      ]
    }
  }
});
```

```typescript
// src/setupTests.ts
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
});
```

### Example Tests

```typescript
// src/shared/ui/__tests__/Button.test.tsx

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '../Button';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    
    await userEvent.click(screen.getByText('Click'));
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('shows loading state', () => {
    render(<Button isLoading>Loading</Button>);
    expect(screen.getByText('Loading')).toBeDisabled();
  });
});
```

---

## Performance Checklist

- [ ] TypeScript migration complete
- [ ] Code splitting implemented
- [ ] Virtual scrolling for lists
- [ ] Images optimized
- [ ] Bundle size < 500KB (gzipped)
- [ ] First Contentful Paint < 1s
- [ ] Time to Interactive < 2s

## UX Checklist

- [ ] Keyboard shortcuts working
- [ ] Command palette functional
- [ ] Form validation smooth
- [ ] Loading states everywhere
- [ ] Error boundaries in place
- [ ] Onboarding tour ready

## Testing Checklist

- [ ] Unit tests > 70% coverage
- [ ] Integration tests for key flows
- [ ] E2E tests for critical paths
- [ ] Performance tests passing

---

**Status**: Ready for Week 2-3 🚀

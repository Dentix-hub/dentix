# 📦 نظام المخزون المحسّن - خطة تفصيلية

## الهدف
تحويل نظام المخزون من معقد إلى بسيط وسريع مع الحفاظ على القوة التقنية

---

## المشاكل الحالية

### 1. تجربة المستخدم
- ❌ خطوات كثيرة لتسجيل استخدام مادة
- ❌ رسائل خطأ غير واضحة
- ❌ عدم وجود quick actions
- ❌ Material Sessions يدوية

### 2. الأداء
- ❌ تحميل كل المواد مرة واحدة
- ❌ عدم وجود caching
- ❌ Batch operations غير محسّنة

### 3. الذكاء
- ❌ Smart Learning موجود لكن مخفي
- ❌ لا توجد اقتراحات واضحة
- ❌ عدم وجود pre-flight checks

---

## الحل المقترح

### Phase 1: تحسين واجهة استهلاك المواد

#### 1. Enhanced Material Consumption Modal

```typescript
// File: src/features/inventory/EnhancedMaterialConsumption.tsx

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface MaterialConsumptionProps {
  procedure: Procedure;
  patientAge?: number;
  onSave: (materials: MaterialConsumption[]) => void;
  onClose: () => void;
}

export function EnhancedMaterialConsumption({
  procedure,
  patientAge,
  onSave,
  onClose
}: MaterialConsumptionProps) {
  const queryClient = useQueryClient();
  const currentUser = useAuth();
  
  const [materials, setMaterials] = useState<MaterialConsumption[]>([]);
  const [showMaterialPicker, setShowMaterialPicker] = useState(false);

  // Fetch suggested materials with smart learning
  const { data: suggestions, isLoading } = useQuery({
    queryKey: ['material-suggestions', procedure.id, currentUser.id, patientAge],
    queryFn: () => getMaterialSuggestions({
      procedureId: procedure.id,
      doctorId: currentUser.id,
      patientAge
    })
  });

  // Pre-flight stock check
  const { data: stockCheck } = useQuery({
    queryKey: ['stock-check', materials.map(m => ({ id: m.materialId, qty: m.quantity }))],
    queryFn: () => checkMaterialsAvailability(materials),
    enabled: materials.length > 0
  });

  // Auto-populate with suggestions
  useEffect(() => {
    if (suggestions && materials.length === 0) {
      setMaterials(
        suggestions.map(s => ({
          materialId: s.material_id,
          materialName: s.material.name,
          quantity: s.suggested_quantity || s.default_quantity,
          unit: s.material.base_unit,
          suggested: true,
          confidence: s.confidence,
          reason: s.reason
        }))
      );
    }
  }, [suggestions]);

  // Get warnings from stock check
  const warnings = useMemo(() => {
    if (!stockCheck) return [];
    
    const warns = [];
    
    stockCheck.forEach(check => {
      if (check.available === 0) {
        warns.push({
          type: 'critical',
          materialId: check.materialId,
          message: `${check.materialName} غير متوفر`,
          action: 'show_alternatives'
        });
      } else if (check.available < check.required) {
        warns.push({
          type: 'warning',
          materialId: check.materialId,
          message: `${check.materialName} غير كافي (متوفر: ${check.available})`,
          action: 'adjust_quantity'
        });
      } else if (check.daysToExpiry < 7) {
        warns.push({
          type: 'info',
          materialId: check.materialId,
          message: `تنتهي صلاحية ${check.materialName} خلال ${check.daysToExpiry} أيام`,
          action: 'use_this_batch'
        });
      }
    });
    
    return warns;
  }, [stockCheck]);

  const saveMutation = useMutation({
    mutationFn: async (data: MaterialConsumption[]) => {
      // Save consumption and update stock
      await saveConsumption({
        procedureId: procedure.id,
        materials: data
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['inventory-stock']);
      onSave(materials);
      toast.success('تم حفظ المواد بنجاح');
      onClose();
    }
  });

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <Modal size="lg" onClose={onClose}>
      <ModalHeader>
        <div>
          <h2 className="text-xl font-bold">مواد الإجراء</h2>
          <p className="text-sm text-gray-600">{procedure.name}</p>
        </div>
      </ModalHeader>

      <ModalBody>
        {/* Warnings Section */}
        {warnings.length > 0 && (
          <div className="space-y-2 mb-6">
            {warnings.map((warning, idx) => (
              <WarningAlert
                key={idx}
                warning={warning}
                onAction={() => handleWarningAction(warning)}
              />
            ))}
          </div>
        )}

        {/* Empty State */}
        {materials.length === 0 ? (
          <EmptyMaterialsState
            procedureId={procedure.id}
            onAddManually={() => setShowMaterialPicker(true)}
          />
        ) : (
          <>
            {/* Materials List */}
            <div className="space-y-3 mb-6">
              {materials.map((material, idx) => (
                <SmartMaterialRow
                  key={idx}
                  material={material}
                  stockInfo={stockCheck?.find(s => s.materialId === material.materialId)}
                  onChange={(updated) => updateMaterial(idx, updated)}
                  onRemove={() => removeMaterial(idx)}
                />
              ))}
            </div>

            {/* Add More Button */}
            <Button
              variant="ghost"
              onClick={() => setShowMaterialPicker(true)}
              className="w-full"
            >
              + إضافة مادة أخرى
            </Button>
          </>
        )}

        {/* Cost Analysis */}
        {materials.length > 0 && (
          <CostAnalysisCard
            materials={materials}
            procedurePrice={procedure.price}
            className="mt-6"
          />
        )}
      </ModalBody>

      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>
          إلغاء
        </Button>
        <Button
          onClick={() => saveMutation.mutate(materials)}
          disabled={materials.length === 0 || warnings.some(w => w.type === 'critical')}
          isLoading={saveMutation.isPending}
        >
          حفظ وخصم من المخزون
        </Button>
      </ModalFooter>

      {/* Material Picker Modal */}
      {showMaterialPicker && (
        <SmartMaterialPicker
          isOpen={showMaterialPicker}
          onClose={() => setShowMaterialPicker(false)}
          onSelect={(material) => {
            addMaterial(material);
            setShowMaterialPicker(false);
          }}
          excludeIds={materials.map(m => m.materialId)}
        />
      )}
    </Modal>
  );
}
```

#### 2. Smart Material Row Component

```typescript
// File: src/features/inventory/SmartMaterialRow.tsx

interface SmartMaterialRowProps {
  material: MaterialConsumption;
  stockInfo?: StockCheckResult;
  onChange: (material: MaterialConsumption) => void;
  onRemove: () => void;
}

export function SmartMaterialRow({
  material,
  stockInfo,
  onChange,
  onRemove
}: SmartMaterialRowProps) {
  const [mode, setMode] = useState<'quick' | 'custom'>('quick');

  // Generate quick amounts based on unit
  const quickAmounts = useMemo(() => {
    if (material.unit === 'ml' || material.unit === 'g') {
      return [
        { value: 0.1, label: '0.1' },
        { value: 0.25, label: '¼' },
        { value: 0.5, label: '½' },
        { value: 1, label: '1' }
      ];
    } else {
      return [
        { value: 1, label: '1' },
        { value: 2, label: '2' },
        { value: 3, label: '3' },
        { value: 5, label: '5' }
      ];
    }
  }, [material.unit]);

  // Stock status
  const stockStatus = useMemo(() => {
    if (!stockInfo) return 'unknown';
    if (stockInfo.available === 0) return 'out';
    if (stockInfo.available < material.quantity) return 'insufficient';
    if (stockInfo.available < material.quantity * 2) return 'low';
    return 'ok';
  }, [stockInfo, material.quantity]);

  return (
    <div className="bg-white border-2 border-gray-200 rounded-xl p-4 hover:border-primary/30 transition-all">
      <div className="flex items-start gap-4">
        {/* Material Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-bold text-lg truncate">{material.materialName}</h4>
            
            {material.suggested && (
              <Badge variant="primary" size="sm">
                ✨ مقترح
              </Badge>
            )}
          </div>

          {/* Suggestion Reason */}
          {material.reason && material.suggested && (
            <p className="text-sm text-gray-600 mb-2">
              💡 {material.reason}
              {material.confidence && (
                <span className="text-xs text-gray-500">
                  {' '}(ثقة: {Math.round(material.confidence * 100)}%)
                </span>
              )}
            </p>
          )}

          {/* Stock Status */}
          <div className="flex items-center gap-3 flex-wrap">
            <StockStatusBadge status={stockStatus} />
            
            {stockInfo && (
              <span className="text-sm text-gray-600">
                المتوفر: <strong>{stockInfo.available} {material.unit}</strong>
              </span>
            )}
            
            {stockInfo?.daysToExpiry && stockInfo.daysToExpiry < 30 && (
              <Badge variant="warning" size="sm">
                ⏰ صلاحية: {stockInfo.daysToExpiry} يوم
              </Badge>
            )}
          </div>
        </div>

        {/* Quantity Selector */}
        <div className="flex-shrink-0">
          {mode === 'quick' ? (
            <div className="space-y-2">
              <div className="text-xs text-gray-500 text-center mb-1">
                اختر الكمية
              </div>
              
              <div className="grid grid-cols-2 gap-2 min-w-[160px]">
                {quickAmounts.map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => onChange({ ...material, quantity: value })}
                    className={cn(
                      'px-4 py-3 rounded-lg border-2 font-bold transition-all',
                      'hover:scale-105 active:scale-95',
                      material.quantity === value
                        ? 'border-primary bg-primary text-white shadow-lg'
                        : 'border-gray-200 hover:border-primary/50 hover:bg-primary/5'
                    )}
                  >
                    <div className="text-lg">{label}</div>
                    <div className="text-xs opacity-80">{material.unit}</div>
                  </button>
                ))}
              </div>
              
              <button
                type="button"
                onClick={() => setMode('custom')}
                className="w-full text-sm text-primary hover:underline"
              >
                ✏️ كمية مخصصة
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Input
                type="number"
                step="0.01"
                min="0"
                value={material.quantity}
                onChange={(e) => onChange({
                  ...material,
                  quantity: parseFloat(e.target.value) || 0
                })}
                className="w-24 text-center"
                autoFocus
              />
              <span className="text-sm text-gray-600">{material.unit}</span>
              <IconButton
                icon={<Check />}
                variant="ghost"
                size="sm"
                onClick={() => setMode('quick')}
              />
            </div>
          )}
        </div>

        {/* Remove Button */}
        <IconButton
          icon={<X />}
          variant="ghost"
          size="sm"
          onClick={onRemove}
          className="text-red-500 hover:bg-red-50"
        />
      </div>

      {/* Alternatives (if out of stock) */}
      {stockStatus === 'out' && (
        <AlternativeMaterialsSection
          materialId={material.materialId}
          onSelect={(alt) => onChange({
            ...material,
            materialId: alt.id,
            materialName: alt.name,
            unit: alt.baseUnit
          })}
        />
      )}
    </div>
  );
}
```

#### 3. Smart Material Picker

```typescript
// File: src/features/inventory/SmartMaterialPicker.tsx

export function SmartMaterialPicker({
  isOpen,
  onClose,
  onSelect,
  excludeIds = []
}: SmartMaterialPickerProps) {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<'all' | 'recent' | 'popular'>('popular');

  const { data: materials } = useQuery({
    queryKey: ['materials'],
    queryFn: fetchMaterials
  });

  const { data: recentMaterials } = useQuery({
    queryKey: ['recent-materials'],
    queryFn: fetchRecentlyUsedMaterials
  });

  const { data: stockInfo } = useQuery({
    queryKey: ['materials-stock'],
    queryFn: fetchMaterialsStockInfo
  });

  // Filter and sort
  const displayMaterials = useMemo(() => {
    let filtered = materials || [];

    // Exclude already selected
    filtered = filtered.filter(m => !excludeIds.includes(m.id));

    // Search
    if (search) {
      filtered = filtered.filter(m =>
        m.name.toLowerCase().includes(search.toLowerCase())
      );
    }

    // Category
    if (category === 'recent') {
      const recentIds = recentMaterials?.map(r => r.id) || [];
      filtered = filtered.filter(m => recentIds.includes(m.id));
    } else if (category === 'popular') {
      // Sort by usage frequency
      filtered = filtered.sort((a, b) => 
        (b.usageCount || 0) - (a.usageCount || 0)
      );
    }

    return filtered.slice(0, 20);
  }, [materials, search, category, excludeIds, recentMaterials]);

  return (
    <Modal size="lg" isOpen={isOpen} onClose={onClose}>
      <ModalHeader>
        <h2>اختر مادة</h2>
      </ModalHeader>

      <ModalBody>
        {/* Search */}
        <Input
          placeholder="بحث سريع..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          leftIcon={<Search />}
          className="mb-4"
          autoFocus
        />

        {/* Category Tabs */}
        <div className="flex gap-2 mb-4">
          <TabButton
            active={category === 'popular'}
            onClick={() => setCategory('popular')}
          >
            🔥 الأكثر استخداماً
          </TabButton>
          <TabButton
            active={category === 'recent'}
            onClick={() => setCategory('recent')}
          >
            🕐 مستخدمة مؤخراً
          </TabButton>
          <TabButton
            active={category === 'all'}
            onClick={() => setCategory('all')}
          >
            📋 الكل
          </TabButton>
        </div>

        {/* Materials Grid */}
        <div className="grid grid-cols-2 gap-3 max-h-[400px] overflow-y-auto">
          {displayMaterials.map(material => {
            const stock = stockInfo?.find(s => s.materialId === material.id);
            
            return (
              <button
                key={material.id}
                onClick={() => onSelect(material)}
                className="p-4 text-right border-2 border-gray-200 rounded-xl hover:border-primary hover:bg-primary/5 transition-all"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-sm">{material.name}</h3>
                  {stock && (
                    <StockBadge
                      quantity={stock.quantity}
                      threshold={material.alertThreshold}
                      size="sm"
                    />
                  )}
                </div>
                
                <div className="text-xs text-gray-600 space-y-1">
                  <div>الوحدة: {material.baseUnit}</div>
                  {stock && (
                    <div className="font-medium">
                      المتوفر: {stock.quantity} {material.baseUnit}
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {displayMaterials.length === 0 && (
          <EmptyState
            icon="🔍"
            title="لا توجد نتائج"
            description="جرب البحث بكلمة أخرى"
          />
        )}
      </ModalBody>
    </Modal>
  );
}
```

---

### Phase 2: Backend Enhancements

#### 1. Smart Suggestions API

```python
# File: backend/routers/inventory_smart.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.database import get_db
from backend.auth import get_current_user
from backend.services.material_suggestion_service import MaterialSuggestionService
from backend.schemas.inventory import MaterialSuggestion

router = APIRouter(prefix="/api/inventory/smart", tags=["inventory-smart"])

@router.get("/suggestions/{procedure_id}", response_model=List[MaterialSuggestion])
async def get_material_suggestions(
    procedure_id: int,
    patient_age: Optional[int] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get smart material suggestions for a procedure
    Based on:
    - Procedure's default BOM
    - Doctor's historical usage
    - Patient age adjustments
    - Recent trends
    """
    
    service = MaterialSuggestionService(db)
    
    suggestions = service.get_suggested_materials(
        procedure_id=procedure_id,
        doctor_id=current_user.id,
        patient_age=patient_age
    )
    
    return suggestions

@router.post("/check-availability")
async def check_materials_availability(
    materials: List[dict],  # [{ material_id, quantity }]
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Pre-flight check for materials availability
    Returns warnings and critical issues
    """
    
    from backend.services.inventory_preflight_service import InventoryPreflightService
    
    service = InventoryPreflightService(db)
    
    results = []
    for mat in materials:
        check = service.check_material(
            material_id=mat['material_id'],
            required_quantity=mat['quantity'],
            tenant_id=current_user.tenant_id
        )
        results.append(check)
    
    return results

@router.get("/alternatives/{material_id}")
async def get_material_alternatives(
    material_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Find alternative materials"""
    
    from backend.services.material_alternatives_service import MaterialAlternativesService
    
    service = MaterialAlternativesService(db)
    alternatives = service.find_alternatives(
        material_id=material_id,
        tenant_id=current_user.tenant_id
    )
    
    return alternatives
```

#### 2. Auto Session Management

```python
# File: backend/services/auto_session_service.py

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models.inventory import MaterialSession, StockItem

class AutoSessionService:
    """Automatically manage material sessions"""
    
    SESSION_TIMEOUT = 4  # hours
    
    @staticmethod
    def start_or_reuse_session(
        stock_item_id: int,
        doctor_id: int,
        db: Session
    ) -> MaterialSession:
        """
        Start new session or reuse active one
        """
        
        # Check for active session
        active_session = db.query(MaterialSession).filter(
            MaterialSession.stock_item_id == stock_item_id,
            MaterialSession.status == "ACTIVE",
            MaterialSession.doctor_id == doctor_id
        ).first()
        
        if active_session:
            # Refresh timestamp
            active_session.last_used = datetime.utcnow()
            db.commit()
            return active_session
        
        # Create new session
        session = MaterialSession(
            stock_item_id=stock_item_id,
            doctor_id=doctor_id,
            opened_at=datetime.utcnow(),
            last_used=datetime.utcnow(),
            status="ACTIVE",
            remaining_est=1.0
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
    
    @staticmethod
    def auto_close_idle_sessions(db: Session):
        """
        Background task: Close sessions idle for > 4 hours
        """
        
        timeout_threshold = datetime.utcnow() - timedelta(
            hours=AutoSessionService.SESSION_TIMEOUT
        )
        
        idle_sessions = db.query(MaterialSession).filter(
            MaterialSession.status == "ACTIVE",
            MaterialSession.last_used < timeout_threshold
        ).all()
        
        for session in idle_sessions:
            # Estimate consumption (simple: assume fully used)
            session.status = "CLOSED"
            session.closed_at = datetime.utcnow()
            session.total_amount_consumed = session.remaining_est
            session.close_reason = "AUTO_TIMEOUT"
        
        db.commit()
        
        return len(idle_sessions)
```

---

## Implementation Timeline

### Week 1: Frontend UI
- Day 1-2: Enhanced Consumption Modal
- Day 3-4: Smart Material Row
- Day 5: Material Picker

### Week 2: Backend Logic
- Day 1-2: Smart Suggestions API
- Day 3: Pre-flight Checks
- Day 4: Auto Session Management
- Day 5: Testing

### Week 3: Integration & Polish
- Day 1-2: Integration Testing
- Day 3: Bug Fixes
- Day 4-5: Documentation & Training

---

## Success Metrics

### Speed
- ✅ Material consumption: 10 seconds (vs 3-4 minutes)
- ✅ 95% faster workflow

### Accuracy
- ✅ Smart suggestions 85%+ accurate
- ✅ 90% reduction in manual errors

### Adoption
- ✅ 80%+ users prefer new system
- ✅ Support tickets -50%

---

**Status**: Ready for Implementation 🚀

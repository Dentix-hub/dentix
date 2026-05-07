import { useState, useEffect, useMemo, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Modal, Button, Badge } from '@/shared/ui';
import { SmartMaterialRow } from './SmartMaterialRow';
import { api } from '@/api';
import { toast } from 'react-hot-toast';
import { Plus, CheckCircle, AlertTriangle, Clock } from 'lucide-react';
import { cn } from '@/utils/cn';
export function EnhancedMaterialConsumption({
    procedure,
    patientAge,
    availableMaterials = [],
    initialMaterials = [], // [{ material_id, quantity, unit }]
    mode = 'smart', // 'smart' | 'manual'
    onSave,
    onClose,
    isOpen,
    isLoading = false
}) {
    const queryClient = useQueryClient();
    // Track if we've initialized for this modal session
    const hasInitializedRef = useRef(false);
    const prevIsOpenRef = useRef(false);
    // Initialize with empty - will be populated by useEffect
    const [materials, setMaterials] = useState([]);
    const [pickerOpen, setPickerOpen] = useState(false);
    // Auto-open picker for manual mode
    useEffect(() => {
        console.log('[EMC_DEBUG] Picker effect triggered:', { isOpen, mode, materialsCount: availableMaterials?.length });
        if (isOpen && mode === 'manual') {
            setPickerOpen(true);
        } else {
            setPickerOpen(false);
        }
    }, [isOpen, mode, availableMaterials]); // Added availableMaterials to dependencies
    // CRITICAL FIX: Only sync from props when modal OPENS (transition from closed to open)
    // Never overwrite while modal is already open
    useEffect(() => {
        const wasOpen = prevIsOpenRef.current;
        prevIsOpenRef.current = isOpen;
        // Case 1: Modal just opened (transition from closed to open)
        if (isOpen && !wasOpen) {
            hasInitializedRef.current = false; // Reset for new session
        }
        // Case 2: Modal closed - reset for next time
        if (!isOpen && wasOpen) {
            hasInitializedRef.current = false;
            setMaterials([]);
            return;
        }
        // Case 3: Modal is open and we have data to initialize with
        // Only initialize if availableMaterials is populated (unless it's genuinely empty)
        const isReadyToInitialize = isOpen && !hasInitializedRef.current && (availableMaterials.length > 0 || !isLoading);
        
        if (isReadyToInitialize && Array.isArray(initialMaterials)) {
            console.log('[EMC_DEBUG] Initializing materials from:', initialMaterials.length, 'items');
            const mapped = initialMaterials.map(m => {
                const targetId = parseInt(m.material_id || m.id || m.materialId);
                const matInfo = availableMaterials.find(am => (am.material_id || am.id) === targetId) || {};
                
                return {
                    id: Date.now() + Math.random(),
                    material_id: targetId,
                    material_name: matInfo.material_name || matInfo.name || m.material_name || m.name || 'Unknown',
                    quantity: parseFloat(m.quantity) || 1,
                    unit: matInfo.unit || matInfo.base_unit || m.unit || 'وحدة',
                    is_manual: m.is_manual_override || m.is_manual || false
                };
            });
            setMaterials(mapped);
            hasInitializedRef.current = true;
            console.log('[EnhancedMaterialConsumption] Initialized materials:', mapped);
        }
    }, [isOpen, availableMaterials, initialMaterials]);
    // Pre-flight Stock Check
    const { data: rawStockCheckData } = useQuery({
        queryKey: ['stock-check', materials],
        queryFn: async () => {
            if (materials.length === 0) return [];
            const payload = materials.map(m => ({ 
                material_id: m.material_id || m.id, 
                quantity: m.quantity 
            }));
            const res = await api.post('/api/v1/inventory/smart/check-availability', payload);
            const rawData = res.data?.data;
            return Array.isArray(rawData) ? rawData : [];
        },
        enabled: materials.length > 0
    });
    const stockCheckData = Array.isArray(rawStockCheckData) ? rawStockCheckData : [];
    const addManualMaterial = (materialId) => {
        const mat = availableMaterials.find(m => (m.material_id || m.id) === parseInt(materialId));
        if (!mat) return;
        // Prevent duplicates
        if (materials.some(m => (m.material_id || m.materialId) === (mat.material_id || mat.id))) {
            toast.error("هذه المادة مضافة بالفعل");
            setPickerOpen(false);
            return;
        }
        // Check for smart suggestion (Relative Weight)
        let initialQuantity = 1;
        // Check if material is divisible (by type or unit)
        const isDivisible = mat.material_type === 'DIVISIBLE' || mat.type === 'DIVISIBLE' || ['ml', 'g', 'cm'].includes(mat.base_unit?.toLowerCase());
        if (isDivisible) {
            // FIX: For manual addition of divisible items (g/ml), always start with small relative weight (0.1)
            // The user prefers "Relative" increment logic over the static BOM definition (which might be large, e.g. 1.5g)
            initialQuantity = 0.1;
        }
        setMaterials(prev => [
            ...prev,
            {
                id: Date.now(),
                material_id: mat.material_id || mat.id,
                material_name: mat.material_name || mat.name,
                quantity: initialQuantity,
                unit: mat.unit || mat.base_unit,
                is_manual: true
            }
        ]);
        setPickerOpen(false);
    };
    // Analyze Warnings
    const warnings = useMemo(() => {
        if (!stockCheckData) return [];
        return stockCheckData.filter(check => check.status !== 'OK').map(check => ({
            type: check.status === 'CRITICAL' ? 'critical' : 'warning',
            message: `${check.material_name}: ${check.message}`,
            materialId: check.material_id
        }));
    }, [stockCheckData]);
    const hasCritical = warnings.some(w => w.type === 'critical');

    const availableMaterialsList = useMemo(() => {
        if (!Array.isArray(availableMaterials)) return [];
        // Filter out materials already in the list
        return availableMaterials.filter(am => 
            !materials.some(m => (m.material_id || m.id) === (am.material_id || am.id))
        );
    }, [availableMaterials, materials]);

    const handleSave = async () => {
        try {
            onSave(materials);
            onClose();
        } catch (error) {
            console.error("Save failed", error);
        }
    };
    const updateMaterial = (index, updated) => {
        const newMats = [...materials];
        newMats[index] = updated;
        setMaterials(newMats);
    };
    const removeMaterial = (index) => {
        const newMats = [...materials];
        newMats.splice(index, 1);
        setMaterials(newMats);
    };
    return (
        <Modal isOpen={isOpen} onClose={onClose} size="lg" title={`المواد المستخدمة: ${procedure?.name || ''}`}>
            {/* DEBUG BANNER - ALWAYS VISIBLE IF DATA EXISTS */}
            {availableMaterials?.length > 0 && (
                <div className="bg-red-600 text-white p-1 text-[10px] text-center font-bold">
                    DEBUG: {availableMaterials.length} مواد متوفرة | {availableMaterialsList.length} مصفاة
                </div>
            )}
            <div className="space-y-6">
                {/* Warnings */}
                {warnings.length > 0 && (
                    <div className="space-y-2">
                        {warnings.map((w, i) => (
                            <div key={i} className={`p-3 rounded-lg flex items-center gap-2 text-sm font-bold border ${w.type === 'critical' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-yellow-50 text-yellow-800 border-yellow-200'
                                }`}>
                                <AlertTriangle size={18} />
                                {w.message}
                            </div>
                        ))}
                    </div>
                )}
                {materials.length === 0 && !pickerOpen ? (
                    <div className="text-center py-12 bg-gray-50 rounded-xl border border-dashed border-gray-300">
                        <p className="text-gray-500 mb-4">لا توجد مواد مقترحة لهذا الإجراء</p>
                        <Button variant="outline" onClick={() => setPickerOpen(true)}>
                            + إضافة يدوية
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
                        {materials.map((mat, idx) => (
                            <SmartMaterialRow
                                key={mat.material_id || mat.id || idx}
                                material={mat}
                                stockInfo={stockCheckData?.find(s => s.material_id === (mat.material_id || mat.id))}
                                onChange={(updated) => updateMaterial(idx, updated)}
                                onRemove={() => removeMaterial(idx)}
                            />
                        ))}
                        {/* Inline Picker */}
                        {pickerOpen && (
                            <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-100 animate-in slide-in-from-top-2">
                                <div className="flex justify-between items-center mb-3">
                                    <label className="block text-sm font-bold text-blue-900">اختر مادة من المخزون:</label>
                                    <Button size="sm" variant="ghost" onClick={() => setPickerOpen(false)} className="h-7 text-xs">إلغاء</Button>
                                </div>
                                
                                <div className="grid grid-cols-1 gap-2 max-h-[200px] overflow-y-auto p-1">
                                    {isLoading ? (
                                        <div className="text-center py-4 text-blue-600 text-sm animate-pulse">جاري تحميل المواد...</div>
                                    ) : availableMaterialsList.length > 0 ? (
                                        availableMaterialsList.map((m, idx) => {
                                            const id = m.material_id || m.id;
                                            const name = m.material_name || m.name;
                                            const unitDisplay = m.unit || m.base_unit || '';
                                            const qtyDisplay = m.total_quantity !== undefined ? m.total_quantity : (m.quantity || 0);
                                            
                                            if (!id) return null;

                                            return (
                                                <button
                                                    key={`${id}-${idx}`}
                                                    onClick={() => {
                                                        console.log('[EMC_ACTION] Adding material:', id);
                                                        addManualMaterial(id);
                                                    }}
                                                    className="flex justify-between items-center p-3 bg-white border border-blue-200 rounded-lg hover:border-primary hover:shadow-sm transition-all text-right group"
                                                >
                                                    <div className="flex flex-col items-end">
                                                        <span className="font-bold text-slate-800 group-hover:text-primary transition-colors">{name}</span>
                                                        <span className="text-[10px] text-slate-500">{m.brand || ''}</span>
                                                    </div>
                                                    <div className="flex flex-col items-start text-left">
                                                        <Badge variant="outline" className="text-[10px] bg-slate-50">
                                                            {qtyDisplay} {unitDisplay} متوفر
                                                        </Badge>
                                                    </div>
                                                </button>
                                            );
                                        })
                                    ) : (
                                        <div className="text-center py-6 bg-white rounded-lg border border-dashed border-blue-200">
                                            <p className="text-sm text-slate-500">لا توجد مواد إضافية في المخزن</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                )}
                <div className="pt-4 border-t border-gray-100 flex justify-between items-center">
                    <Button variant="ghost" className="text-gray-500" onClick={onClose}>
                        إلغاء
                    </Button>
                    <div className="flex gap-3">
                        {!pickerOpen && (
                            <div className="flex flex-col items-center">
                                <div className="flex gap-2">
                                    <Button 
                                        variant="outline" 
                                        size="sm"
                                        onClick={() => {
                                            console.log('[EMC_DEBUG_MANUAL] Current State:', { availableMaterials, materials, initialMaterials });
                                            queryClient.invalidateQueries(['stock-summary']);
                                        }}
                                        title="تحديث المخزون"
                                    >
                                        <Clock size={16} />
                                    </Button>
                                    <Button variant="outline" onClick={() => setPickerOpen(true)}>
                                        <Plus size={18} className="ml-2" />
                                        مادة أخرى
                                    </Button>
                                </div>
                                <span className="text-[10px] text-gray-400 mt-1">
                                    متاح: {availableMaterials?.length || 0} | مختار: {materials?.length || 0}
                                    {availableMaterials?.length > 0 && availableMaterialsList?.length === 0 && " (الكل مختار)"}
                                </span>
                            </div>
                        )}
                        <Button
                            onClick={handleSave}
                            className="bg-primary hover:bg-primary/90 text-white px-8"
                            disabled={isLoading}
                        >
                            {isLoading ? 'جاري الحفظ...' : (
                                <div className="flex items-center gap-2">
                                    <CheckCircle size={18} />
                                    تأكيد الصرف
                                </div>
                            )}
                        </Button>
                    </div>
                </div>
            </div>
            
            {/* Visual Diagnostic for Debugging */}
            {process.env.NODE_ENV === 'development' && (
                <div style={{ display: 'none' }}>
                    {console.log('[EMC_DIAGNOSTIC]', { 
                        available: availableMaterials?.length,
                        filtered: availableMaterialsList?.length,
                        selected: materials?.length
                    })}
                </div>
            )}
        </Modal>
    );
}


import { useState, useEffect, useMemo, useRef } from 'react';
import logger from '@/utils/logger';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Modal, Button, Badge } from '@/shared/ui';
import { SmartMaterialRow } from './SmartMaterialRow';
import { api } from '@/api';
import { toast } from 'react-hot-toast';
import { Plus, CheckCircle, AlertTriangle, Clock } from 'lucide-react';
import { cn } from '@/utils/cn';
export function EnhancedMaterialConsumption({
    procedure,
    availableMaterials = [],
    initialMaterials = [], // [{ material_id, quantity, unit }]
    mode = 'smart', // 'smart' | 'manual'
    patientId = null,
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
        logger.log('[EMC_DEBUG] Picker effect triggered:', { isOpen, mode, materialsCount: availableMaterials?.length });
        if (isOpen && mode === 'manual') {
            setPickerOpen(true);
        } else {
            setPickerOpen(false);
        }
    }, [isOpen, mode, availableMaterials]); // Added availableMaterials to dependencies
    // CRITICAL FIX: Only sync from props when modal OPENS or when initialMaterials arrive
    useEffect(() => {
        const wasOpen = prevIsOpenRef.current;
        prevIsOpenRef.current = isOpen;

        // Reset if modal closes
        if (!isOpen) {
            if (wasOpen) {
                hasInitializedRef.current = false;
                setMaterials([]);
            }
            return;
        }

        // Initialize if:
        // 1. Modal just opened
        // 2. OR we haven't initialized yet and initialMaterials is now available
        // 3. OR the current materials list is empty but initialMaterials has data (reactive pop-in)
        const shouldInitialize = !hasInitializedRef.current || (materials.length === 0 && initialMaterials?.length > 0);
        
        if (shouldInitialize && Array.isArray(initialMaterials) && initialMaterials.length > 0) {
            logger.log('[EMC_DEBUG] Initializing/Syncing materials from:', initialMaterials.length, 'items');
            const mapped = initialMaterials.map(m => {
                const targetId = parseInt(m.material_id || m.id || m.materialId);
                const matInfo = availableMaterials.find(am => (am.material_id || am.id) === targetId) || {};
                
                return {
                    id: Math.random(), // Use random for internal keying
                    material_id: targetId,
                    material_name: m.name || m.material_name || matInfo.material_name || matInfo.name || 'Unknown',
                    quantity: Number.isFinite(parseFloat(m.quantity)) ? parseFloat(m.quantity) : 1,
                    unit: m.unit || matInfo.unit || matInfo.base_unit || 'وحدة',
                    is_manual: m.is_manual || m.is_manual_override || false
                };
            });
            setMaterials(mapped);
            hasInitializedRef.current = true;
            logger.log('[EMC_DEBUG] Materials State Updated:', mapped);
        }
    }, [isOpen, initialMaterials, availableMaterials, materials.length]);

    // Pre-flight Stock Check
    const { data: rawStockCheckData } = useQuery({
        queryKey: ['stock-check', materials],
        queryFn: async () => {
            if (!materials || materials.length === 0) return [];
            const payload = {
                materials: materials.map(m => ({ 
                    material_id: m.material_id, 
                    quantity: m.quantity 
                })),
                patient_id: patientId
            };
            const res = await api.post('/api/v1/inventory/smart/check-availability', payload);
            const rawData = res.data?.data;
            return Array.isArray(rawData) ? rawData : [];
        },
        enabled: materials.length > 0
    });
    const stockCheckData = useMemo(
        () => (Array.isArray(rawStockCheckData) ? rawStockCheckData : []),
        [rawStockCheckData]
    );

    const addManualMaterial = (materialId) => {
        logger.log('[EMC_ACTION] addManualMaterial called for ID:', materialId);
        const mat = availableMaterials.find(m => (m.material_id || m.id) === parseInt(materialId));
        
        if (!mat) {
            logger.error('[EMC_ERROR] Material not found in available list:', materialId);
            return;
        }

        // Prevent duplicates using normalized IDs
        const normalizedTargetId = parseInt(mat.material_id || mat.id);
        if (materials.some(m => parseInt(m.material_id || m.id) === normalizedTargetId)) {
            logger.warn('[EMC_WARN] Material already added:', normalizedTargetId);
            toast.error("هذه المادة مضافة بالفعل");
            setPickerOpen(false);
            return;
        }

        const isDivisible = mat.material_type === 'DIVISIBLE' || mat.type === 'DIVISIBLE' || ['ml', 'g', 'cm'].includes(mat.base_unit?.toLowerCase());
        const initialQuantity = isDivisible ? 0.1 : 1;

        const newEntry = {
            id: Date.now(),
            material_id: normalizedTargetId,
            material_name: mat.material_name || mat.name,
            quantity: initialQuantity,
            unit: mat.unit || mat.base_unit,
            is_manual: true
        };

        logger.log('[EMC_ACTION] Adding new entry to state:', newEntry);
        setMaterials(prev => [...prev, newEntry]);
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
            logger.error("Save failed", error);
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
            {/* DEBUG BANNER removed - production-ready */}
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
                    <div className="space-y-3 max-h-[60vh] overflow-y-auto pe-1">
                        {materials.map((mat, idx) => (
                            <SmartMaterialRow
                                key={mat.material_id || mat.id || idx}
                                material={mat}
                                patientId={patientId}
                                stockInfo={stockCheckData?.find(s => s.material_id === (mat.material_id || mat.id))}
                                onChange={(updated) => updateMaterial(idx, updated)}
                                onRemove={() => removeMaterial(idx)}
                                onRefresh={() => queryClient.invalidateQueries(['stock-check', materials])}
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
                                            const alertStatus = m.alert_status || (qtyDisplay <= 0 ? 'CRITICAL' : 'OK');
                                            const isCritical = alertStatus === 'CRITICAL' || qtyDisplay <= 0;
                                            const isLow = alertStatus === 'LOW';
                                            
                                            if (!id) return null;

                                            return (
                                                <button
                                                    key={`${id}-${idx}`}
                                                    onClick={() => {
                                                        logger.log('[EMC_ACTION] Adding material:', id);
                                                        addManualMaterial(id);
                                                    }}
                                                    className={cn(
                                                        "flex justify-between items-center p-3 border rounded-lg hover:shadow-sm transition-all text-right group",
                                                        isCritical 
                                                            ? "bg-red-50/50 border-red-200 hover:border-red-400" 
                                                            : isLow 
                                                                ? "bg-amber-50/50 border-amber-200 hover:border-amber-400" 
                                                                : "bg-white border-blue-200 hover:border-primary"
                                                    )}
                                                >
                                                    <div className="flex flex-col items-end">
                                                        <span className={cn(
                                                            "font-bold transition-colors",
                                                            isCritical ? "text-red-700 group-hover:text-red-800" : "text-slate-800 group-hover:text-primary"
                                                        )}>{name}</span>
                                                        <span className="text-[10px] text-slate-500">{m.brand || ''}</span>
                                                    </div>
                                                    <div className="flex flex-col items-start text-left gap-1">
                                                        <Badge variant="outline" className={cn(
                                                            "text-[10px]",
                                                            isCritical ? "bg-red-100 text-red-700 border-red-300" :
                                                            isLow ? "bg-amber-100 text-amber-700 border-amber-300" :
                                                            "bg-slate-50"
                                                        )}>
                                                            {qtyDisplay} {unitDisplay} متوفر
                                                        </Badge>
                                                        {isCritical && (
                                                            <span className="text-[9px] text-red-500 font-bold flex items-center gap-0.5">
                                                                <AlertTriangle size={10} /> نفد المخزون
                                                            </span>
                                                        )}
                                                        {isLow && !isCritical && (
                                                            <span className="text-[9px] text-amber-600 font-bold flex items-center gap-0.5">
                                                                <AlertTriangle size={10} /> مخزون منخفض
                                                            </span>
                                                        )}
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
                                            logger.log('[EMC_DEBUG_MANUAL] Current State:', { availableMaterials, materials, initialMaterials });
                                            queryClient.invalidateQueries(['stock-summary']);
                                        }}
                                        title="تحديث المخزون"
                                    >
                                        <Clock size={16} />
                                    </Button>
                                    <Button variant="outline" onClick={() => setPickerOpen(true)}>
                                        <Plus size={18} className="ms-2" />
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
            {import.meta.env.DEV && (
                <div style={{ display: 'none' }}>
                    {logger.log('[EMC_DIAGNOSTIC]', { 
                        available: availableMaterials?.length,
                        filtered: availableMaterialsList?.length,
                        selected: materials?.length
                    })}
                </div>
            )}
        </Modal>
    );
}

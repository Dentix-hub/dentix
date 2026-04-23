import { useState, useEffect, useMemo, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Modal, Button } from '@/shared/ui';
import { SmartMaterialRow } from './SmartMaterialRow';
import api from '@/api';
import { toast } from 'react-hot-toast';
import { Plus, CheckCircle, AlertTriangle } from 'lucide-react';
import { cn } from '@/utils/cn';
export function EnhancedMaterialConsumption({
    procedure,
    patientAge,
    availableMaterials = [],
    initialMaterials = [], // [{ material_id, quantity, unit }]
    mode = 'smart', // 'smart' | 'manual'
    onSave,
    onClose,
    isOpen
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
        if (isOpen && mode === 'manual') {
            setPickerOpen(true);
        } else {
            setPickerOpen(false);
        }
    }, [isOpen, mode]);
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
        if (isOpen && !hasInitializedRef.current && Array.isArray(availableMaterials) && Array.isArray(initialMaterials)) {
            const mapped = initialMaterials.map(m => {
                const matInfo = availableMaterials.find(am => am.id === parseInt(m.material_id)) || {};
                return {
                    materialId: parseInt(m.material_id),
                    materialName: matInfo.name || 'Unknown',
                    quantity: parseFloat(m.quantity),
                    unit: m.unit || matInfo.base_unit,
                    suggested: false
                };
            });
            setMaterials(mapped);
            hasInitializedRef.current = true; // Mark as initialized - NO MORE OVERWRITES
            console.log('[EnhancedMaterialConsumption] Initialized materials:', mapped);
        }
    }, [isOpen, availableMaterials, initialMaterials]);
    // Pre-flight Stock Check
    const { data: rawStockCheckData } = useQuery({
        queryKey: ['stock-check', materials],
        queryFn: async () => {
            if (materials.length === 0) return [];
            const payload = materials.map(m => ({ material_id: m.materialId, quantity: m.quantity }));
            const res = await api.post('/api/v1/inventory/smart/check-availability', payload);
            const rawData = res.data?.data;
            return Array.isArray(rawData) ? rawData : [];
        },
        enabled: materials.length > 0
    });
    const stockCheckData = Array.isArray(rawStockCheckData) ? rawStockCheckData : [];
    const addManualMaterial = (materialId) => {
        const mat = availableMaterials.find(m => m.id === parseInt(materialId));
        if (!mat) return;
        // Prevent duplicates
        if (materials.some(m => m.materialId === mat.id)) {
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
                materialId: mat.id,
                materialName: mat.name,
                quantity: initialQuantity,
                unit: mat.base_unit,
                suggested: false
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
    const handleSave = async () => {
        // 1. Check for materials needing Open Confirmation
        // We need to know which ones are "New/Closed" but `stockCheckData` only returns qty.
        // The backend consumes_stock throws error `CONFIRM_OPEN_REQUIRED`. 
        // So we can try to save, catch that error, show confirm dialog.
        try {
            onSave(materials);
            onClose();
        } catch (error) {
            console.error("Save failed", error);
        }
    };
    // Actually `onSave` just passes data to parent (TreatmentModal). 
    // The parent calls the API. The parent needs to handle the confirmation workflow.
    // BUT we are in `EnhancedMaterialConsumption`.
    // Let's modify the parent logic OR we can do a "Pre-Check" here if we want.
    // The user requirement says "System must ask for approval".
    // Best place: The backend throws specific error. The UI catches it and shows "Confirm Open?".
    // Then re-tries with `auto_open=true`.
    // Since `onSave` is just passing data, we should update `TreatmentModal` or whoever calls API.
    // Let's create an `SmartStockHandler` component or hook in the parent.
    // WAIT: `EnhancedMaterialConsumption` is just a picker.
    // The API call happens in `TreatmentModal.jsx` -> `createTreatment`.
    // We should look at `TreatmentModal.jsx`.
    // Placeholder to avoid breaking current file logic.
    const handleSavePlaceholder = () => {
        onSave(materials);
        onClose();
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
                                key={mat.materialId || idx}
                                material={mat}
                                stockInfo={stockCheckData?.find(s => s.material_id === mat.materialId)}
                                onChange={(updated) => updateMaterial(idx, updated)}
                                onRemove={() => removeMaterial(idx)}
                            />
                        ))}
                        {/* Inline Picker */}
                        {pickerOpen && (
                            <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-100 animate-in slide-in-from-top-2">
                                <label className="block text-sm font-bold text-blue-900 mb-2">اختر مادة من المخزون:</label>
                                <div className="flex gap-2">
                                    <select
                                        className="flex-1 p-2 rounded-lg border border-blue-200 outline-none"
                                        onChange={(e) => addManualMaterial(e.target.value)}
                                        value=""
                                    >
                                        <option value="">-- اختر مادة --</option>
                                        {Array.isArray(availableMaterials) && availableMaterials.map(m => (
                                            <option key={m.id} value={m.id}>{m.name} ({m.quantity} {m.base_unit})</option>
                                        ))}
                                    </select>
                                    <Button size="sm" variant="ghost" onClick={() => setPickerOpen(false)}>إلغاء</Button>
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
                            <Button variant="outline" onClick={() => setPickerOpen(true)}>
                                <Plus size={18} className="ml-2" />
                                مادة أخرى
                            </Button>
                        )}
                        <Button
                            onClick={handleSave}
                            disabled={hasCritical || materials.length === 0}
                            className={cn(hasCritical && "opacity-50 cursor-not-allowed")}
                            variant="primary"
                        >
                            <CheckCircle size={18} className="ml-2" />
                            تأكيد الصرف
                        </Button>
                    </div>
                </div>
            </div>
        </Modal>
    );
}


import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { getSuggestedMaterials, getCategoryMaterials } from '@/api/inventory';
import { Package, Droplets, AlertCircle, CheckCircle2, Minus, Plus, Edit3 } from 'lucide-react';
import { toast } from '@/shared/ui';

/**
 * MaterialConsumptionPanel
 * 
 * Displays suggested materials for a procedure with:
 * - DIVISIBLE: active session indicator + weight score
 * - NON_DIVISIBLE: quantity spinner
 * - Multiple brands: radio selection
 * - Manual override toggle
 */
const MaterialConsumptionPanel = ({ procedureId, doctorId, onMaterialsChange, initialMaterials = [] }) => {
    const { t } = useTranslation();
    const [selectedMaterials, setSelectedMaterials] = useState({});
    const [manualOverrides, setManualOverrides] = useState({});

    // Fetch suggested materials from resolution engine
    const { data: rawSuggestions, isLoading, error } = useQuery({
        queryKey: ['material-suggestions', procedureId, doctorId],
        queryFn: () => getSuggestedMaterials(procedureId, doctorId).then(r => r.data),
        enabled: !!procedureId,
        staleTime: 30 * 1000
    });
    const suggestions = Array.isArray(rawSuggestions) ? rawSuggestions : [];

    // Initialize selected materials from suggestions
    useEffect(() => {
        if (Array.isArray(suggestions) && suggestions.length > 0 && Object.keys(selectedMaterials).length === 0) {
            const initial = {};
            suggestions.forEach(sugg => {
                // If there's an active session, use it; otherwise use first alternative
                const materialId = sugg.material_id || (sugg.alternatives[0]?.id);
                if (materialId) {
                    initial[sugg.category_id] = {
                        category_id: sugg.category_id,
                        material_id: materialId,
                        material_name: sugg.material_name || sugg.alternatives[0]?.name,
                        weight: sugg.weight,
                        quantity: (sugg.material_type === 'NON_DIVISIBLE' || sugg.material_type === 'REUSABLE') ? 1 : null,
                        material_type: sugg.material_type,
                        base_unit: sugg.base_unit,
                        has_active_session: sugg.has_active_session,
                        session_id: sugg.session_id,
                        is_manual_override: false
                    };
                }
            });
            setSelectedMaterials(initial);
        }
    }, [suggestions]);

    // Initialize from initialMaterials when procedureId changes (new treatment modal opened)
    useEffect(() => {
        if (Array.isArray(initialMaterials) && initialMaterials.length > 0) {
            const initial = {};
            initialMaterials.forEach(mat => {
                if (mat.category_id || mat.material_id) {
                    initial[mat.category_id || mat.material_id] = {
                        category_id: mat.category_id,
                        material_id: mat.material_id || mat.id,
                        material_name: mat.material_name || mat.name,
                        weight: mat.weight || 1.0,
                        quantity: Number.isFinite(parseFloat(mat.quantity)) ? parseFloat(mat.quantity) : 1,
                        material_type: mat.material_type || 'NON_DIVISIBLE',
                        base_unit: mat.base_unit,
                        has_active_session: mat.has_active_session,
                        session_id: mat.session_id,
                        is_manual_override: !!mat.is_manual_override
                    };
                }
            });
            setSelectedMaterials(initial);
        } else if (procedureId) {
            // Reset when switching to a new treatment with no materials
            setSelectedMaterials({});
        }
    }, [procedureId]);

    const handleMaterialSelect = (categoryId, material) => {
        setSelectedMaterials(prev => {
            const updated = {
                ...prev,
                [categoryId]: {
                    ...prev[categoryId],
                    material_id: material.id,
                    material_name: material.name,
                    brand: material.brand
                }
            };
            // Explicitly notify parent
            onMaterialsChange?.(Object.values(updated).filter(m => m.material_id));
            return updated;
        });
    };

    const handleQuantityChange = (categoryId, delta) => {
        setSelectedMaterials(prev => {
            const updated = {
                ...prev,
                [categoryId]: {
                    ...prev[categoryId],
                    quantity: Math.max(0, (prev[categoryId]?.quantity || 0) + delta)
                }
            };
            onMaterialsChange?.(Object.values(updated).filter(m => m.material_id));
            return updated;
        });
    };

    const handleWeightChange = (categoryId, newWeight) => {
        setSelectedMaterials(prev => {
            const updated = {
                ...prev,
                [categoryId]: {
                    ...prev[categoryId],
                    weight: parseFloat(newWeight) || 1.0,
                    is_manual_override: true
                }
            };
            onMaterialsChange?.(Object.values(updated).filter(m => m.material_id));
            return updated;
        });
        setManualOverrides(prev => ({ ...prev, [categoryId]: true }));
    };

    const toggleManualOverride = (categoryId) => {
        setManualOverrides(prev => ({ ...prev, [categoryId]: !prev[categoryId] }));
    };

    if (isLoading) {
        return (
            <div className="p-4 text-center text-text-secondary">
                {t('inventory.materials.loading_suggestions')}
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 text-center text-red-500">
                {t('inventory.materials.error_suggestions')}
            </div>
        );
    }

    if (!Array.isArray(suggestions) || suggestions.length === 0) {
        return (
            <div className="p-4 text-center text-text-secondary bg-surface rounded-lg">
                <AlertCircle className="mx-auto mb-2" size={24} />
                {t('inventory.materials.no_suggestions')}
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <h3 className="font-bold text-text-primary flex items-center gap-2">
                <Package size={18} />
                {t('inventory.materials.suggested_materials')}
            </h3>

            {suggestions.map((sugg) => {
                const selected = selectedMaterials[sugg.category_id];
                const isManual = manualOverrides[sugg.category_id];
                const isDivisible = sugg.material_type === 'DIVISIBLE';
                const isReusable = sugg.material_type === 'REUSABLE';

                return (
                    <div
                        key={sugg.category_id}
                        className={`p-2.5 rounded-xl border transition-all ${selected ? 'border-primary bg-primary/5 shadow-sm' : 'border-slate-200 bg-white'}`}
                    >
                        <div className="flex flex-col gap-2">
                            {/* Top Row: Category Name & Quantity */}
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    {(isDivisible || isReusable) ? <Droplets size={16} className={selected ? 'text-primary' : 'text-slate-400'} /> : <Package size={16} className={selected ? 'text-primary' : 'text-slate-400'} />}
                                    <span className="font-bold text-slate-700 text-sm">{sugg.category_name_ar}</span>
                                </div>
                                
                                <div className="flex items-center gap-2">
                                    {/* Weight / Quantity Controls */}
                                    {isDivisible ? (
                                        <div className="flex items-center gap-1">
                                            {isManual ? (
                                                <input
                                                    type="number"
                                                    step="0.1"
                                                    value={selected?.weight || sugg.weight}
                                                    onChange={(e) => handleWeightChange(sugg.category_id, e.target.value)}
                                                    className="w-16 px-1.5 py-0.5 text-sm border rounded"
                                                />
                                            ) : (
                                                <span className="text-sm font-bold bg-white px-2 py-0.5 rounded border border-slate-200 shadow-sm text-slate-700">
                                                    {selected?.weight || sugg.weight} {sugg.base_unit || 'وزن نسبي'}
                                                </span>
                                            )}
                                            <button
                                                onClick={() => toggleManualOverride(sugg.category_id)}
                                                className={`p-1 rounded transition-colors ${isManual ? 'bg-primary text-white' : 'bg-slate-50 hover:bg-slate-100 text-slate-500 border border-slate-200 shadow-sm'}`}
                                                title={t('inventory.materials.manual_override')}
                                            >
                                                <Edit3 size={14} />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-1 bg-white rounded border border-slate-200 p-0.5 shadow-sm">
                                            <button
                                                onClick={() => handleQuantityChange(sugg.category_id, -1)}
                                                className="p-1 hover:bg-slate-50 rounded text-slate-600 transition-colors"
                                            >
                                                <Minus size={14} />
                                            </button>
                                            <span className="w-6 text-center text-sm font-bold text-slate-700">
                                                {selected?.quantity || 0}
                                            </span>
                                            <button
                                                onClick={() => handleQuantityChange(sugg.category_id, 1)}
                                                className="p-1 hover:bg-slate-50 rounded text-slate-600 transition-colors"
                                            >
                                                <Plus size={14} />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Bottom Row: Material Select & Badges */}
                            <div className="flex flex-wrap items-center gap-2">
                                <div className="flex-1 min-w-[180px]">
                                    {(sugg.material_id || sugg.alternatives?.length > 0) ? (
                                        <select 
                                            className={`w-full text-xs p-1.5 rounded border focus:bg-white focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all ${selected ? 'bg-white border-primary/20 text-slate-700' : 'bg-slate-50 border-slate-200 text-slate-600'}`}
                                            value={selected?.material_id || sugg.material_id || ''}
                                            onChange={(e) => {
                                                const selectedId = e.target.value;
                                                if (!selectedId) return;
                                                let mat = sugg.material_id?.toString() === selectedId 
                                                    ? {id: sugg.material_id, name: sugg.material_name, brand: sugg.brand} 
                                                    : sugg.alternatives?.find(a => a.id?.toString() === selectedId);
                                                if (mat) handleMaterialSelect(sugg.category_id, mat);
                                            }}
                                        >
                                            <option value="" disabled>{t('inventory.materials.select_material')}</option>
                                            {sugg.material_id && (
                                                <option value={sugg.material_id}>
                                                    {sugg.material_name} {sugg.brand ? `(${sugg.brand})` : ''}
                                                </option>
                                            )}
                                            {sugg.alternatives?.map(alt => (
                                                <option key={alt.id} value={alt.id}>
                                                    {alt.name} {alt.brand ? `(${alt.brand})` : ''}
                                                </option>
                                            ))}
                                        </select>
                                    ) : (
                                        <div className="text-[10px] text-amber-600 bg-amber-50 px-2 py-1.5 rounded border border-amber-100">
                                            {t('inventory.materials.no_materials_in_category')}
                                        </div>
                                    )}
                                </div>

                                <div className="flex items-center gap-1.5">
                                    {/* Session info */}
                                    {sugg.has_active_session && (
                                        <span className="text-[10px] font-bold px-1.5 py-1 bg-green-50 text-green-700 rounded flex items-center gap-1 border border-green-100 whitespace-nowrap">
                                            <CheckCircle2 size={10} />
                                            {t('inventory.materials.active_session')}
                                            {(sugg.max_uses > 1 || isReusable) && (
                                                <span className="ml-0.5 opacity-80 border-l border-green-200 pl-1">
                                                    {sugg.current_uses}/{isReusable ? '∞' : sugg.max_uses}
                                                </span>
                                            )}
                                        </span>
                                    )}
                                    
                                    {/* Confidence indicator (Only if there is a material) */}
                                    {sugg.material_id && sugg.reason && (
                                        <span className={`text-[10px] px-1.5 py-1 rounded border whitespace-nowrap ${sugg.confidence > 0.8 ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-slate-50 text-slate-500 border-slate-200'}`} title={sugg.reason}>
                                            {sugg.confidence > 0.8 ? 'مقترح' : 'بديل'}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default MaterialConsumptionPanel;

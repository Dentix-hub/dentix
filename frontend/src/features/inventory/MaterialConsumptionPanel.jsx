import { useState, useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { getSuggestedMaterials } from '@/api/inventory';
import { Package, Droplets, AlertCircle, CheckCircle2, Minus, Plus, Edit3 } from 'lucide-react';

/**
 * MaterialConsumptionPanel
 * 
 * Displays suggested materials for a procedure with:
 * - DIVISIBLE: active session indicator + weight score
 * - NON_DIVISIBLE: quantity spinner
 * - Multiple brands: radio selection
 * - Manual override toggle
 */
const EMPTY_MATERIALS = [];

const getSuggestionKey = (item) => (
    item?.is_direct_material || item?.category_id == null
        ? `mat-${item?.material_id || item?.id}`
        : `cat-${item.category_id}`
);

const MaterialConsumptionPanel = ({ procedureId, doctorId, onMaterialsChange, initialMaterials = EMPTY_MATERIALS }) => {
    const { t } = useTranslation();
    const [selectedMaterials, setSelectedMaterials] = useState({});
    const [manualOverrides, setManualOverrides] = useState({});
    const onMaterialsChangeRef = useRef(onMaterialsChange);
    const lastAutoSyncRef = useRef('');

    useEffect(() => {
        onMaterialsChangeRef.current = onMaterialsChange;
    }, [onMaterialsChange]);

    // Fetch suggested materials from resolution engine
    const { data: rawSuggestions, isLoading, error } = useQuery({
        queryKey: ['material-suggestions', procedureId, doctorId],
        queryFn: () => getSuggestedMaterials(procedureId, doctorId).then(r => r.data),
        enabled: !!procedureId,
        staleTime: 30 * 1000
    });
    const suggestions = useMemo(
        () => Array.isArray(rawSuggestions) ? rawSuggestions : [],
        [rawSuggestions]
    );

    // Initialize selected materials from suggestions and sync resolved list to parent
    useEffect(() => {
        if (Array.isArray(initialMaterials) && initialMaterials.length > 0) return;
        if (suggestions.length === 0) return;

        const sig = `${procedureId || ''}:${suggestions
            .map((s) => `${getSuggestionKey(s)}:${s.material_id || ''}:${s.weight || ''}`)
            .join(',')}`;
        if (lastAutoSyncRef.current === sig) return;

        const initial = {};
        suggestions.forEach(sugg => {
            const materialId = sugg.material_id || (sugg.alternatives?.[0]?.id);
            if (materialId) {
                const key = getSuggestionKey(sugg);
                const isCountBased = sugg.material_type === 'NON_DIVISIBLE' || sugg.material_type === 'REUSABLE';
                initial[key] = {
                    category_id: sugg.category_id ?? null,
                    material_id: materialId,
                    material_name: sugg.material_name || sugg.alternatives?.[0]?.name,
                    weight: sugg.weight,
                    quantity: isCountBased ? Math.max(1, Math.round(Number(sugg.weight) || 1)) : null,
                    material_type: sugg.material_type,
                    base_unit: sugg.base_unit,
                    has_active_session: sugg.has_active_session,
                    session_id: sugg.session_id,
                    is_manual_override: false,
                    is_direct_material: Boolean(sugg.is_direct_material),
                    source: 'panel',
                };
            }
        });

        const resolvedList = Object.values(initial).filter(m => m.material_id);
        if (resolvedList.length > 0) {
            lastAutoSyncRef.current = sig;
            setSelectedMaterials(current => (Object.keys(current).length === 0 ? initial : current));
            onMaterialsChangeRef.current?.(resolvedList);
        }
    }, [suggestions, procedureId, initialMaterials]);

    // Initialize from initialMaterials when procedureId changes or parent restores selection
    useEffect(() => {
        if (Array.isArray(initialMaterials) && initialMaterials.length > 0) {
            const initial = {};
            initialMaterials.forEach(mat => {
                if (mat.category_id != null || mat.material_id || mat.id) {
                    const key = getSuggestionKey(mat);
                    initial[key] = {
                        category_id: mat.category_id ?? null,
                        material_id: mat.material_id || mat.id,
                        material_name: mat.material_name || mat.name,
                        weight: mat.weight ?? mat.weight_score ?? 1.0,
                        quantity: mat.material_type === 'DIVISIBLE'
                            ? null
                            : (Number.isFinite(parseFloat(mat.quantity)) ? parseFloat(mat.quantity) : 1),
                        material_type: mat.material_type || 'NON_DIVISIBLE',
                        base_unit: mat.base_unit || mat.unit,
                        has_active_session: mat.has_active_session,
                        session_id: mat.session_id,
                        is_manual_override: !!mat.is_manual_override,
                        is_direct_material: Boolean(mat.is_direct_material),
                        source: 'panel',
                    };
                }
            });
            setSelectedMaterials(initial);
        } else if (procedureId) {
            lastAutoSyncRef.current = '';
            setSelectedMaterials({});
        }
    }, [initialMaterials, procedureId]);

    const handleMaterialSelect = (categoryId, material) => {
        const updated = {
            ...selectedMaterials,
            [categoryId]: {
                ...selectedMaterials[categoryId],
                material_id: material.id,
                material_name: material.name,
                brand: material.brand
            }
        };
        setSelectedMaterials(updated);
        onMaterialsChangeRef.current?.(Object.values(updated).filter(m => m.material_id));
    };

    const handleQuantityChange = (categoryId, delta) => {
        const updated = {
            ...selectedMaterials,
            [categoryId]: {
                ...selectedMaterials[categoryId],
                quantity: Math.max(0, (selectedMaterials[categoryId]?.quantity || 0) + delta)
            }
        };
        setSelectedMaterials(updated);
        onMaterialsChangeRef.current?.(Object.values(updated).filter(m => m.material_id));
    };

    const handleWeightChange = (categoryId, newWeight) => {
        const updated = {
            ...selectedMaterials,
            [categoryId]: {
                ...selectedMaterials[categoryId],
                weight: parseFloat(newWeight) || 1.0,
                is_manual_override: true
            }
        };
        setSelectedMaterials(updated);
        setManualOverrides(prev => ({ ...prev, [categoryId]: true }));
        onMaterialsChangeRef.current?.(Object.values(updated).filter(m => m.material_id));
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
                const suggKey = getSuggestionKey(sugg);
                const selected = selectedMaterials[suggKey];
                const isManual = manualOverrides[suggKey];
                const isDivisible = sugg.material_type === 'DIVISIBLE';
                const isReusable = sugg.material_type === 'REUSABLE';

                return (
                    <div
                        key={suggKey}
                        className={`p-2.5 rounded-xl border transition-all ${selected ? 'border-primary bg-primary/5 shadow-sm dark:bg-primary/10' : 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800/80'}`}
                    >
                        <div className="flex flex-col gap-2">
                            {/* Top Row: Category Name & Quantity */}
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    {(isDivisible || isReusable) ? <Droplets size={16} className={selected ? 'text-primary' : 'text-slate-400'} /> : <Package size={16} className={selected ? 'text-primary' : 'text-slate-400'} />}
                                    <span className="font-bold text-slate-700 dark:text-slate-200 text-sm">{sugg.category_name_ar}</span>
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
                                                    onChange={(e) => handleWeightChange(suggKey, e.target.value)}
                                                    className="w-16 px-1.5 py-0.5 text-sm border rounded bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-700"
                                                />
                                            ) : (
                                                <span className="text-sm font-bold bg-white px-2 py-0.5 rounded border border-slate-200 shadow-sm text-slate-700 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200">
                                                    {selected?.weight || sugg.weight} {sugg.base_unit || 'وزن نسبي'}
                                                </span>
                                            )}
                                            <button
                                                type="button"
                                                onClick={() => toggleManualOverride(suggKey)}
                                                className={`p-1 rounded transition-colors ${isManual ? 'bg-primary text-white' : 'bg-slate-50 hover:bg-slate-100 text-slate-500 border border-slate-200 shadow-sm dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 dark:border-slate-700'}`}
                                                title={t('inventory.materials.manual_override')}
                                            >
                                                <Edit3 size={14} />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-1 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 p-0.5 shadow-sm">
                                            <button
                                                type="button"
                                                onClick={() => handleQuantityChange(suggKey, -1)}
                                                className="p-1 hover:bg-slate-50 dark:hover:bg-slate-700 rounded text-slate-600 dark:text-slate-300 transition-colors"
                                            >
                                                <Minus size={14} />
                                            </button>
                                            <span className="w-6 text-center text-sm font-bold text-slate-700 dark:text-slate-200">
                                                {selected?.quantity || 0}
                                            </span>
                                            <button
                                                type="button"
                                                onClick={() => handleQuantityChange(suggKey, 1)}
                                                className="p-1 hover:bg-slate-50 dark:hover:bg-slate-700 rounded text-slate-600 dark:text-slate-300 transition-colors"
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
                                            className={`w-full text-xs p-1.5 rounded border focus:bg-white focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all dark:bg-slate-800 dark:text-slate-100 dark:border-slate-700 ${selected ? 'bg-white border-primary/20 text-slate-700' : 'bg-slate-50 border-slate-200 text-slate-600'}`}
                                            value={selected?.material_id || sugg.material_id || ''}
                                            onChange={(e) => {
                                                const selectedId = e.target.value;
                                                if (!selectedId) return;
                                                let mat = sugg.material_id?.toString() === selectedId 
                                                    ? {id: sugg.material_id, name: sugg.material_name, brand: sugg.brand} 
                                                    : sugg.alternatives?.find(a => a.id?.toString() === selectedId);
                                                if (mat) handleMaterialSelect(suggKey, mat);
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
                                        <div className="text-[10px] text-amber-600 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 px-2 py-1.5 rounded border border-amber-100 dark:border-amber-800">
                                            {t('inventory.materials.no_materials_in_category')}
                                        </div>
                                    )}
                                </div>

                                <div className="flex items-center gap-1.5">
                                    {/* Session info */}
                                    {sugg.has_active_session && (
                                        <span className="text-[10px] font-bold px-1.5 py-1 bg-green-50 dark:bg-green-950/50 text-green-700 dark:text-green-300 rounded flex items-center gap-1 border border-green-100 dark:border-green-800 whitespace-nowrap">
                                            <CheckCircle2 size={10} />
                                            {t('inventory.materials.active_session')}
                                            {(sugg.max_uses > 1 || isReusable) && (
                                                <span className="ms-0.5 opacity-80 border-s border-green-200 dark:border-green-700 ps-1">
                                                    {sugg.current_uses}/{isReusable ? '∞' : sugg.max_uses}
                                                </span>
                                            )}
                                        </span>
                                    )}
                                    
                                    {/* Confidence indicator (Only if there is a material) */}
                                    {sugg.material_id && sugg.reason && (
                                        <span className={`text-[10px] px-1.5 py-1 rounded border whitespace-nowrap ${sugg.confidence > 0.8 ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border-emerald-100 dark:border-emerald-800' : 'bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-300 border-slate-200 dark:border-slate-700'}`} title={sugg.reason}>
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

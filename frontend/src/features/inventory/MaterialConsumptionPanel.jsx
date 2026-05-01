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
                        quantity: sugg.material_type === 'NON_DIVISIBLE' ? 1 : null,
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

    // Notify parent of changes
    useEffect(() => {
        const materialsList = Object.values(selectedMaterials).filter(m => m.material_id);
        onMaterialsChange?.(materialsList);
    }, [selectedMaterials, onMaterialsChange]);

    const handleMaterialSelect = (categoryId, material) => {
        setSelectedMaterials(prev => ({
            ...prev,
            [categoryId]: {
                ...prev[categoryId],
                material_id: material.id,
                material_name: material.name,
                brand: material.brand
            }
        }));
    };

    const handleQuantityChange = (categoryId, delta) => {
        setSelectedMaterials(prev => ({
            ...prev,
            [categoryId]: {
                ...prev[categoryId],
                quantity: Math.max(0, (prev[categoryId]?.quantity || 0) + delta)
            }
        }));
    };

    const handleWeightChange = (categoryId, newWeight) => {
        setSelectedMaterials(prev => ({
            ...prev,
            [categoryId]: {
                ...prev[categoryId],
                weight: parseFloat(newWeight) || 1.0,
                is_manual_override: true
            }
        }));
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

                return (
                    <div
                        key={sugg.category_id}
                        className={`p-4 rounded-lg border ${sugg.has_active_session ? 'border-green-500 bg-green-50' : 'border-border bg-surface'}`}
                    >
                        {/* Category Header */}
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                                {isDivisible ? <Droplets size={16} /> : <Package size={16} />}
                                <span className="font-medium">{sugg.category_name_ar}</span>
                                <span className="text-xs text-text-secondary">({sugg.category_name_en})</span>
                            </div>
                            {sugg.has_active_session && (
                                <span className="text-xs bg-green-500 text-white px-2 py-1 rounded-full flex items-center gap-1">
                                    <CheckCircle2 size={12} />
                                    {t('inventory.materials.active_session')}
                                </span>
                            )}
                        </div>

                        {/* Material Selection */}
                        <div className="mb-3">
                            <label className="block text-sm text-text-secondary mb-1">
                                {t('inventory.materials.select_material')}
                            </label>

                            {/* Primary option */}
                            {sugg.material_id && (
                                <label className="flex items-center gap-2 p-2 rounded bg-background mb-1 cursor-pointer hover:bg-surface-hover">
                                    <input
                                        type="radio"
                                        name={`material-${sugg.category_id}`}
                                        checked={selected?.material_id === sugg.material_id}
                                        onChange={() => handleMaterialSelect(sugg.category_id, {
                                            id: sugg.material_id,
                                            name: sugg.material_name,
                                            brand: sugg.brand
                                        })}
                                        className="text-primary"
                                    />
                                    <span className="flex-1">
                                        {sugg.material_name}
                                        {sugg.brand && <span className="text-xs text-text-secondary ml-1">({sugg.brand})</span>}
                                    </span>
                                    {sugg.has_active_session && (
                                        <span className="text-xs text-green-600">{t('inventory.materials.session_linked')}</span>
                                    )}
                                </label>
                            )}

                            {/* Alternatives */}
                            {sugg.alternatives?.map(alt => (
                                <label
                                    key={alt.id}
                                    className="flex items-center gap-2 p-2 rounded bg-background mb-1 cursor-pointer hover:bg-surface-hover"
                                >
                                    <input
                                        type="radio"
                                        name={`material-${sugg.category_id}`}
                                        checked={selected?.material_id === alt.id}
                                        onChange={() => handleMaterialSelect(sugg.category_id, alt)}
                                        className="text-primary"
                                    />
                                    <span className="flex-1">
                                        {alt.name}
                                        {alt.brand && <span className="text-xs text-text-secondary ml-1">({alt.brand})</span>}
                                    </span>
                                </label>
                            ))}

                            {/* No materials available */}
                            {!sugg.material_id && sugg.alternatives?.length === 0 && (
                                <div className="p-2 text-sm text-amber-600 bg-amber-50 rounded">
                                    {t('inventory.materials.no_materials_in_category')}
                                </div>
                            )}
                        </div>

                        {/* Weight / Quantity Controls */}
                        <div className="flex items-center justify-between">
                            {isDivisible ? (
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-text-secondary">
                                        {t('inventory.materials.weight_score')}:
                                    </span>
                                    {isManual ? (
                                        <input
                                            type="number"
                                            step="0.1"
                                            value={selected?.weight || sugg.weight}
                                            onChange={(e) => handleWeightChange(sugg.category_id, e.target.value)}
                                            className="w-20 px-2 py-1 text-sm border rounded"
                                        />
                                    ) : (
                                        <span className="font-medium">{selected?.weight || sugg.weight}</span>
                                    )}
                                    <button
                                        onClick={() => toggleManualOverride(sugg.category_id)}
                                        className={`p-1 rounded ${isManual ? 'bg-primary text-white' : 'bg-surface-hover'}`}
                                        title={t('inventory.materials.manual_override')}
                                    >
                                        <Edit3 size={14} />
                                    </button>
                                </div>
                            ) : (
                                <div className="flex items-center gap-3">
                                    <span className="text-sm text-text-secondary">
                                        {t('inventory.materials.quantity')}:
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => handleQuantityChange(sugg.category_id, -1)}
                                            className="p-1 rounded bg-surface-hover hover:bg-border"
                                        >
                                            <Minus size={16} />
                                        </button>
                                        <span className="w-8 text-center font-medium">
                                            {selected?.quantity || 0}
                                        </span>
                                        <button
                                            onClick={() => handleQuantityChange(sugg.category_id, 1)}
                                            className="p-1 rounded bg-surface-hover hover:bg-border"
                                        >
                                            <Plus size={16} />
                                        </button>
                                    </div>
                                    <span className="text-xs text-text-secondary">{sugg.base_unit}</span>
                                </div>
                            )}

                            {/* Confidence indicator */}
                            <span className={`text-xs px-2 py-1 rounded ${sugg.confidence > 0.8 ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                                {sugg.reason}
                            </span>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default MaterialConsumptionPanel;

import { useState, useEffect } from 'react';
import { X, Save, AlertCircle } from 'lucide-react';
import { createMaterial, updateMaterial, getCategories, createCategory } from '@/api/inventory';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { showToast } from '@/shared/ui/Toast';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react';

const AddMaterialModal = ({ isOpen, onClose, initialData = null }) => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [showNewCategoryForm, setShowNewCategoryForm] = useState(false);
    const [newCategoryData, setNewCategoryData] = useState({ name_ar: '', name_en: '' });

    const [formData, setFormData] = useState({
        name: '',
        type: 'NON_DIVISIBLE', // DIVISIBLE, NON_DIVISIBLE
        base_unit: 'Tablet',
        alert_threshold: 10,
        packaging_ratio: 1.0,
        category_id: null,
        brand: ''
    });

    // Fetch categories
    const { data: categories = [] } = useQuery({
        queryKey: ['material-categories'],
        queryFn: async () => {
            const res = await getCategories();
            return Array.isArray(res.data) ? res.data : [];
        },
        enabled: isOpen,
        staleTime: 5 * 60 * 1000
    });

    const categoryMutation = useMutation({
        mutationFn: createCategory,
        onSuccess: (res) => {
            queryClient.invalidateQueries(['material-categories']);
            setShowNewCategoryForm(false);
            setNewCategoryData({ name_ar: '', name_en: '' });
            if (res.data?.id) {
                handleCategoryChange(res.data.id);
            }
            showToast('success', t('inventory.categories.success_add') || 'Category added');
        }
    });

    // Auto-fill type and base_unit when category changes
    const handleCategoryChange = (categoryId) => {
        const category = categories.find(c => c.id === parseInt(categoryId));
        if (category) {
            setFormData(prev => ({
                ...prev,
                category_id: parseInt(categoryId),
                name: category.name_ar, // Auto-fill name from category
                type: category.default_type,
                base_unit: category.default_unit
            }));
        } else {
            setFormData(prev => ({ ...prev, category_id: null, name: '' }));
        }
    };

    useEffect(() => {
        if (isOpen && initialData) {
            setFormData({
                name: initialData.material_name || initialData.name,
                type: initialData.material_type || initialData.type || 'NON_DIVISIBLE',
                base_unit: initialData.unit || initialData.base_unit || 'Tablet',
                alert_threshold: initialData.alert_status === 'LOW' ? 10 : (initialData.alert_threshold || 5),
                packaging_ratio: initialData.packaging_ratio || 1.0,
                category_id: initialData.category_id || null,
                brand: initialData.brand || ''
            });
        } else if (isOpen) {
            setFormData({
                name: '',
                type: 'NON_DIVISIBLE',
                base_unit: 'Tablet',
                alert_threshold: 10,
                packaging_ratio: 1.0,
                category_id: null,
                brand: ''
            });
            setShowNewCategoryForm(false);
        }
    }, [isOpen, initialData]);

    const mutation = useMutation({
        mutationFn: (data) => initialData ? updateMaterial(initialData.material_id, data) : createMaterial(data),
        onSuccess: () => {
            queryClient.invalidateQueries(['inventory-stock']);
            showToast('success', initialData ? t('inventory.materials.success_edit') : t('inventory.materials.success_add'));
            onClose();
        },
        onError: (error) => {
            showToast('error', (initialData ? t('inventory.materials.fail_edit') : t('inventory.materials.fail_add')) + (error.response?.data?.detail || error.message));
        }
    });

    if (!isOpen) return null;

    const handleSubmit = (e) => {
        e.preventDefault();
        mutation.mutate(formData);
    };

    const handleCreateCategory = (e) => {
        e.preventDefault();
        if (!newCategoryData.name_ar || !newCategoryData.name_en) return;
        categoryMutation.mutate(newCategoryData);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-surface w-full max-w-md rounded-2xl shadow-2xl border border-border overflow-hidden animate-in fade-in zoom-in duration-200">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-border bg-background">
                    <h2 className="text-lg font-bold">{initialData ? t('inventory.materials.modal_edit') : t('inventory.materials.modal_add')}</h2>
                    <button onClick={onClose} className="p-2 hover:bg-surface-hover rounded-full transition-colors">
                        <X size={20} />
                    </button>
                </div>
                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {/* Category */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <label className="block text-sm font-medium text-text-secondary">{t('inventory.materials.category_label')}</label>
                            <button
                                type="button"
                                onClick={() => setShowNewCategoryForm(!showNewCategoryForm)}
                                className="text-xs text-primary flex items-center gap-1 hover:underline"
                            >
                                <Plus size={14} />
                                {showNewCategoryForm ? t('common.cancel') : t('inventory.actions.add_category')}
                            </button>
                        </div>

                        {showNewCategoryForm ? (
                            <div className="p-3 bg-primary/5 rounded-lg border border-primary/20 space-y-2 animate-in slide-in-from-top-2 duration-200">
                                <div className="grid grid-cols-2 gap-2">
                                    <input
                                        type="text"
                                        placeholder="Name (Ar)"
                                        value={newCategoryData.name_ar}
                                        onChange={e => setNewCategoryData({ ...newCategoryData, name_ar: e.target.value })}
                                        className="text-xs p-2 rounded border border-border"
                                    />
                                    <input
                                        type="text"
                                        placeholder="Name (En)"
                                        value={newCategoryData.name_en}
                                        onChange={e => setNewCategoryData({ ...newCategoryData, name_en: e.target.value })}
                                        className="text-xs p-2 rounded border border-border"
                                    />
                                </div>
                                <button
                                    type="button"
                                    onClick={handleCreateCategory}
                                    disabled={categoryMutation.isPending || !newCategoryData.name_ar || !newCategoryData.name_en}
                                    className="w-full py-1.5 bg-primary text-white text-xs rounded font-bold disabled:opacity-50"
                                >
                                    {categoryMutation.isPending ? '...' : t('common.save')}
                                </button>
                            </div>
                        ) : (
                            <select
                                value={formData.category_id || ''}
                                onChange={e => handleCategoryChange(e.target.value)}
                                className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20"
                                required
                            >
                                <option value="">{t('inventory.materials.category_placeholder')}</option>
                                {categories.map(cat => (
                                    <option key={cat.id} value={cat.id}>
                                        {cat.name_ar} / {cat.name_en}
                                    </option>
                                ))}
                            </select>
                        )}
                    </div>

                    {/* Brand */}
                    <div>
                        <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.materials.brand_label')} (Brand)</label>
                        <input
                            type="text"
                            value={formData.brand}
                            onChange={e => setFormData({ ...formData, brand: e.target.value })}
                            className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                            placeholder={t('inventory.materials.brand_placeholder')}
                        />
                    </div>

                    {/* Hidden Name field (auto-filled from category) */}
                    <input type="hidden" name="name" value={formData.name} />
                    {/* Type & Unit Grid */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.materials.type_label')}</label>
                            <select
                                value={formData.type}
                                onChange={e => setFormData({ ...formData, type: e.target.value })}
                                className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20"
                            >
                                <option value="NON_DIVISIBLE">{t('inventory.types.indivisible')} (Units)</option>
                                <option value="DIVISIBLE">{t('inventory.types.divisible')} (Liquids/Gels)</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.materials.unit_label')}</label>
                            <input
                                type="text"
                                required
                                value={formData.base_unit}
                                onChange={e => setFormData({ ...formData, base_unit: e.target.value })}
                                className="w-full px-4 py-2 rounded-lg border border-border bg-background"
                                placeholder={t('inventory.materials.unit_placeholder')}
                            />
                        </div>
                    </div>
                    {/* Numeric Fields Grid */}
                    <div className="space-y-4">
                        {/* Alert Threshold */}
                        <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.materials.alert_threshold')}</label>
                            <input
                                type="number"
                                min="0"
                                value={formData.alert_threshold}
                                onChange={e => setFormData({ ...formData, alert_threshold: parseInt(e.target.value) || 0 })}
                                className="w-full px-4 py-2 rounded-lg border border-border bg-background"
                            />
                        </div>
                        {/* Packaging Ratio */}
                        <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1">
                                {formData.type === 'DIVISIBLE' ? t('inventory.materials.packaging_ratio_divisible') : t('inventory.materials.packaging_ratio_indivisible')}
                            </label>
                            <input
                                type="number"
                                step="0.1"
                                min="0.1"
                                value={formData.packaging_ratio}
                                onChange={e => setFormData({ ...formData, packaging_ratio: parseFloat(e.target.value) })}
                                className="w-full px-4 py-2 rounded-lg border border-border bg-background"
                                placeholder={formData.type === 'DIVISIBLE' ? t('inventory.materials.ratio_placeholder_divisible') : t('inventory.materials.ratio_placeholder_indivisible')}
                            />
                        </div>
                    </div>
                    {/* Info Alert */}
                    <div className="bg-blue-50 text-blue-700 p-3 rounded-lg text-xs flex items-start gap-2">
                        <AlertCircle size={16} className="shrink-0 mt-0.5" />
                        <p>
                            <strong>{formData.type === 'DIVISIBLE' ? t('inventory.materials.info_divisible_label') : t('inventory.materials.info_indivisible_label')}</strong>
                            {formData.type === 'DIVISIBLE'
                                ? t('inventory.materials.info_divisible_desc')
                                : t('inventory.materials.info_indivisible_desc')}
                        </p>
                    </div>
                    {/* Actions */}
                    <div className="pt-4 flex justify-end gap-3 border-t border-border">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 rounded-lg font-medium text-text-secondary hover:bg-surface-hover"
                        >
                            {t('common.cancel')}
                        </button>
                        <button
                            type="submit"
                            disabled={mutation.isPending}
                            className="flex items-center gap-2 px-6 py-2 bg-primary text-white rounded-lg font-bold hover:bg-primary-600 disabled:opacity-50 transition-all shadow-lg shadow-primary/20"
                        >
                            {mutation.isPending ? t('inventory.materials.saving') : (
                                <>
                                    <Save size={18} />
                                    <span>{initialData ? t('inventory.materials.save_changes') : t('inventory.materials.save_new')}</span>
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
export default AddMaterialModal;


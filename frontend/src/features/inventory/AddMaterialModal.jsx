import { useEffect, useState } from 'react';
import { Save, AlertCircle, Plus } from 'lucide-react';
import { createMaterial, updateMaterial, getCategories, createCategory } from '@/api/inventory';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { Modal, toast } from '@/shared/ui';
import { useTranslation } from 'react-i18next';

const AddMaterialModal = ({ isOpen, onClose, initialData = null }) => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [showNewCategoryForm, setShowNewCategoryForm] = useState(false);
    const [newCategoryData, setNewCategoryData] = useState({ name_ar: '', name_en: '' });
    const [formData, setFormData] = useState({
        name: '',
        type: 'NON_DIVISIBLE',
        base_unit: 'Tablet',
        alert_threshold: 10,
        packaging_ratio: 1.0,
        category_id: null,
        brand: ''
    });

    const { data: categories = [] } = useQuery({
        queryKey: ['material-categories'],
        queryFn: async () => {
            const res = await getCategories();
            return Array.isArray(res.data) ? res.data : [];
        },
        enabled: isOpen,
        staleTime: 5 * 60 * 1000
    });

    const applyCategory = (category) => {
        setFormData(prev => ({
            ...prev,
            category_id: category.id,
            name: category.name_ar,
            type: category.default_type,
            base_unit: category.default_unit
        }));
    };

    const handleCategoryChange = (categoryId) => {
        const category = categories.find(item => item.id === parseInt(categoryId, 10));
        if (category) {
            applyCategory(category);
        } else {
            setFormData(prev => ({ ...prev, category_id: null, name: '' }));
        }
    };

    const categoryMutation = useMutation({
        mutationFn: createCategory,
        onSuccess: (res) => {
            const category = res.data;
            if (category?.id) {
                queryClient.setQueryData(['material-categories'], (current = []) => {
                    const withoutDuplicate = current.filter(item => item.id !== category.id);
                    return [...withoutDuplicate, category];
                });
                // Do not look the new category up in the stale query result. Apply
                // the response directly so the material form is immediately valid.
                applyCategory(category);
            }
            queryClient.invalidateQueries({ queryKey: ['material-categories'] });
            setShowNewCategoryForm(false);
            setNewCategoryData({ name_ar: '', name_en: '' });
            toast.success(t('inventory.categories.success_add') || 'Category added');
        },
        onError: (error) => {
            toast.error(`${t('inventory.categories.fail_add')}: ${error.response?.data?.detail || error.message}`);
        },
        retry: false,
    });

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
            queryClient.invalidateQueries({ queryKey: ['inventory-stock'] });
            toast.success(initialData ? t('inventory.materials.success_edit') : t('inventory.materials.success_add'));
            onClose();
        },
        onError: (error) => {
            toast.error((initialData ? t('inventory.materials.fail_edit') : t('inventory.materials.fail_add')) + (error.response?.data?.detail || error.message));
        },
        retry: false,
    });

    const handleSubmit = (event) => {
        event.preventDefault();
        mutation.mutate(formData);
    };

    const handleCreateCategory = (event) => {
        event.preventDefault();
        if (!newCategoryData.name_ar || !newCategoryData.name_en) return;
        categoryMutation.mutate(newCategoryData);
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={initialData ? t('inventory.materials.modal_edit') : t('inventory.materials.modal_add')}
            size="md"
            closeOnOutside={!mutation.isPending}
        >
            <form onSubmit={handleSubmit} className="min-w-0 space-y-4">
                <div className="space-y-2">
                    <div className="flex min-w-0 flex-col gap-2 min-[360px]:flex-row min-[360px]:items-center min-[360px]:justify-between">
                        <label className="text-sm font-medium text-text-secondary">{t('inventory.materials.category_label')}</label>
                        <button
                            type="button"
                            onClick={() => setShowNewCategoryForm(prev => !prev)}
                            className="inline-flex min-h-11 items-center justify-center gap-1 rounded-xl px-3 text-xs font-bold text-primary transition-colors hover:bg-primary/10"
                        >
                            <Plus size={15} aria-hidden="true" />
                            {showNewCategoryForm ? t('common.cancel') : t('inventory.actions.add_category')}
                        </button>
                    </div>

                    {showNewCategoryForm ? (
                        <div className="space-y-3 rounded-xl border border-primary/20 bg-primary/5 p-3 animate-in slide-in-from-top-2 duration-200">
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                <input
                                    type="text"
                                    placeholder="Name (Ar)"
                                    value={newCategoryData.name_ar}
                                    onChange={event => setNewCategoryData({ ...newCategoryData, name_ar: event.target.value })}
                                    className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2"
                                    dir="rtl"
                                />
                                <input
                                    type="text"
                                    placeholder="Name (En)"
                                    value={newCategoryData.name_en}
                                    onChange={event => setNewCategoryData({ ...newCategoryData, name_en: event.target.value })}
                                    className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2"
                                    dir="ltr"
                                />
                            </div>
                            <button
                                type="button"
                                onClick={handleCreateCategory}
                                disabled={categoryMutation.isPending || !newCategoryData.name_ar || !newCategoryData.name_en}
                                className="min-h-11 w-full rounded-xl bg-primary px-3 py-2 text-sm font-bold text-white disabled:opacity-50"
                            >
                                {categoryMutation.isPending ? '...' : t('common.save')}
                            </button>
                        </div>
                    ) : (
                        <select
                            value={formData.category_id || ''}
                            onChange={event => handleCategoryChange(event.target.value)}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2 outline-none focus:ring-2 focus:ring-primary/20"
                            required
                        >
                            <option value="">{t('inventory.materials.category_placeholder')}</option>
                            {categories.map(category => (
                                <option key={category.id} value={category.id}>{category.name_ar} / {category.name_en}</option>
                            ))}
                        </select>
                    )}
                </div>

                <div>
                    <label className="mb-1 block text-sm font-medium text-text-secondary">{t('inventory.materials.brand_label')} (Brand)</label>
                    <input
                        type="text"
                        value={formData.brand}
                        onChange={event => setFormData({ ...formData, brand: event.target.value })}
                        className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2 outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
                        placeholder={t('inventory.materials.brand_placeholder')}
                    />
                </div>

                <input type="hidden" name="name" value={formData.name} />

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                        <label className="mb-1 block text-sm font-medium text-text-secondary">{t('inventory.materials.type_label')}</label>
                        <select
                            value={formData.type}
                            onChange={event => setFormData({ ...formData, type: event.target.value })}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2 outline-none focus:ring-2 focus:ring-primary/20"
                        >
                            <option value="NON_DIVISIBLE">{t('inventory.types.indivisible')} (Units)</option>
                            <option value="DIVISIBLE">{t('inventory.types.divisible')} (Liquids/Gels)</option>
                            <option value="REUSABLE">{t('inventory.types.reusable')}</option>
                        </select>
                    </div>
                    <div>
                        <label className="mb-1 block text-sm font-medium text-text-secondary">{t('inventory.materials.unit_label')}</label>
                        <input
                            type="text"
                            required
                            value={formData.base_unit}
                            onChange={event => setFormData({ ...formData, base_unit: event.target.value })}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2"
                            placeholder={t('inventory.materials.unit_placeholder')}
                        />
                    </div>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                        <label className="mb-1 block text-sm font-medium text-text-secondary">{t('inventory.materials.alert_threshold')}</label>
                        <input
                            type="number"
                            min="0"
                            inputMode="decimal"
                            value={formData.alert_threshold}
                            onChange={event => setFormData({ ...formData, alert_threshold: parseInt(event.target.value, 10) || 0 })}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2"
                        />
                    </div>
                    <div>
                        <label className="mb-1 block text-sm font-medium text-text-secondary">
                            {formData.type === 'DIVISIBLE' ? t('inventory.materials.packaging_ratio_divisible') : t('inventory.materials.packaging_ratio_indivisible')}
                        </label>
                        <input
                            type="number"
                            step="0.1"
                            min="0.1"
                            inputMode="decimal"
                            value={formData.packaging_ratio}
                            onChange={event => setFormData({ ...formData, packaging_ratio: parseFloat(event.target.value) })}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2"
                            placeholder={formData.type === 'DIVISIBLE' ? t('inventory.materials.ratio_placeholder_divisible') : t('inventory.materials.ratio_placeholder_indivisible')}
                        />
                    </div>
                </div>

                <div className="flex items-start gap-2 rounded-xl bg-blue-50 p-3 text-xs text-blue-700 dark:bg-blue-950/30 dark:text-blue-200">
                    <AlertCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
                    <p className="min-w-0 break-words">
                        <strong>{formData.type === 'DIVISIBLE' ? t('inventory.materials.info_divisible_label') : t('inventory.materials.info_indivisible_label')}</strong>{' '}
                        {formData.type === 'DIVISIBLE' ? t('inventory.materials.info_divisible_desc') : t('inventory.materials.info_indivisible_desc')}
                    </p>
                </div>

                <div className="sticky bottom-0 z-10 -mx-3 grid grid-cols-1 gap-2 border-t border-border bg-surface-elevated px-3 pb-[max(0.25rem,env(safe-area-inset-bottom))] pt-3 min-[360px]:grid-cols-2 sm:-mx-4 sm:px-4">
                    <button
                        type="button"
                        onClick={onClose}
                        className="min-h-11 rounded-xl px-4 py-2 font-medium text-text-secondary transition-colors hover:bg-surface-hover"
                    >
                        {t('common.cancel')}
                    </button>
                    <button
                        type="submit"
                        disabled={mutation.isPending}
                        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 font-bold text-white shadow-low transition-colors hover:bg-primary-hover disabled:opacity-50"
                    >
                        {mutation.isPending ? t('inventory.materials.saving') : (
                            <>
                                <Save size={18} aria-hidden="true" />
                                <span>{initialData ? t('inventory.materials.save_changes') : t('inventory.materials.save_new')}</span>
                            </>
                        )}
                    </button>
                </div>
            </form>
        </Modal>
    );
};

export default AddMaterialModal;

import { useState } from 'react';
import { X, Warehouse, Save } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createWarehouse } from '@/api/inventory';
import { toast } from '@/shared/ui';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { useTranslation } from 'react-i18next';
const AddWarehouseModal = ({ isOpen, onClose, onSuccess }) => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [name, setName] = useState('');
    const [type, setType] = useState('MAIN'); // MAIN, CLINIC
    const mutation = useMutation({
        mutationFn: createWarehouse,
        onSuccess: (res) => {
            queryClient.invalidateQueries(['inventory-warehouses']);
            toast.success(t('inventory.warehouses.add_success', 'تم إضافة المخزن بنجاح'));
            if (onSuccess) onSuccess(res.data);
            handleClose();
        },
        onError: (err) => {
            toast.error(t('inventory.warehouses.add_fail', 'فشل الإضافة') + ': ' + (err.response?.data?.detail || err.message));
        }
    });
    const handleClose = () => {
        setName('');
        setType('MAIN');
        onClose();
    };
    const handleSubmit = (e) => {
        e.preventDefault();
        mutation.mutate({ name, type });
    };
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-surface w-full max-w-sm rounded-2xl shadow-xl border border-border overflow-hidden animate-in fade-in zoom-in duration-200">
                <div className="flex items-center justify-between p-4 border-b border-border bg-background">
                    <h2 className="text-lg font-bold flex items-center gap-2">
                        <Warehouse className="text-primary" size={20} />
                        {t('inventory.warehouses.add_title', 'إضافة مخزن جديد')}
                    </h2>
                    <button onClick={handleClose} className="p-2 hover:bg-surface-hover rounded-full transition-colors">
                        <X size={20} />
                    </button>
                </div>
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.warehouses.name', 'اسم المخزن')}</label>
                        <input
                            type="text"
                            required
                            autoFocus
                            value={name}
                            onChange={e => setName(e.target.value)}
                            className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20"
                            placeholder={t('inventory.warehouses.name_placeholder', 'مثال: المخزن الرئيسي')}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.warehouses.type', 'النوع')}</label>
                        <select
                            value={type}
                            onChange={e => setType(e.target.value)}
                            className="w-full px-4 py-2 rounded-lg border border-border bg-background"
                        >
                            <option value="MAIN">{t('inventory.warehouses.type_main', 'مخزن رئيسي (Main Warehouse)')}</option>
                            <option value="CLINIC">{t('inventory.warehouses.type_clinic', 'عيادة / فرعي (Clinic)')}</option>
                        </select>
                    </div>
                    <div className="pt-4 flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="px-4 py-2 rounded-lg font-medium text-text-secondary hover:bg-surface-hover"
                        >
                            {t('common.cancel', 'إلغاء')}
                        </button>
                        <button
                            type="submit"
                            disabled={mutation.isPending || !name}
                            className="flex items-center gap-2 px-6 py-2 bg-primary text-white rounded-lg font-bold hover:bg-primary-600 disabled:opacity-50 transition-colors"
                        >
                            {mutation.isPending ? <LoadingSpinner size="sm" color="white" /> : (
                                <>
                                    <Save size={18} />
                                    <span>{t('common.save', 'حفظ')}</span>
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
export default AddWarehouseModal;


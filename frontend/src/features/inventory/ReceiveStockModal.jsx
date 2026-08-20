import { useState } from 'react';
import { ArrowDownLeft, Plus } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMaterials, getWarehouses, receiveStock } from '@/api/inventory';
import { Modal, toast, DateTimePicker } from '@/shared/ui';
import AddWarehouseModal from './components/AddWarehouseModal';
import { useTranslation } from 'react-i18next';

const ReceiveStockModal = ({ isOpen, onClose }) => {
    const { t, i18n } = useTranslation();
    const queryClient = useQueryClient();
    const [isAddWarehouseOpen, setIsAddWarehouseOpen] = useState(false);
    const [formData, setFormData] = useState({
        material_id: '',
        warehouse_id: '',
        quantity: 1,
        batch_number: '',
        expiry_date: '',
        supplier: '',
        package_price: 0
    });

    const { data: materials = [] } = useQuery({
        queryKey: ['inventory-materials'],
        queryFn: async () => {
            const res = await getMaterials();
            return Array.isArray(res.data?.data) ? res.data.data : (Array.isArray(res.data) ? res.data : []);
        }
    });

    const { data: warehouses = [] } = useQuery({
        queryKey: ['inventory-warehouses'],
        queryFn: async () => {
            const res = await getWarehouses();
            return Array.isArray(res.data?.data) ? res.data.data : (Array.isArray(res.data) ? res.data : []);
        }
    });

    const mutation = useMutation({
        mutationFn: (data) => {
            let finalExpiry = data.expiry_date;
            if (typeof finalExpiry === 'string') {
                if (finalExpiry.includes('T')) finalExpiry = finalExpiry.split('T')[0];
                if (finalExpiry.length === 7) {
                    const [year, month] = finalExpiry.split('-').map(Number);
                    const lastDay = new Date(year, month, 0).getDate();
                    finalExpiry = `${year}-${String(month).padStart(2, '0')}-${lastDay}`;
                }
            }
            return receiveStock({
                material_id: parseInt(data.material_id, 10),
                warehouse_id: parseInt(data.warehouse_id, 10),
                quantity: parseFloat(data.quantity),
                batch: {
                    batch_number: `EXP-${finalExpiry.replace(/-/g, '')}-${Math.floor(1000 + Math.random() * 9000)}`,
                    expiry_date: finalExpiry,
                    supplier: data.supplier,
                    cost_per_unit: parseFloat(data.cost_per_unit)
                }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['inventory-stock'] });
            toast.success(t('inventory.receive.success'));
            onClose();
            setFormData(prev => ({ ...prev, batch_number: '', quantity: 1 }));
        },
        onError: (error) => {
            toast.error(t('inventory.receive.fail') + (error.response?.data?.detail || error.message));
        }
    });

    const handleSubmit = (event) => {
        event.preventDefault();
        if (!formData.material_id || !formData.warehouse_id) {
            toast.error(t('inventory.receive.validation_error'));
            return;
        }
        if (!formData.expiry_date) {
            toast.error(`${t('inventory.receive.expiry_date')} is required.`);
            return;
        }

        const selectedMat = materials.find(material => material.id === parseInt(formData.material_id, 10));
        const ratio = selectedMat?.packaging_ratio || 1.0;
        const finalCostPerUnit = (parseFloat(formData.package_price) || 0) / ratio;
        mutation.mutate({ ...formData, cost_per_unit: finalCostPerUnit });
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={t('inventory.receive.title')}
            size="2xl"
            closeOnOutside={!mutation.isPending}
        >
            <form onSubmit={handleSubmit} className="grid min-w-0 grid-cols-1 gap-4 md:grid-cols-2 md:gap-5">
                <div className="md:col-span-2">
                    <label className="mb-1 block text-sm font-medium text-text-secondary">{t('inventory.receive.select_material')}</label>
                    <select
                        required
                        value={formData.material_id}
                        onChange={event => {
                            const val = event.target.value;
                            const selectedMat = materials.find(material => material.id === parseInt(val, 10));
                            setFormData({
                                ...formData,
                                material_id: val,
                                package_price: selectedMat?.standard_price || 0
                            });
                        }}
                        className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2 outline-none focus:ring-2 focus:ring-secondary/20"
                    >
                        <option value="">{t('inventory.receive.select_placeholder_material')}</option>
                        {materials.map(material => {
                            const catName = material.category ? (i18n.language === 'ar' ? material.category.name_ar : material.category.name_en) : '';
                            const isNameDuplicate = material.name === catName;
                            return (
                                <option key={material.id} value={material.id}>
                                    {material.brand ? `${material.brand} ` : ''}
                                    {catName ? `(${catName}) ` : ''}
                                    {!isNameDuplicate && (material.brand || material.category) ? ' - ' : ''}
                                    {!isNameDuplicate ? `${material.name} ` : ''}
                                    ({material.base_unit})
                                </option>
                            );
                        })}
                    </select>
                </div>

                <div>
                    <label className="mb-1 block text-sm font-medium text-text-secondary">{t('inventory.receive.select_warehouse')}</label>
                    <div className="flex min-w-0 gap-2">
                        <select
                            required
                            value={formData.warehouse_id}
                            onChange={event => setFormData({ ...formData, warehouse_id: event.target.value })}
                            className="min-h-11 min-w-0 flex-1 rounded-xl border border-border bg-background px-3 py-2 outline-none focus:ring-2 focus:ring-secondary/20"
                        >
                            <option value="">{t('inventory.receive.select_placeholder_warehouse')}</option>
                            {warehouses.map(warehouse => (
                                <option key={warehouse.id} value={warehouse.id}>{warehouse.name} ({warehouse.type})</option>
                            ))}
                        </select>
                        <button
                            type="button"
                            onClick={() => setIsAddWarehouseOpen(true)}
                            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors hover:bg-primary/20"
                            title={t('inventory.actions.add_warehouse', 'إضافة مخزن جديد')}
                            aria-label={t('inventory.actions.add_warehouse', 'إضافة مخزن جديد')}
                        >
                            <Plus size={20} aria-hidden="true" />
                        </button>
                    </div>
                </div>

                <div>
                    <label className="mb-1 block text-sm font-medium text-text-secondary">{t('inventory.receive.quantity')}</label>
                    <input
                        type="number"
                        min="1"
                        step="any"
                        required
                        inputMode="decimal"
                        value={formData.quantity}
                        onChange={event => setFormData({ ...formData, quantity: event.target.value })}
                        className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2 font-mono"
                    />
                </div>

                <div className="border-t border-border pt-4 md:col-span-2 md:grid md:grid-cols-2 md:gap-5">
                    <div>
                        <label className="mb-1 block text-sm font-medium text-text-secondary">{t('inventory.receive.expiry_date')}</label>
                        <DateTimePicker
                            mode="month"
                            required
                            value={formData.expiry_date ? formData.expiry_date.slice(0, 7) : ''}
                            onChange={event => setFormData({ ...formData, expiry_date: event.target.value })}
                        />
                        <p className="mt-1 text-xs text-text-muted">{t('inventory.receive.expiry_note')}</p>
                    </div>

                    <div className="mt-4 md:mt-0">
                        <label className="mb-1 block text-sm font-medium text-text-secondary">{t('inventory.receive.package_price')}</label>
                        <input
                            type="number"
                            min="0"
                            step="0.01"
                            inputMode="decimal"
                            value={formData.package_price}
                            onChange={event => setFormData({ ...formData, package_price: event.target.value })}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2"
                            placeholder="0.00"
                        />
                        <p className="mt-1 text-[11px] text-text-secondary">{t('inventory.receive.price_note')}</p>
                    </div>
                </div>

                <div className="md:col-span-2">
                    <label className="mb-1 block text-sm font-medium text-text-secondary">{t('inventory.receive.supplier')}</label>
                    <input
                        type="text"
                        value={formData.supplier}
                        onChange={event => setFormData({ ...formData, supplier: event.target.value })}
                        className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2"
                        placeholder={t('inventory.receive.supplier_placeholder')}
                    />
                </div>

                <div className="sticky bottom-0 z-10 -mx-3 grid grid-cols-1 gap-2 border-t border-border bg-surface-elevated px-3 pb-[max(0.25rem,env(safe-area-inset-bottom))] pt-3 min-[360px]:grid-cols-2 sm:-mx-4 sm:px-4 md:col-span-2">
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
                        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-secondary px-4 py-2 font-bold text-white shadow-low transition-colors hover:brightness-95 disabled:opacity-50"
                    >
                        {mutation.isPending ? t('inventory.receive.receiving') : (
                            <>
                                <ArrowDownLeft size={18} aria-hidden="true" />
                                <span>{t('inventory.receive.confirm')}</span>
                            </>
                        )}
                    </button>
                </div>
            </form>

            <AddWarehouseModal
                isOpen={isAddWarehouseOpen}
                onClose={() => setIsAddWarehouseOpen(false)}
                onSuccess={(newWarehouse) => setFormData(prev => ({ ...prev, warehouse_id: newWarehouse.id }))}
            />
        </Modal>
    );
};

export default ReceiveStockModal;

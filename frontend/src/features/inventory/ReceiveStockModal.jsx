import React, { useState } from 'react';
import { X, ArrowDownLeft, Calendar, Plus } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMaterials, getWarehouses, receiveStock } from '@/api/inventory';
import { showToast } from '@/shared/ui/Toast';
import AddWarehouseModal from './components/AddWarehouseModal';
import { useTranslation } from 'react-i18next';

const ReceiveStockModal = ({ isOpen, onClose }) => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [isAddWarehouseOpen, setIsAddWarehouseOpen] = useState(false);

    // Data Fetching
    const { data: materials } = useQuery({ queryKey: ['inventory-materials'], queryFn: async () => (await getMaterials()).data });
    const { data: warehouses } = useQuery({ queryKey: ['inventory-warehouses'], queryFn: async () => (await getWarehouses()).data });

    // Helper to get today's date in YYYY-MM-DD format
    const getToday = () => new Date().toISOString().split('T')[0];

    const [formData, setFormData] = useState({
        material_id: '',
        warehouse_id: '',
        quantity: 1,
        batch_number: '',
        expiry_date: '',
        supplier: '',
        package_price: 0
    });

    const mutation = useMutation({
        mutationFn: (data) => {
            // Logic: Convert YYYY-MM to YYYY-MM-{LastDay}
            let finalExpiry = data.expiry_date;
            if (data.expiry_date && data.expiry_date.length === 7) {
                // It's YYYY-MM
                const [y, m] = data.expiry_date.split('-').map(Number);
                const lastDay = new Date(y, m, 0).getDate(); // Day 0 of next month is last day of this month
                finalExpiry = `${y}-${String(m).padStart(2, '0')}-${lastDay}`;
            }

            return receiveStock({
                material_id: parseInt(data.material_id),
                warehouse_id: parseInt(data.warehouse_id),
                quantity: parseFloat(data.quantity),
                batch: {
                    // Auto-generate hidden batch number based on Expiry Date
                    // Format: EXP-YYMMDD-{Random4Digit}
                    batch_number: `EXP-${finalExpiry.replace(/-/g, '')}-${Math.floor(1000 + Math.random() * 9000)}`,
                    expiry_date: finalExpiry,
                    supplier: data.supplier,
                    cost_per_unit: parseFloat(data.cost_per_unit)
                }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['inventory-stock']);
            showToast('success', t('inventory.receive.success'));
            onClose();
            // Reset crucial fields
            setFormData(prev => ({
                ...prev,
                batch_number: '',
                quantity: 1
            }));
        },
        onError: (error) => {
            showToast('error', t('inventory.receive.fail') + (error.response?.data?.detail || error.message));
        }
    });

    if (!isOpen) return null;

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!formData.material_id || !formData.warehouse_id) {
            showToast('error', t('inventory.receive.validation_error'));
            return;
        }

        // Calculate Cost Per Unit derived from Package Price
        const selectedMat = materials?.find(m => m.id === parseInt(formData.material_id));
        const ratio = selectedMat?.packaging_ratio || 1.0;
        const finalCostPerUnit = (parseFloat(formData.package_price) || 0) / ratio;

        mutation.mutate({
            ...formData,
            cost_per_unit: finalCostPerUnit
        });
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-surface w-full max-w-2xl rounded-2xl shadow-2xl border border-border overflow-hidden animate-in fade-in zoom-in duration-200">

                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-border bg-background">
                    <h2 className="text-lg font-bold flex items-center gap-2">
                        <ArrowDownLeft className="text-secondary" />
                        {t('inventory.receive.title')}
                    </h2>
                    <button onClick={onClose} className="p-2 hover:bg-surface-hover rounded-full transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">

                    {/* Material Selection */}
                    <div className="col-span-2">
                        <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.receive.select_material')}</label>
                        <select
                            required
                            value={formData.material_id}
                            onChange={e => {
                                const val = e.target.value;
                                const selectedMat = materials?.find(m => m.id === parseInt(val));
                                setFormData({
                                    ...formData,
                                    material_id: val,
                                    package_price: selectedMat?.standard_price || 0
                                });
                            }}
                            className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-secondary/20"
                        >
                            <option value="">{t('inventory.receive.select_placeholder_material')}</option>
                            {materials?.map(m => (
                                <option key={m.id} value={m.id}>{m.name} ({m.base_unit})</option>
                            ))}
                        </select>
                    </div>

                    {/* Warehouse Selection */}
                    <div>
                        <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.receive.select_warehouse')}</label>
                        <div className="flex gap-2">
                            <select
                                required
                                value={formData.warehouse_id}
                                onChange={e => setFormData({ ...formData, warehouse_id: e.target.value })}
                                className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-secondary/20"
                            >
                                <option value="">{t('inventory.receive.select_placeholder_warehouse')}</option>
                                {warehouses?.map(w => (
                                    <option key={w.id} value={w.id}>{w.name} ({w.type})</option>
                                ))}
                            </select>
                            <button
                                type="button"
                                onClick={() => setIsAddWarehouseOpen(true)}
                                className="p-2 bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors"
                                title="إضافة مخزن جديد"
                            >
                                <Plus size={20} />
                            </button>
                        </div>
                    </div>

                    {/* Quantity */}
                    <div>
                        <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.receive.quantity')}</label>
                        <input
                            type="number"
                            min="1"
                            step="any"
                            required
                            value={formData.quantity}
                            onChange={e => setFormData({ ...formData, quantity: e.target.value })}
                            className="w-full px-4 py-2 rounded-lg border border-border bg-background font-mono"
                        />
                    </div>

                    <div className="col-span-2 border-t border-border my-2"></div>

                    {/* Batch Details Group */}
                    <div>
                        <label className="block text-sm font-medium text-text-secondary mb-1">
                            {t('inventory.receive.expiry_date')}
                        </label>
                        <div className="relative">
                            <input
                                type="month"
                                required
                                min={new Date().toISOString().slice(0, 7)}
                                value={formData.expiry_date ? formData.expiry_date.slice(0, 7) : ''}
                                onChange={e => {
                                    setFormData({ ...formData, expiry_date: e.target.value });
                                }}
                                className="w-full px-4 py-2 rounded-lg border border-border bg-background ltr-text"
                                style={{ direction: 'ltr' }}
                            />
                            <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none" size={16} />
                        </div>
                        <p className="text-xs text-slate-400 mt-1">{t('inventory.receive.expiry_note')}</p>
                    </div>

                    {/* PACKAGE PRICE INPUT */}
                    <div>
                        <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.receive.package_price')}</label>
                        <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={formData.package_price}
                            onChange={e => setFormData({ ...formData, package_price: e.target.value })}
                            className="w-full px-4 py-2 rounded-lg border border-border bg-background"
                            placeholder="0.00"
                        />
                        <p className="text-[10px] text-text-secondary mt-1">
                            {t('inventory.receive.price_note')}
                        </p>
                    </div>

                    {/* Supplier - Full Width */}
                    <div className="col-span-2">
                        <label className="block text-sm font-medium text-text-secondary mb-1">{t('inventory.receive.supplier')}</label>
                        <input
                            type="text"
                            value={formData.supplier}
                            onChange={e => setFormData({ ...formData, supplier: e.target.value })}
                            className="w-full px-4 py-2 rounded-lg border border-border bg-background"
                            placeholder={t('inventory.receive.supplier_placeholder')}
                        />
                    </div>

                    {/* Actions */}
                    <div className="col-span-2 pt-4 flex justify-end gap-3 mt-4 border-t border-border">
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
                            className="flex items-center gap-2 px-8 py-2 bg-secondary text-white rounded-lg font-bold hover:bg-secondary-600 disabled:opacity-50 transition-all shadow-lg shadow-secondary/20"
                        >
                            {mutation.isPending ? t('inventory.receive.receiving') : (
                                <>
                                    <ArrowDownLeft size={18} />
                                    <span>{t('inventory.receive.confirm')}</span>
                                </>
                            )}
                        </button>
                    </div>
                </form>

                {/* Nested Modals */}
                <AddWarehouseModal
                    isOpen={isAddWarehouseOpen}
                    onClose={() => setIsAddWarehouseOpen(false)}
                    onSuccess={(newWh) => setFormData(prev => ({ ...prev, warehouse_id: newWh.id }))}
                />
            </div>
        </div>
    );
};

export default ReceiveStockModal;

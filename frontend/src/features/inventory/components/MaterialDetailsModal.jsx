import React, { useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getMaterialStock, updateMaterial } from '@/api/inventory';
import { X, Package, Calendar, Truck, AlertCircle, Square, Settings } from 'lucide-react';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { toast } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
const MaterialDetailsModal = ({ isOpen, onClose, material, activeSessions = [] }) => {
    const { t } = useTranslation();
    // Handle both 'id' (Active Session) and 'material_id' (Stock Summary) formats
    const materialId = material?.material_id || material?.id;
    const [isEditing, setIsEditing] = React.useState(false);
    const [formData, setFormData] = React.useState({
        type: 'NON_DIVISIBLE',
        base_unit: '',
        packaging_ratio: 1.0,
        standard_price: 0.0
    });
    const queryClient = useQueryClient();
    const { data: stockItems, isLoading } = useQuery({
        queryKey: ['material-stock', materialId],
        queryFn: async () => {
            const res = await getMaterialStock(materialId);
            return res.data;
        },
        enabled: !!materialId && isOpen
    });
    // Initialize form data when material changes
    React.useEffect(() => {
        if (material) {
            setFormData({
                // Fix: Handle both 'type' (API) and 'material_type' (StockSummary)
                type: material.type || material.material_type || 'NON_DIVISIBLE',
                // Fix: Handle both 'base_unit' (API) and 'unit' (StockSummary)
                base_unit: material.base_unit || material.unit || '',
                packaging_ratio: material.packaging_ratio || 1.0,
                standard_price: material.standard_price || 0.0
            });
        }
    }, [material]);
    const activeSessionMap = useMemo(() => {
        const map = {};
        const sessions = Array.isArray(activeSessions) ? activeSessions : [];
        sessions.forEach(s => {
            map[s.stock_item_id] = s;
        });
        return map;
    }, [activeSessions]);
    const handleSaveSettings = async () => {
        try {
            await updateMaterial(materialId, formData);
            setIsEditing(false);
            queryClient.invalidateQueries(['inventory-stock']);
            toast.success(t('inventory.material_details.messages.update_success'));
        } catch (error) {
            console.error("Failed to update material", error);
            toast.error(t('inventory.material_details.messages.update_fail'));
        }
    };
    if (!isOpen || !material) return null;
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-surface w-full max-w-4xl rounded-xl shadow-2xl border border-border flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-border">
                    <div>
                        <h2 className="text-xl font-bold text-text-primary flex items-center gap-2">
                            <Package className="text-primary" />
                            {material.material_name || material.name}
                        </h2>
                        <p className="text-sm text-text-secondary mt-1">
                            {t('inventory.material_details.title')}
                        </p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-surface-hover rounded-full transition-colors">
                        <X size={20} className="text-text-secondary" />
                    </button>
                </div>
                {/* Material Settings Section */}
                <div className="p-4 bg-secondary/5 border-b border-border">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                            <Settings size={16} /> {t('inventory.material_details.settings.title')}
                        </h3>
                        {!isEditing ? (
                            <button
                                onClick={() => setIsEditing(true)}
                                className="text-xs text-primary hover:underline"
                            >
                                {t('inventory.material_details.settings.edit')}
                            </button>
                        ) : (
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setIsEditing(false)}
                                    className="text-xs text-text-secondary hover:text-text-primary"
                                >
                                    {t('inventory.material_details.settings.cancel')}
                                </button>
                                <button
                                    onClick={handleSaveSettings}
                                    className="text-xs bg-primary text-white px-3 py-1 rounded hover:bg-primary-hover"
                                >
                                    {t('inventory.material_details.settings.save')}
                                </button>
                            </div>
                        )}
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <label className="block text-xs text-text-secondary mb-1">{t('inventory.material_details.settings.type')}</label>
                            {isEditing ? (
                                <select
                                    value={formData.type}
                                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                                    className="w-full text-sm p-1 border rounded bg-surface"
                                >
                                    <option value="NON_DIVISIBLE">{t('inventory.material_details.settings.type_indivisible')}</option>
                                    <option value="DIVISIBLE">{t('inventory.material_details.settings.type_divisible')}</option>
                                </select>
                            ) : (
                                <span className={`text-sm font-medium ${formData.type === 'DIVISIBLE' ? 'text-blue-600' : 'text-gray-700'}`}>
                                    {formData.type === 'DIVISIBLE' ? t('inventory.material_details.settings.type_divisible') : t('inventory.material_details.settings.type_indivisible')}
                                </span>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs text-text-secondary mb-1">{t('inventory.material_details.settings.unit')}</label>
                            {isEditing ? (
                                <input
                                    type="text"
                                    value={formData.base_unit}
                                    onChange={(e) => setFormData({ ...formData, base_unit: e.target.value })}
                                    placeholder="e.g., ml, g, pcs"
                                    className="w-full text-sm p-1 border rounded bg-surface"
                                />
                            ) : (
                                <span className="text-sm font-medium">{formData.base_unit || '-'}</span>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs text-text-secondary mb-1">{t('inventory.material_details.settings.ratio')}</label>
                            {isEditing ? (
                                <input
                                    type="number"
                                    value={formData.packaging_ratio}
                                    onChange={(e) => setFormData({ ...formData, packaging_ratio: parseFloat(e.target.value) })}
                                    step="0.01"
                                    className="w-full text-sm p-1 border rounded bg-surface"
                                />
                            ) : (
                                <span className="text-sm font-medium">{formData.packaging_ratio}</span>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs text-text-secondary mb-1">{t('inventory.material_details.settings.price')}</label>
                            {isEditing ? (
                                <input
                                    type="number"
                                    value={formData.standard_price}
                                    onChange={(e) => setFormData({ ...formData, standard_price: parseFloat(e.target.value) })}
                                    className="w-full text-sm p-1 border rounded bg-surface"
                                />
                            ) : (
                                <span className="text-sm font-medium">{formData.standard_price || 0} ج.م</span>
                            )}
                        </div>
                    </div>
                </div>
                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
                    {isLoading ? (
                        <div className="flex justify-center py-12">
                            <LoadingSpinner />
                        </div>
                    ) : !stockItems || stockItems.length === 0 ? (
                        <div className="text-center py-12 text-text-secondary">
                            <Package size={48} className="mx-auto mb-4 opacity-20" />
                            <p>{t('inventory.material_details.empty')}</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 gap-4">
                            {stockItems.map((item) => {
                                const activeSession = activeSessionMap[item.id];
                                const isExpired = new Date(item.batch?.expiry_date) < new Date();
                                const isNearExpiry = new Date(item.batch?.expiry_date) < new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
                                return (
                                    <div
                                        key={item.id}
                                        className={`
                                            relative p-4 rounded-xl border transition-all
                                            ${activeSession
                                                ? 'bg-red-50/50 border-red-200 ring-1 ring-red-100'
                                                : 'bg-background border-border hover:border-primary/30'}
                                        `}
                                    >
                                        <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
                                            {/* Batch Info */}
                                            <div className="flex items-center gap-4">
                                                <div className={`
                                                    p-3 rounded-lg 
                                                    ${activeSession ? 'bg-red-100 text-red-600' : 'bg-secondary/10 text-secondary'}
                                                `}>
                                                    {activeSession ? <Square size={24} className="animate-pulse" /> : <Package size={24} />}
                                                </div>
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-mono font-bold text-lg dir-ltr">
                                                            {item.batch?.batch_number}
                                                        </span>
                                                        {activeSession && (
                                                            <span className="px-2 py-0.5 bg-red-100 text-red-600 text-[10px] font-bold rounded-full border border-red-200">
                                                                {t('inventory.material_details.active_badge')}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-4 text-sm text-text-secondary mt-1">
                                                        <span className="flex items-center gap-1" title="تاريخ الصلاحية">
                                                            <Calendar size={14} />
                                                            <span className={`dir-ltr ${isExpired ? 'text-red-500 font-bold' : isNearExpiry ? 'text-amber-500 font-bold' : ''}`}>
                                                                {item.batch?.expiry_date}
                                                            </span>
                                                        </span>
                                                        {item.batch?.supplier && (
                                                            <span className="flex items-center gap-1" title="المورد">
                                                                <Truck size={14} />
                                                                {item.batch.supplier}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            {/* Quantity & Warehouse */}
                                            <div className="text-right">
                                                <div className="font-bold text-xl text-text-primary">
                                                    {item.quantity} <span className="text-sm font-normal text-text-secondary">{(material.unit || material.base_unit)}</span>
                                                </div>
                                                <div className="text-xs text-text-secondary mt-0.5">
                                                    المستودع: {item.warehouse?.name || 'Main'}
                                                </div>
                                            </div>
                                        </div>
                                        {/* Usage Bar (Visual only for now) */}
                                        {activeSession && (
                                            <div className="mt-4 pt-4 border-t border-red-100 flex items-center justify-between text-xs text-red-700">
                                                <span className="flex items-center gap-1">
                                                    <AlertCircle size={14} />
                                                    {t('inventory.material_details.usage_bar')}
                                                </span>
                                                <span className="font-mono dir-ltr">
                                                    {t('inventory.material_details.started_at')} {new Date(activeSession.opened_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
                {/* Footer */}
                <div className="p-4 border-t border-border bg-surface-hover/30 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-6 py-2 bg-surface border border-border hover:bg-surface-hover rounded-lg transition-colors font-medium text-text-secondary"
                    >
                        {t('inventory.material_details.close')}
                    </button>
                </div>
            </div>
        </div>
    );
};
export default MaterialDetailsModal;


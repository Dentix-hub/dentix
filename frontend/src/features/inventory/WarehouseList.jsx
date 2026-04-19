import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getWarehouses, deleteWarehouse } from '@/api/inventory';
import { Warehouse, Trash2, MapPin, Plus } from 'lucide-react';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { showToast } from '@/shared/ui/Toast';
import AddWarehouseModal from './components/AddWarehouseModal';
import WarehouseDetailsModal from './components/WarehouseDetailsModal';
import { useTranslation } from 'react-i18next';
const WarehouseList = () => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [selectedWarehouse, setSelectedWarehouse] = useState(null);
    const { data: warehouses, isLoading } = useQuery({
        queryKey: ['warehouses'],
        queryFn: async () => {
            const res = await getWarehouses();
            return Array.isArray(res.data) ? res.data : [];
        }
    });
    const deleteMutation = useMutation({
        mutationFn: deleteWarehouse,
        onSuccess: () => {
            queryClient.invalidateQueries(['warehouses']);
            showToast('success', t('inventory.warehouses.delete_success'));
        },
        onError: (err) => {
            showToast('error', err.response?.data?.detail || t('inventory.warehouses.delete_fail'));
        }
    });
    const handleDelete = (e, id, name) => {
        e.stopPropagation(); // Prevent opening modal
        if (window.confirm(t('inventory.warehouses.delete_confirm', { name }))) {
            deleteMutation.mutate(id);
        }
    };
    if (isLoading) return <LoadingSpinner />;
    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            {/* Header Actions */}
            <div className="flex justify-end">
                <button
                    onClick={() => setIsAddOpen(true)}
                    className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-hover transition-colors shadow-sm font-medium"
                >
                    <Plus size={20} />
                    {t('inventory.warehouses.add_button')}
                </button>
            </div>
            {/* Grid */}
            {!warehouses || warehouses.length === 0 ? (
                <div className="text-center py-12 text-gray-500 bg-gray-50 rounded-xl border border-dashed border-gray-300">
                    <Warehouse size={48} className="mx-auto mb-3 opacity-20" />
                    <p>{t('inventory.warehouses.empty_desc')}</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {warehouses.map((wh) => (
                        <div
                            key={wh.id}
                            onClick={() => setSelectedWarehouse(wh)}
                            className="bg-white p-5 rounded-xl border border-slate-200 hover:border-primary/50 hover:shadow-md transition-all group relative cursor-pointer"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="p-3 bg-blue-50 text-blue-600 rounded-lg group-hover:bg-blue-100 transition-colors">
                                        <Warehouse size={24} />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-lg text-slate-800">{wh.name}</h3>
                                        {wh.location && (
                                            <div className="flex items-center gap-1 text-sm text-slate-500 mt-1">
                                                <MapPin size={14} />
                                                {wh.location}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <button
                                    onClick={(e) => handleDelete(e, wh.id, wh.name)}
                                    className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                                    title="حذف المخزن"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </div>
                            {wh.description && (
                                <p className="text-sm text-slate-500 mt-4 line-clamp-2">
                                    {wh.description}
                                </p>
                            )}
                            <div className="mt-4 pt-4 border-t border-slate-100 flex justify-end">
                                <span className="text-xs font-semibold text-primary">{t('inventory.warehouses.click_to_view')}</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
            <AddWarehouseModal
                isOpen={isAddOpen}
                onClose={() => setIsAddOpen(false)}
            />
            <WarehouseDetailsModal
                isOpen={!!selectedWarehouse}
                warehouse={selectedWarehouse}
                onClose={() => setSelectedWarehouse(null)}
            />
        </div>
    );
};
export default WarehouseList;


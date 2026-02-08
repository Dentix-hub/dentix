import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { X, Package, Layers } from 'lucide-react';
import api from '@/api'; // Using base API instance for flexible query
import LoadingSpinner from '@/shared/ui/LoadingSpinner';

const WarehouseDetailsModal = ({ isOpen, onClose, warehouse }) => {

    const { data: stockItems, isLoading } = useQuery({
        queryKey: ['warehouse-stock', warehouse?.id],
        queryFn: async () => {
            // Using the stock summary endpoint but filtered by warehouse
            const res = await api.get('/api/v1/inventory/stock', {
                params: { warehouse_id: warehouse.id }
            });
            return Array.isArray(res.data) ? res.data : [];
        },
        enabled: !!isOpen && !!warehouse,
    });

    if (!isOpen || !warehouse) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-surface w-full max-w-2xl rounded-2xl shadow-xl border border-border overflow-hidden animate-in fade-in zoom-in duration-200 flex flex-col max-h-[85vh]">

                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-border bg-background">
                    <h2 className="text-lg font-bold flex items-center gap-2">
                        <Layers className="text-primary" size={20} />
                        محتويات: {warehouse.name}
                    </h2>
                    <button onClick={onClose} className="p-2 hover:bg-surface-hover rounded-full transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-0 overflow-y-auto flex-1">
                    {isLoading ? (
                        <div className="p-12 flex justify-center">
                            <LoadingSpinner />
                        </div>
                    ) : !stockItems || stockItems.length === 0 ? (
                        <div className="text-center py-16 px-4">
                            <Package size={48} className="mx-auto text-slate-300 mb-4" />
                            <h3 className="text-xl font-bold text-slate-700">المخزن فارغ</h3>
                            <p className="text-slate-500 mt-2">لا توجد مواد مخزنة هنا حالياً.</p>
                        </div>
                    ) : (
                        <table className="w-full text-right">
                            <thead className="bg-slate-50 sticky top-0 z-10 border-b border-slate-200">
                                <tr>
                                    <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">المادة</th>
                                    <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">النوع</th>
                                    <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">الكمية الإجمالية</th>
                                    <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">الحالة</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {stockItems.map((item) => (
                                    <tr key={item.material_id} className="hover:bg-slate-50/50 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="font-bold text-slate-800">{item.material_name}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-xs font-medium px-2 py-1 bg-slate-100 rounded-full text-slate-600">
                                                {item.material_type}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="font-bold font-mono text-primary">
                                                {item.total_quantity} <span className="text-xs text-slate-400">{item.unit}</span>
                                            </div>
                                            {item.packaging_ratio > 1 && (
                                                <div className="text-xs text-slate-400 mt-0.5">
                                                    {(item.total_quantity / item.packaging_ratio).toFixed(1)} box
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            {item.alert_status === 'CRITICAL' ? (
                                                <span className="text-xs font-bold text-red-600 bg-red-50 px-2 py-1 rounded-full">نفذت</span>
                                            ) : item.alert_status === 'LOW' ? (
                                                <span className="text-xs font-bold text-amber-600 bg-amber-50 px-2 py-1 rounded-full">منخفض</span>
                                            ) : (
                                                <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded-full">متوفر</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-border bg-slate-50 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-6 py-2 bg-white border border-slate-300 rounded-lg font-medium hover:bg-slate-50 shadow-sm"
                    >
                        إغلاق
                    </button>
                </div>
            </div>
        </div>
    );
};

export default WarehouseDetailsModal;

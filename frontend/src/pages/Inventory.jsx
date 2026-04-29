import { useState } from 'react';
import StockList from '@/features/inventory/StockList';
import WarehouseList from '@/features/inventory/WarehouseList';
import AddMaterialModal from '@/features/inventory/AddMaterialModal';
import ReceiveStockModal from '@/features/inventory/ReceiveStockModal';
import { getExpiryAlerts } from '@/api/inventory';
import { Package, AlertTriangle, Layers, Warehouse } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
const Inventory = () => {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState('stock'); // 'stock' | 'warehouses'
    const [editingMaterial, setEditingMaterial] = useState(null);
    const [isAddMaterialOpen, setIsAddMaterialOpen] = useState(false);
    const [isReceiveStockOpen, setIsReceiveStockOpen] = useState(false);
    const { data: alerts = [] } = useQuery({
        queryKey: ['inventory-alerts'],
        queryFn: async () => {
            if (!getExpiryAlerts) return [];
            try {
                const res = await getExpiryAlerts();
                return Array.isArray(res.data) ? res.data : [];
            } catch (e) {
                console.error("Alerts fetch error", e);
                return [];
            }
        },
        enabled: !!getExpiryAlerts
    });
    const handleOpenAdd = () => {
        setEditingMaterial(null);
        setIsAddMaterialOpen(true);
    };
    const handleOpenEdit = (material) => {
        setEditingMaterial(material);
        setIsAddMaterialOpen(true);
    };
    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-black text-text-primary flex items-center gap-3">
                        <Package className="text-primary" size={32} />
                        {t('inventory.title')}
                    </h1>
                    <p className="text-text-secondary mt-1">{t('inventory.subtitle')}</p>
                </div>
            </div>
            {/* Tabs */}
            <div className="flex border-b border-border">
                <button
                    onClick={() => setActiveTab('stock')}
                    className={`pb-3 px-6 text-sm font-bold flex items-center gap-2 transition-colors relative
                        ${activeTab === 'stock' ? 'text-primary' : 'text-text-secondary hover:text-text-primary'}
                    `}
                >
                    <Layers size={18} />
                    {t('inventory.tabs.stock')}
                    {activeTab === 'stock' && (
                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t-full" />
                    )}
                </button>
                <button
                    onClick={() => setActiveTab('warehouses')}
                    className={`pb-3 px-6 text-sm font-bold flex items-center gap-2 transition-colors relative
                        ${activeTab === 'warehouses' ? 'text-primary' : 'text-text-secondary hover:text-text-primary'}
                    `}
                >
                    <Warehouse size={18} />
                    {t('inventory.tabs.warehouses')}
                    {activeTab === 'warehouses' && (
                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t-full" />
                    )}
                </button>
            </div>
            {/* Content based on Tab */}
            {activeTab === 'stock' ? (
                <>
                    {/* Alerts Section */}
                    {alerts && alerts.length > 0 && (
                        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 animate-in slide-in-from-top-2">
                            <h3 className="flex items-center gap-2 text-red-800 font-bold mb-3">
                                <AlertTriangle size={20} />
                                {t('inventory.alerts.title')}
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {alerts.slice(0, 6).map((alert, idx) => (
                                    <div key={idx} className="bg-white p-3 rounded-xl border border-red-100 flex items-center justify-between shadow-sm">
                                        <div>
                                            <div className="font-bold text-slate-800">{alert.material_name}</div>
                                            <div className="text-xs text-slate-500 font-mono">{alert.batch_number}</div>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-sm font-bold text-red-600">{alert.days_left} {t('inventory.alerts.days_left')}</div>
                                            <div className="text-xs text-slate-400">{new Date(alert.expiry_date).toLocaleDateString()}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            {alerts.length > 6 && (
                                <div className="text-center mt-3 text-sm text-red-600 font-medium cursor-pointer hover:underline">
                                    + {alerts.length - 6} {t('inventory.alerts.more_alerts', 'تنبيهات إضافية')}
                                </div>
                            )}
                        </div>
                    )}
                    {/* Main Content */}
                    <StockList
                        onAddMaterial={handleOpenAdd}
                        onEditMaterial={handleOpenEdit}
                        onReceiveStock={() => setIsReceiveStockOpen(true)}
                    />
                </>
            ) : (
                <WarehouseList />
            )}
            {/* Modals */}
            <AddMaterialModal
                isOpen={isAddMaterialOpen}
                onClose={() => setIsAddMaterialOpen(false)}
                initialData={editingMaterial}
            />
            <ReceiveStockModal
                isOpen={isReceiveStockOpen}
                onClose={() => setIsReceiveStockOpen(false)}
            />
        </div>
    );
};
export default Inventory;


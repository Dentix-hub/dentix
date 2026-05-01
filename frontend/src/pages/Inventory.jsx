import { useState } from 'react';
import StockList from '@/features/inventory/StockList';
import WarehouseList from '@/features/inventory/WarehouseList';
import AddMaterialModal from '@/features/inventory/AddMaterialModal';
import ReceiveStockModal from '@/features/inventory/ReceiveStockModal';
import { getExpiryAlerts } from '@/api/inventory';
import { Package, AlertTriangle, Layers, Warehouse, Home } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { PageHeader, TabGroup } from '@/shared/ui';

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
        enabled: !!getExpiryAlerts,
        staleTime: 60 * 1000,
        retry: 1,
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
        <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <PageHeader
                title={t('inventory.title')}
                subtitle={t('inventory.subtitle')}
                icon={Package}
                breadcrumbs={[
                    { label: t('nav.home', 'Home'), icon: Home, path: '/' },
                    { label: t('inventory.title') }
                ]}
            />

            {/* Tabs */}
            <TabGroup
                variant="underline"
                activeTab={activeTab}
                onChange={setActiveTab}
                tabs={[
                    { id: 'stock', label: t('inventory.tabs.stock'), icon: Layers },
                    { id: 'warehouses', label: t('inventory.tabs.warehouses'), icon: Warehouse }
                ]}
            />
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
            {/* Modals - Only mount when open to prevent unnecessary hook execution */}
            {isAddMaterialOpen && (
                <AddMaterialModal
                    isOpen={isAddMaterialOpen}
                    onClose={() => setIsAddMaterialOpen(false)}
                    initialData={editingMaterial}
                />
            )}
            {isReceiveStockOpen && (
                <ReceiveStockModal
                    isOpen={isReceiveStockOpen}
                    onClose={() => setIsReceiveStockOpen(false)}
                />
            )}
        </div>
    );
};
export default Inventory;


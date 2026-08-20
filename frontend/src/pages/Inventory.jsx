import { useState } from 'react';
import logger from '@/utils/logger';
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
    const [activeTab, setActiveTab] = useState('stock');
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
            } catch (error) {
                logger.error('Alerts fetch error', error);
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
        <div className="mx-auto min-w-0 max-w-7xl space-y-5 pb-8 animate-in fade-in slide-in-from-bottom-4 duration-700 sm:space-y-6 sm:pb-12">
            <PageHeader
                title={t('inventory.title')}
                subtitle={t('inventory.subtitle')}
                icon={Package}
                breadcrumbs={[
                    { label: t('nav.home', 'Home'), icon: Home, path: '/' },
                    { label: t('inventory.title') }
                ]}
            />

            <div className="min-w-0 overflow-x-auto overscroll-x-contain">
                <TabGroup
                    variant="underline"
                    activeTab={activeTab}
                    onChange={setActiveTab}
                    tabs={[
                        { id: 'stock', label: t('inventory.tabs.stock'), icon: Layers },
                        { id: 'warehouses', label: t('inventory.tabs.warehouses'), icon: Warehouse }
                    ]}
                />
            </div>

            {activeTab === 'stock' ? (
                <>
                    {alerts.length > 0 && (
                        <section className="min-w-0 rounded-2xl border border-red-200 bg-red-50 p-3 animate-in slide-in-from-top-2 sm:p-4">
                            <h3 className="mb-3 flex items-center gap-2 font-bold text-red-800">
                                <AlertTriangle size={20} className="shrink-0" aria-hidden="true" />
                                <span className="break-words">{t('inventory.alerts.title')}</span>
                            </h3>
                            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
                                {alerts.slice(0, 6).map((alert, idx) => (
                                    <article key={`${alert.material_name}-${alert.batch_number}-${idx}`} className="flex min-w-0 flex-col gap-2 rounded-xl border border-red-100 bg-white p-3 shadow-sm min-[360px]:flex-row min-[360px]:items-center min-[360px]:justify-between">
                                        <div className="min-w-0">
                                            <div className="break-words font-bold text-slate-800">{alert.material_name}</div>
                                            <div className="truncate font-mono text-xs text-slate-500">{alert.batch_number}</div>
                                        </div>
                                        <div className="shrink-0 text-start min-[360px]:text-end">
                                            <div className="text-sm font-bold text-red-600">{alert.days_left} {t('inventory.alerts.days_left')}</div>
                                            <div className="text-xs text-slate-500" dir="ltr">{new Date(alert.expiry_date).toLocaleDateString()}</div>
                                        </div>
                                    </article>
                                ))}
                            </div>
                            {alerts.length > 6 && (
                                <p className="mt-3 text-center text-sm font-medium text-red-600">
                                    + {alerts.length - 6} {t('inventory.alerts.more_alerts', 'تنبيهات إضافية')}
                                </p>
                            )}
                        </section>
                    )}

                    <StockList
                        onAddMaterial={handleOpenAdd}
                        onEditMaterial={handleOpenEdit}
                        onReceiveStock={() => setIsReceiveStockOpen(true)}
                    />
                </>
            ) : (
                <WarehouseList />
            )}

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

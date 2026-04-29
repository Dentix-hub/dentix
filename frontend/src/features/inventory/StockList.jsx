import { useState, useMemo } from 'react';
import {
    Search, Plus, Package, ArrowDownLeft, Brain, Play, Square, AlertCircle, Trash2, Edit
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getStockSummary, getActiveSessions, deleteMaterial } from '@/api/inventory';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { useTranslation } from 'react-i18next';
import SmartLearningModal from './components/SmartLearningModal';
import TrackSessionModal from './components/TrackSessionModal';
import MaterialDetailsModal from './components/MaterialDetailsModal';
const StockList = ({ onAddMaterial, onReceiveStock, onEditMaterial }) => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [searchQuery, setSearchQuery] = useState('');
    const [filter, setFilter] = useState('ALL');
    const [smartMaterial, setSmartMaterial] = useState(null);
    const [selectedMaterial, setSelectedMaterial] = useState(null); // For Details Modal
    const [sessionModal, setSessionModal] = useState({ open: false, mode: 'OPEN', material: null, session: null });
    const { data: stockItems, isLoading, error } = useQuery({
        queryKey: ['inventory-stock'],
        queryFn: async () => {
            const res = await getStockSummary();
            return Array.isArray(res.data) ? res.data : [];
        }
    });
    const { data: activeSessions } = useQuery({
        queryKey: ['active-sessions'],
        queryFn: async () => {
            const res = await getActiveSessions();
            return Array.isArray(res.data) ? res.data : [];
        },
        refetchInterval: 30000 // Refresh every 30s
    });
    const deleteMutation = useMutation({
        mutationFn: deleteMaterial,
        onSuccess: () => {
            queryClient.invalidateQueries(['inventory-stock']);
            alert(t('inventory.messages.delete_success'));
        },
        onError: (err) => {
            console.error(err);
            const msg = err.response?.data?.detail
                || err.response?.data?.error?.message
                || t('inventory.messages.delete_fail');
            alert(msg);
        }
    });
    // Map material_id -> Active Session (just take first one for MVP, or indicate count)
    const activeSessionsMap = useMemo(() => {
        const map = {};
        if (activeSessions) {
            const safeSessions = Array.isArray(activeSessions) ? activeSessions : [];
            safeSessions.forEach(sess => {
                // Fix: stock_item is nested with batch
                const matId = sess.stock_item?.batch?.material_id;
                if (matId) {
                    if (!map[matId]) map[matId] = [];
                    map[matId].push(sess);
                }
            });
        }
        return map;
    }, [activeSessions]);
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 25;

    const filteredItems = useMemo(() => {
        return (stockItems || [])?.filter(item => {
            const matchesSearch = (item.material_name || '').toLowerCase().includes((searchQuery || '').toLowerCase());
            if (filter === 'ALL') return matchesSearch;
            return matchesSearch && item.alert_status === filter;
        });
    }, [stockItems, searchQuery, filter]);

    const paginatedItems = useMemo(() => {
        const start = (currentPage - 1) * ITEMS_PER_PAGE;
        return filteredItems.slice(start, start + ITEMS_PER_PAGE);
    }, [filteredItems, currentPage]);

    const totalPages = Math.ceil(filteredItems.length / ITEMS_PER_PAGE);

    const handleOpenSession = (item) => {
        setSessionModal({
            open: true,
            mode: 'OPEN',
            material: { id: item.material_id, name: item.material_name, unit: item.unit },
            session: null
        });
    };
    const handleCloseSession = (session) => {
        setSessionModal({
            open: true,
            mode: 'CLOSE',
            material: null,
            session: session
        });
    };
    const handleDelete = (id, name) => {
        if (window.confirm(t('inventory.messages.delete_confirm', { name }))) {
            deleteMutation.mutate(id);
        }
    };
    if (isLoading) return <LoadingSpinner />;
    if (error) return <div className="text-red-500 text-center p-4">حدث خطأ في تحميل البيانات</div>;
    return (
        <div className="space-y-4">
            {/* Header Actions */}
            <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-surface p-4 rounded-xl shadow-sm border border-border">
                <div className="relative w-full md:w-96">
                    <Search className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary" size={20} />
                    <input
                        type="text"
                        placeholder={t('inventory.actions.search_placeholder')}
                        value={searchQuery}
                        onChange={(e) => {
                            setSearchQuery(e.target.value);
                            setCurrentPage(1);
                        }}
                        className="w-full pr-10 pl-4 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                    />
                </div>
                <div className="flex gap-2 w-full md:w-auto">
                    <select
                        value={filter}
                        onChange={(e) => {
                            setFilter(e.target.value);
                            setCurrentPage(1);
                        }}
                        className="px-4 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20"
                    >
                        <option value="ALL">{t('inventory.filters.all')}</option>
                        <option value="LOW">{t('inventory.filters.low')}</option>
                        <option value="CRITICAL">{t('inventory.filters.critical')}</option>
                    </select>
                    <button
                        onClick={onReceiveStock}
                        className="flex items-center gap-2 px-4 py-2 bg-secondary/10 text-secondary hover:bg-secondary/20 rounded-lg font-bold transition-colors"
                    >
                        <ArrowDownLeft size={18} />
                        <span>{t('inventory.actions.receive_stock')}</span>
                    </button>
                    <button
                        onClick={onAddMaterial}
                        className="flex items-center gap-2 px-4 py-2 bg-primary text-white hover:bg-primary-600 rounded-lg font-bold transition-colors shadow-lg shadow-primary/20"
                    >
                        <Plus size={18} />
                        <span>{t('inventory.actions.new_material')}</span>
                    </button>
                </div>
            </div>
            {/* Table */}
            <div className="bg-surface rounded-xl shadow-sm border border-border overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-right">
                        <thead className="bg-background border-b border-border">
                            <tr>
                                <th className="px-6 py-4 text-sm font-bold text-text-secondary">{t('inventory.table.material')}</th>
                                <th className="px-6 py-4 text-sm font-bold text-text-secondary">{t('inventory.table.type')}</th>
                                <th className="px-6 py-4 text-sm font-bold text-text-secondary">{t('inventory.table.standard_price')}</th>
                                <th className="px-6 py-4 text-sm font-bold text-text-secondary">{t('inventory.table.current_stock')}</th>
                                {/* Batches column removed */}
                                <th className="px-6 py-4 text-sm font-bold text-text-secondary">{t('inventory.table.status')}</th>
                                <th className="px-6 py-4 text-sm font-bold text-text-secondary">{t('inventory.table.sessions')}</th>
                                <th className="px-6 py-4 text-sm font-bold text-text-secondary">{t('inventory.table.actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {paginatedItems?.length === 0 ? (
                                <tr>
                                    <td colSpan="8" className="px-6 py-12 text-center text-text-secondary">
                                        <Package size={48} className="mx-auto mb-2 opacity-20" />
                                        <p>{t('inventory.table.empty')}</p>
                                    </td>
                                </tr>
                            ) : (
                                paginatedItems?.map((item) => {
                                    const sessions = activeSessionsMap[item.material_id] || [];
                                    const hasActiveSession = sessions.length > 0;
                                    return (
                                        <tr key={item.material_id} className="hover:bg-surface-hover transition-colors group">
                                            <td
                                                onClick={() => setSelectedMaterial(item)}
                                                className="px-6 py-4 font-bold text-text-primary cursor-pointer hover:text-primary transition-colors underline decoration-dotted decoration-text-secondary/30 hover:decoration-primary"
                                                title={t('inventory.table.details_tooltip')}
                                            >
                                                <div className="text-base">{item.brand || item.material_name}</div>
                                                {item.brand && (
                                                    <span className="text-[10px] text-text-secondary block font-normal opacity-70">
                                                        {item.material_name}
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-text-secondary">
                                                {item.material_type === 'DIVISIBLE' ? t('inventory.types.divisible') : t('inventory.types.indivisible')}
                                            </td>
                                            <td className="px-6 py-4 text-sm font-mono text-text-primary dir-ltr text-right">
                                                {item.standard_price?.toFixed(2) || '0.00'}
                                            </td>
                                            <td className="px-6 py-4 font-mono font-medium dir-ltr text-right">
                                                {item.packaging_ratio > 1 ? (
                                                    <div>
                                                        <span className="text-lg font-bold text-primary">
                                                            {Math.floor(item.total_quantity / item.packaging_ratio)}
                                                        </span>
                                                        <span className="text-xs text-text-secondary mx-1">{t('inventory.types.package')}</span>
                                                        <span className="block text-[10px] text-text-secondary opacity-70">
                                                            ({item.total_quantity} {item.unit})
                                                        </span>
                                                    </div>
                                                ) : (
                                                    <span>
                                                        {item.total_quantity} <span className="text-xs text-text-secondary">{item.unit}</span>
                                                    </span>
                                                )}
                                            </td>
                                            {/* Batches cell removed */}
                                            {/* Status */}
                                            <td className="px-6 py-4">
                                                {/* Existing alert logic can be simplified or kept */}
                                                {item.alert_status === 'OK' ? (
                                                    <span className="text-green-600 text-xs font-bold px-2 py-1 bg-green-100 rounded-full">{t('inventory.status.available')}</span>
                                                ) : (
                                                    <span className="text-amber-600 text-xs font-bold px-2 py-1 bg-amber-100 rounded-full">{t('inventory.status.low')}</span>
                                                )}
                                            </td>
                                            {/* Active Sessions Control */}
                                            <td className="px-6 py-4">
                                                <div className="flex gap-2">
                                                    {hasActiveSession ? (
                                                        // Case: Session Active -> Show Stop Button (Red)
                                                        <button
                                                            onClick={() => handleCloseSession(sessions[0])}
                                                            className="relative p-2 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg animate-pulse transition-colors"
                                                            title={sessions.length > 1 ? t('inventory.messages.open_packages_tooltip', { count: sessions.length }) : t('inventory.actions.close_package')}
                                                        >
                                                            <Square size={18} />
                                                            {sessions.length > 1 && (
                                                                <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[10px] text-white">
                                                                    {sessions.length}
                                                                </span>
                                                            )}
                                                        </button>
                                                    ) : (
                                                        // Case: No Session -> Show Start Button (Green)
                                                        <button
                                                            onClick={() => handleOpenSession(item)}
                                                            className="p-2 bg-green-50 text-green-600 hover:bg-green-100 rounded-lg transition-colors"
                                                            title={t('inventory.actions.open_package')}
                                                        >
                                                            <Play size={18} />
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                            {/* Smart Config & Actions */}
                                            <td className="px-6 py-4">
                                                <div className="flex gap-2">
                                                    {item.material_type === 'DIVISIBLE' && (
                                                        <button
                                                            onClick={() => setSmartMaterial({ id: item.material_id, name: item.material_name, unit: item.unit })}
                                                            title={t('inventory.actions.smart_settings')}
                                                            className="p-2 text-primary bg-primary/5 hover:bg-primary/20 rounded-lg transition-colors"
                                                        >
                                                            <Brain size={18} />
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => onEditMaterial && onEditMaterial(item)}
                                                        className="p-2 text-indigo-400 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition-colors"
                                                        title={t('inventory.actions.edit')}
                                                    >
                                                        <Edit size={18} />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(item.material_id, item.material_name)}
                                                        className="p-2 text-red-400 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors"
                                                        title={t('inventory.actions.delete')}
                                                    >
                                                        <Trash2 size={18} />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })
                            )}
                        </tbody>
                    </table>
                </div>
                {/* Pagination Controls */}
                {totalPages > 1 && (
                    <div className="flex justify-between items-center p-4 border-t border-border bg-background">
                        <span className="text-sm text-text-secondary">
                            {t('common.pagination.page')} {currentPage} {t('common.pagination.of')} {totalPages}
                        </span>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                disabled={currentPage === 1}
                                className="px-3 py-1 rounded-lg border border-border hover:bg-surface-hover disabled:opacity-50 transition-colors"
                            >
                                {t('common.pagination.previous')}
                            </button>
                            <button
                                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                disabled={currentPage === totalPages}
                                className="px-3 py-1 rounded-lg border border-border hover:bg-surface-hover disabled:opacity-50 transition-colors"
                            >
                                {t('common.pagination.next')}
                            </button>
                        </div>
                    </div>
                )}
            </div>
            <SmartLearningModal
                isOpen={!!smartMaterial}
                onClose={() => setSmartMaterial(null)}
                material={smartMaterial}
            />
            <MaterialDetailsModal
                isOpen={!!selectedMaterial}
                onClose={() => setSelectedMaterial(null)}
                material={selectedMaterial}
                activeSessions={activeSessions || []}
            />
            <TrackSessionModal
                isOpen={sessionModal.open}
                onClose={() => setSessionModal(prev => ({ ...prev, open: false }))}
                mode={sessionModal.mode}
                material={sessionModal.material}
                session={sessionModal.session}
            />
        </div>
    );
};
export default StockList;


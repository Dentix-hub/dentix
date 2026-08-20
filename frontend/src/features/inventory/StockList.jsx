import { useMemo, useState } from 'react';
import logger from '@/utils/logger';
import {
    Search,
    Plus,
    Package,
    ArrowDownLeft,
    Brain,
    Play,
    Square,
    Trash2,
    Edit,
    MoreHorizontal,
    Boxes,
    CircleDollarSign,
    ChevronDown
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getStockSummary, getActiveSessions, deleteMaterial } from '@/api/inventory';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { useTranslation } from 'react-i18next';
import SmartLearningModal from './components/SmartLearningModal';
import TrackSessionModal from './components/TrackSessionModal';
import MaterialDetailsModal from './components/MaterialDetailsModal';

const ITEMS_PER_PAGE = 25;

const StockList = ({ onAddMaterial, onReceiveStock, onEditMaterial }) => {
    const { t, i18n } = useTranslation();
    const queryClient = useQueryClient();
    const [searchQuery, setSearchQuery] = useState('');
    const [filter, setFilter] = useState('ALL');
    const [smartMaterial, setSmartMaterial] = useState(null);
    const [selectedMaterial, setSelectedMaterial] = useState(null);
    const [sessionModal, setSessionModal] = useState({ open: false, mode: 'OPEN', material: null, session: null });
    const [expandedActionsId, setExpandedActionsId] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);

    const { data: stockItems, isLoading, error } = useQuery({
        queryKey: ['inventory-stock'],
        queryFn: async () => {
            const res = await getStockSummary();
            return Array.isArray(res.data) ? res.data : [];
        },
        staleTime: 30 * 1000,
        retry: 1,
    });

    const { data: activeSessions } = useQuery({
        queryKey: ['active-sessions'],
        queryFn: async () => {
            const res = await getActiveSessions();
            return Array.isArray(res.data) ? res.data : [];
        },
        staleTime: 15 * 1000,
        retry: 1,
        refetchInterval: 30000,
    });

    const deleteMutation = useMutation({
        mutationFn: deleteMaterial,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['inventory-stock'] });
            alert(t('inventory.messages.delete_success'));
        },
        onError: (err) => {
            logger.error(err);
            const msg = err.response?.data?.detail
                || err.response?.data?.error?.message
                || t('inventory.messages.delete_fail');
            alert(msg);
        }
    });

    const activeSessionsMap = useMemo(() => {
        const map = {};
        const safeSessions = Array.isArray(activeSessions) ? activeSessions : [];
        safeSessions.forEach((session) => {
            const materialId = session.stock_item?.batch?.material_id;
            if (!materialId) return;
            if (!map[materialId]) map[materialId] = [];
            map[materialId].push(session);
        });
        return map;
    }, [activeSessions]);

    const filteredItems = useMemo(() => {
        const normalizedSearch = searchQuery.trim().toLowerCase();
        return (stockItems || []).filter((item) => {
            const searchable = `${item.material_name || ''} ${item.brand || ''} ${item.category_name_ar || ''} ${item.category_name_en || ''}`.toLowerCase();
            const matchesSearch = searchable.includes(normalizedSearch);
            if (filter === 'ALL') return matchesSearch;
            return matchesSearch && item.alert_status === filter;
        });
    }, [stockItems, searchQuery, filter]);

    const totalPages = Math.max(1, Math.ceil(filteredItems.length / ITEMS_PER_PAGE));
    const safeCurrentPage = Math.min(currentPage, totalPages);
    const paginatedItems = useMemo(() => {
        const start = (safeCurrentPage - 1) * ITEMS_PER_PAGE;
        return filteredItems.slice(start, start + ITEMS_PER_PAGE);
    }, [filteredItems, safeCurrentPage]);

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
            session
        });
    };

    const handleDelete = (id, name) => {
        if (window.confirm(t('inventory.messages.delete_confirm', { name }))) {
            deleteMutation.mutate(id);
        }
    };

    const getCategoryLabel = (item) => i18n.language === 'ar' ? item.category_name_ar : item.category_name_en;
    const getMaterialTypeLabel = (item) => item.material_type === 'DIVISIBLE'
        ? t('inventory.types.divisible')
        : t('inventory.types.indivisible');

    const renderQuantity = (item, compact = false) => {
        if (item.packaging_ratio > 1) {
            return (
                <span className="inline-flex flex-wrap items-baseline gap-x-1" dir="ltr">
                    <strong className={compact ? 'text-base text-primary' : 'text-lg text-primary'}>{Math.floor(item.total_quantity / item.packaging_ratio)}</strong>
                    <span className="text-xs text-text-secondary">{t('inventory.types.package')}</span>
                    <span className="text-[10px] text-text-muted">({item.total_quantity} {item.unit})</span>
                </span>
            );
        }
        return (
            <span dir="ltr">
                <strong>{item.total_quantity}</strong> <span className="text-xs text-text-secondary">{item.unit}</span>
            </span>
        );
    };

    const StatusBadge = ({ status }) => status === 'OK' ? (
        <span className="inline-flex min-h-7 items-center rounded-full bg-green-100 px-2.5 py-1 text-xs font-bold text-green-700 dark:bg-green-900/30 dark:text-green-300">
            {t('inventory.status.available')}
        </span>
    ) : (
        <span className="inline-flex min-h-7 items-center rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
            {t('inventory.status.low')}
        </span>
    );

    if (isLoading) return <LoadingSpinner />;
    if (error) return <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center text-red-600">{t('inventory.messages.load_error', 'حدث خطأ في تحميل البيانات')}</div>;

    return (
        <div className="min-w-0 space-y-4">
            <section className="min-w-0 rounded-2xl border border-border bg-surface p-3 shadow-sm sm:p-4">
                <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div className="relative w-full min-w-0 lg:max-w-md">
                        <Search className="pointer-events-none absolute end-3 top-1/2 -translate-y-1/2 text-text-secondary" size={20} aria-hidden="true" />
                        <input
                            type="search"
                            placeholder={t('inventory.actions.search_placeholder')}
                            value={searchQuery}
                            onChange={(event) => {
                                setSearchQuery(event.target.value);
                                setCurrentPage(1);
                            }}
                            className="min-h-11 w-full rounded-xl border border-border bg-background py-2.5 ps-3 pe-10 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20 sm:ps-4"
                        />
                    </div>

                    <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-3 lg:w-auto lg:grid-cols-[auto_auto_auto]">
                        <select
                            value={filter}
                            onChange={(event) => {
                                setFilter(event.target.value);
                                setCurrentPage(1);
                            }}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm font-bold outline-none focus:ring-2 focus:ring-primary/20 lg:w-auto"
                            aria-label={t('inventory.filters.label', 'Filter stock')}
                        >
                            <option value="ALL">{t('inventory.filters.all')}</option>
                            <option value="LOW">{t('inventory.filters.low')}</option>
                            <option value="CRITICAL">{t('inventory.filters.critical')}</option>
                        </select>
                        <button
                            type="button"
                            onClick={onReceiveStock}
                            className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-secondary/10 px-3 py-2 text-sm font-bold text-secondary transition-colors hover:bg-secondary/20 lg:w-auto"
                        >
                            <ArrowDownLeft size={18} aria-hidden="true" />
                            <span>{t('inventory.actions.receive_stock')}</span>
                        </button>
                        <button
                            type="button"
                            onClick={onAddMaterial}
                            className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary px-3 py-2 text-sm font-bold text-white shadow-low transition-colors hover:bg-primary-hover lg:w-auto"
                        >
                            <Plus size={18} aria-hidden="true" />
                            <span>{t('inventory.actions.new_material')}</span>
                        </button>
                    </div>
                </div>
            </section>

            <div className="grid gap-3 lg:hidden">
                {paginatedItems.length === 0 ? (
                    <div className="rounded-2xl border border-border bg-surface-elevated px-4 py-10 text-center text-text-secondary">
                        <Package size={44} className="mx-auto mb-2 opacity-20" aria-hidden="true" />
                        <p>{t('inventory.table.empty')}</p>
                    </div>
                ) : paginatedItems.map((item) => {
                    const sessions = activeSessionsMap[item.material_id] || [];
                    const hasActiveSession = sessions.length > 0;
                    const categoryLabel = getCategoryLabel(item);
                    const actionsExpanded = expandedActionsId === item.material_id;

                    return (
                        <article key={item.material_id} className="min-w-0 rounded-2xl border border-border bg-surface-elevated p-3 shadow-low sm:p-4">
                            <div className="flex min-w-0 items-start gap-3">
                                <button
                                    type="button"
                                    onClick={() => setSelectedMaterial(item)}
                                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors hover:bg-primary/15"
                                    aria-label={t('inventory.table.details_tooltip')}
                                >
                                    <Package size={20} aria-hidden="true" />
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setSelectedMaterial(item)}
                                    className="min-h-11 min-w-0 flex-1 text-start"
                                >
                                    <h3 className="break-words text-sm font-bold text-text-primary" dir="auto">
                                        {item.brand ? `${item.brand} - ` : ''}{item.material_name}
                                    </h3>
                                    {categoryLabel && categoryLabel !== item.material_name && (
                                        <p className="mt-0.5 truncate text-[11px] font-medium uppercase tracking-wide text-text-muted" dir="auto">{categoryLabel}</p>
                                    )}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setExpandedActionsId(actionsExpanded ? null : item.material_id)}
                                    className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary"
                                    aria-expanded={actionsExpanded}
                                    aria-label={t('inventory.actions.more', 'More material actions')}
                                >
                                    <MoreHorizontal size={20} aria-hidden="true" />
                                </button>
                            </div>

                            <div className="mt-3 grid grid-cols-2 gap-2">
                                <div className="min-w-0 rounded-xl bg-surface-subtle p-2.5">
                                    <div className="mb-1 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-text-muted">
                                        <Boxes size={13} aria-hidden="true" />
                                        {t('inventory.table.current_stock')}
                                    </div>
                                    <div className="min-w-0 font-mono text-sm text-text-primary">{renderQuantity(item, true)}</div>
                                </div>
                                <div className="min-w-0 rounded-xl bg-surface-subtle p-2.5">
                                    <div className="mb-1 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-text-muted">
                                        <CircleDollarSign size={13} aria-hidden="true" />
                                        {t('inventory.table.standard_price')}
                                    </div>
                                    <div className="font-mono text-sm font-bold text-text-primary" dir="ltr">{item.standard_price?.toFixed(2) || '0.00'}</div>
                                </div>
                            </div>

                            <div className="mt-3 flex flex-wrap items-center gap-2">
                                <StatusBadge status={item.alert_status} />
                                <span className="inline-flex min-h-7 items-center rounded-full bg-surface-subtle px-2.5 py-1 text-xs font-medium text-text-secondary">
                                    {getMaterialTypeLabel(item)}
                                </span>
                                {hasActiveSession && (
                                    <span className="inline-flex min-h-7 items-center rounded-full bg-red-50 px-2.5 py-1 text-xs font-bold text-red-600 dark:bg-red-900/20 dark:text-red-300">
                                        {sessions.length} {t('inventory.table.sessions')}
                                    </span>
                                )}
                            </div>

                            <div className="mt-3 grid grid-cols-[minmax(0,1fr)_2.75rem] gap-2">
                                {hasActiveSession ? (
                                    <button
                                        type="button"
                                        onClick={() => handleCloseSession(sessions[0])}
                                        className="inline-flex min-h-11 min-w-0 items-center justify-center gap-2 rounded-xl bg-red-50 px-3 py-2 text-sm font-bold text-red-600 transition-colors hover:bg-red-100 dark:bg-red-900/20 dark:text-red-300 dark:hover:bg-red-900/30"
                                    >
                                        <Square size={17} className="shrink-0" aria-hidden="true" />
                                        <span className="truncate">{t('inventory.actions.close_package')}</span>
                                    </button>
                                ) : (
                                    <button
                                        type="button"
                                        onClick={() => handleOpenSession(item)}
                                        className="inline-flex min-h-11 min-w-0 items-center justify-center gap-2 rounded-xl bg-green-50 px-3 py-2 text-sm font-bold text-green-700 transition-colors hover:bg-green-100 dark:bg-green-900/20 dark:text-green-300 dark:hover:bg-green-900/30"
                                    >
                                        <Play size={17} className="shrink-0" aria-hidden="true" />
                                        <span className="truncate">{t('inventory.actions.open_package')}</span>
                                    </button>
                                )}
                                <button
                                    type="button"
                                    onClick={() => setSelectedMaterial(item)}
                                    className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-border text-text-secondary transition-colors hover:bg-surface-hover hover:text-primary"
                                    aria-label={t('inventory.table.details_tooltip')}
                                >
                                    <ChevronDown size={18} aria-hidden="true" />
                                </button>
                            </div>

                            {actionsExpanded && (
                                <div className="mt-3 grid grid-cols-2 gap-2 border-t border-border pt-3 min-[420px]:grid-cols-3">
                                    {item.material_type === 'DIVISIBLE' && (
                                        <button
                                            type="button"
                                            onClick={() => setSmartMaterial({ id: item.material_id, name: item.material_name, unit: item.unit })}
                                            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary/5 px-3 py-2 text-xs font-bold text-primary transition-colors hover:bg-primary/10"
                                        >
                                            <Brain size={17} aria-hidden="true" />
                                            {t('inventory.actions.smart_settings')}
                                        </button>
                                    )}
                                    <button
                                        type="button"
                                        onClick={() => onEditMaterial?.(item)}
                                        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-indigo-50 px-3 py-2 text-xs font-bold text-indigo-600 transition-colors hover:bg-indigo-100 dark:bg-indigo-900/20 dark:text-indigo-300"
                                    >
                                        <Edit size={17} aria-hidden="true" />
                                        {t('inventory.actions.edit')}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => handleDelete(item.material_id, item.material_name)}
                                        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-red-50 px-3 py-2 text-xs font-bold text-red-600 transition-colors hover:bg-red-100 dark:bg-red-900/20 dark:text-red-300"
                                    >
                                        <Trash2 size={17} aria-hidden="true" />
                                        {t('inventory.actions.delete')}
                                    </button>
                                </div>
                            )}
                        </article>
                    );
                })}
            </div>

            <div className="hidden overflow-hidden rounded-2xl border border-border bg-surface shadow-sm lg:block">
                <div className="overflow-x-auto overscroll-x-contain">
                    <table className="w-full min-w-[900px] text-start">
                        <thead className="border-b border-border bg-background">
                            <tr>
                                <th className="px-5 py-4 text-start text-sm font-bold text-text-secondary">{t('inventory.table.material')}</th>
                                <th className="px-5 py-4 text-start text-sm font-bold text-text-secondary">{t('inventory.table.type')}</th>
                                <th className="px-5 py-4 text-start text-sm font-bold text-text-secondary">{t('inventory.table.standard_price')}</th>
                                <th className="px-5 py-4 text-start text-sm font-bold text-text-secondary">{t('inventory.table.current_stock')}</th>
                                <th className="px-5 py-4 text-start text-sm font-bold text-text-secondary">{t('inventory.table.status')}</th>
                                <th className="px-5 py-4 text-start text-sm font-bold text-text-secondary">{t('inventory.table.sessions')}</th>
                                <th className="px-5 py-4 text-start text-sm font-bold text-text-secondary">{t('inventory.table.actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {paginatedItems.length === 0 ? (
                                <tr>
                                    <td colSpan="7" className="px-6 py-12 text-center text-text-secondary">
                                        <Package size={48} className="mx-auto mb-2 opacity-20" aria-hidden="true" />
                                        <p>{t('inventory.table.empty')}</p>
                                    </td>
                                </tr>
                            ) : paginatedItems.map((item) => {
                                const sessions = activeSessionsMap[item.material_id] || [];
                                const hasActiveSession = sessions.length > 0;
                                const categoryLabel = getCategoryLabel(item);
                                return (
                                    <tr key={item.material_id} className="transition-colors hover:bg-surface-hover">
                                        <td className="px-5 py-4">
                                            <button
                                                type="button"
                                                onClick={() => setSelectedMaterial(item)}
                                                className="min-h-11 max-w-64 text-start transition-colors hover:text-primary"
                                                title={t('inventory.table.details_tooltip')}
                                            >
                                                <span className="block break-words text-base font-bold text-text-primary" dir="auto">
                                                    {item.brand ? `${item.brand} - ` : ''}{item.material_name}
                                                </span>
                                                {categoryLabel && categoryLabel !== item.material_name && (
                                                    <span className="mt-0.5 block truncate text-[10px] font-normal uppercase tracking-wider text-text-secondary opacity-70" dir="auto">{categoryLabel}</span>
                                                )}
                                            </button>
                                        </td>
                                        <td className="px-5 py-4 text-sm text-text-secondary">{getMaterialTypeLabel(item)}</td>
                                        <td className="px-5 py-4 text-start font-mono text-sm text-text-primary" dir="ltr">{item.standard_price?.toFixed(2) || '0.00'}</td>
                                        <td className="px-5 py-4 font-mono font-medium text-text-primary">{renderQuantity(item)}</td>
                                        <td className="px-5 py-4"><StatusBadge status={item.alert_status} /></td>
                                        <td className="px-5 py-4">
                                            {hasActiveSession ? (
                                                <button
                                                    type="button"
                                                    onClick={() => handleCloseSession(sessions[0])}
                                                    className="relative inline-flex h-11 min-w-11 items-center justify-center rounded-xl bg-red-50 px-3 text-red-600 transition-colors hover:bg-red-100 dark:bg-red-900/20 dark:text-red-300"
                                                    title={sessions.length > 1 ? t('inventory.messages.open_packages_tooltip', { count: sessions.length }) : t('inventory.actions.close_package')}
                                                >
                                                    <Square size={18} aria-hidden="true" />
                                                    {sessions.length > 1 && (
                                                        <span className="absolute -end-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] text-white">{sessions.length}</span>
                                                    )}
                                                </button>
                                            ) : (
                                                <button
                                                    type="button"
                                                    onClick={() => handleOpenSession(item)}
                                                    className="inline-flex h-11 min-w-11 items-center justify-center rounded-xl bg-green-50 px-3 text-green-600 transition-colors hover:bg-green-100 dark:bg-green-900/20 dark:text-green-300"
                                                    title={t('inventory.actions.open_package')}
                                                >
                                                    <Play size={18} aria-hidden="true" />
                                                </button>
                                            )}
                                        </td>
                                        <td className="px-5 py-4">
                                            <div className="flex flex-wrap gap-2">
                                                {item.material_type === 'DIVISIBLE' && (
                                                    <button
                                                        type="button"
                                                        onClick={() => setSmartMaterial({ id: item.material_id, name: item.material_name, unit: item.unit })}
                                                        title={t('inventory.actions.smart_settings')}
                                                        className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-primary/5 text-primary transition-colors hover:bg-primary/15"
                                                    >
                                                        <Brain size={18} aria-hidden="true" />
                                                    </button>
                                                )}
                                                <button
                                                    type="button"
                                                    onClick={() => onEditMaterial?.(item)}
                                                    className="inline-flex h-11 w-11 items-center justify-center rounded-xl text-indigo-500 transition-colors hover:bg-indigo-50 dark:hover:bg-indigo-900/20"
                                                    title={t('inventory.actions.edit')}
                                                >
                                                    <Edit size={18} aria-hidden="true" />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => handleDelete(item.material_id, item.material_name)}
                                                    className="inline-flex h-11 w-11 items-center justify-center rounded-xl text-red-500 transition-colors hover:bg-red-50 dark:hover:bg-red-900/20"
                                                    title={t('inventory.actions.delete')}
                                                >
                                                    <Trash2 size={18} aria-hidden="true" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {filteredItems.length > 0 && totalPages > 1 && (
                <nav className="flex min-w-0 flex-col gap-3 rounded-2xl border border-border bg-background p-3 sm:flex-row sm:items-center sm:justify-between sm:p-4" aria-label={t('common.pagination.label', 'Pagination')}>
                    <span className="text-center text-sm text-text-secondary sm:text-start">
                        {t('common.pagination.page')} {safeCurrentPage} {t('common.pagination.of')} {totalPages}
                    </span>
                    <div className="grid grid-cols-2 gap-2 sm:flex">
                        <button
                            type="button"
                            onClick={() => setCurrentPage(page => Math.max(1, page - 1))}
                            disabled={safeCurrentPage === 1}
                            className="min-h-11 rounded-xl border border-border px-3 py-2 text-sm font-bold transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {t('common.pagination.previous')}
                        </button>
                        <button
                            type="button"
                            onClick={() => setCurrentPage(page => Math.min(totalPages, page + 1))}
                            disabled={safeCurrentPage === totalPages}
                            className="min-h-11 rounded-xl border border-border px-3 py-2 text-sm font-bold transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {t('common.pagination.next')}
                        </button>
                    </div>
                </nav>
            )}

            {!!smartMaterial && (
                <SmartLearningModal
                    isOpen
                    onClose={() => setSmartMaterial(null)}
                    material={smartMaterial}
                />
            )}
            {!!selectedMaterial && (
                <MaterialDetailsModal
                    isOpen
                    onClose={() => setSelectedMaterial(null)}
                    material={selectedMaterial}
                    activeSessions={activeSessions || []}
                />
            )}
            {sessionModal.open && (
                <TrackSessionModal
                    isOpen
                    onClose={() => setSessionModal(prev => ({ ...prev, open: false }))}
                    mode={sessionModal.mode}
                    material={sessionModal.material}
                    session={sessionModal.session}
                />
            )}
        </div>
    );
};

export default StockList;

import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
    ArrowDownLeft,
    ArrowUpRight,
    Scale,
    ExternalLink,
} from 'lucide-react';
import { useFinancialActivity } from '../activity/hooks/useFinancialActivity';
import MetricCard from '../components/MetricCard';
import FilterBar from '../components/FilterBar';
import DataTable from '../components/DataTable';
import Money from '../components/Money';
import ActivityTypeBadge from '../activity/components/ActivityTypeBadge';

/**
 * Financial Activity V2 Page (§17 MASTER_SPEC).
 * The shared Finance header owns the period control; drill-down links preserve
 * that period and include stable source identifiers when available.
 */
export default function ActivityPage() {
    const { t } = useTranslation();

    const {
        events,
        totalCount,
        totalInflow,
        totalOutflow,
        netFlow,
        from,
        to,
        type,
        search,
        page,
        pageSize,
        isLoading,
        isError,
        refetch,
        updateType,
        updateSearch,
        setPage,
    } = useFinancialActivity(20);

    const typeFilterOptions = [
        { id: 'all', label: t('common.all', 'الكل'), count: null },
        { id: 'payment', label: t('finance.activity.type_payment', 'دفعات المرضى'), count: null },
        { id: 'expense', label: t('finance.activity.type_expense', 'مصروفات العيادة'), count: null },
        { id: 'lab', label: t('finance.activity.type_lab', 'المعامل'), count: null },
        { id: 'salary', label: t('finance.activity.type_salary', 'المرتبات'), count: null },
    ];

    const formatTimestamp = (ts) => {
        if (!ts) return '—';
        try {
            const date = new Date(ts);
            return {
                date: date.toLocaleDateString('ar-EG', { day: 'numeric', month: 'short', year: 'numeric' }),
                time: date.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' }),
            };
        } catch {
            return { date: ts, time: '' };
        }
    };

    const drillDownUrl = (row) => {
        if (!row?.nav_url) return null;
        const [pathname, existingSearch = ''] = String(row.nav_url).split('?');
        const params = new URLSearchParams(existingSearch);

        if (pathname.startsWith('/finance/')) {
            if (from && !params.has('from')) params.set('from', from);
            if (to && !params.has('to')) params.set('to', to);
        }

        if (row.source_type === 'payment') {
            if (row.patient_id && !params.has('patient_id')) {
                params.set('patient_id', String(row.patient_id));
            }
            if (row.source_id && !params.has('payment_id')) {
                params.set('payment_id', String(row.source_id));
            }
        }

        const query = params.toString();
        return query ? `${pathname}?${query}` : pathname;
    };

    const columns = [
        {
            id: 'time',
            header: t('finance.activity.timestamp', 'الوقت والتاريخ'),
            sortable: false,
            width: '160px',
            cell: (row) => {
                const formatted = formatTimestamp(row.timestamp);
                return (
                    <div className="space-y-0.5 text-xs font-mono">
                        <span className="block font-bold text-text-primary">{formatted.date}</span>
                        {formatted.time && (
                            <span className="block text-[11px] text-text-secondary">{formatted.time}</span>
                        )}
                    </div>
                );
            },
        },
        {
            id: 'source_type',
            header: t('common.type', 'النوع'),
            sortable: false,
            width: '150px',
            cell: (row) => (
                <ActivityTypeBadge sourceType={row.source_type} direction={row.direction} />
            ),
        },
        {
            id: 'title',
            header: t('finance.activity.subject', 'البيان / الطرف'),
            sortable: false,
            cell: (row) => {
                const navUrl = drillDownUrl(row);
                return (
                    <div className="space-y-0.5">
                        {navUrl ? (
                            <Link
                                to={navUrl}
                                className="group inline-flex items-center gap-1 font-bold text-text-primary transition-colors hover:text-primary"
                            >
                                <span>{row.title}</span>
                                <ExternalLink className="h-3 w-3 text-primary opacity-0 transition-opacity group-hover:opacity-100" />
                            </Link>
                        ) : (
                            <span className="block font-bold text-text-primary">{row.title}</span>
                        )}
                        {row.subtitle && (
                            <span className="block line-clamp-1 text-[11px] text-text-secondary">{row.subtitle}</span>
                        )}
                    </div>
                );
            },
        },
        {
            id: 'amount',
            header: t('finance.activity.movement', 'حركة المبلغ'),
            align: 'end',
            sortable: false,
            width: '160px',
            cell: (row) => {
                const isInflow = row.direction === 'inflow';
                return (
                    <div className="flex items-center justify-end gap-1 font-mono text-sm font-bold">
                        <span className={isInflow ? 'text-emerald-600 dark:text-emerald-400' : 'text-text-primary'}>
                            {isInflow ? '+' : '−'}
                        </span>
                        <Money amount={row.amount} size="sm" colored={isInflow} />
                    </div>
                );
            },
        },
    ];

    const renderMobileCard = (row) => {
        const formatted = formatTimestamp(row.timestamp);
        const isInflow = row.direction === 'inflow';
        const navUrl = drillDownUrl(row);

        return (
            <div key={row.id} className="space-y-3 rounded-xl border border-border bg-card p-4 shadow-xs">
                <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1">
                        <ActivityTypeBadge sourceType={row.source_type} direction={row.direction} />
                        <div>
                            {navUrl ? (
                                <Link
                                    to={navUrl}
                                    className="inline-flex items-center gap-1 text-sm font-bold text-text-primary hover:text-primary"
                                >
                                    <span>{row.title}</span>
                                    <ExternalLink className="h-3 w-3 text-text-secondary" />
                                </Link>
                            ) : (
                                <span className="block text-sm font-bold text-text-primary">{row.title}</span>
                            )}
                            {row.subtitle && (
                                <p className="line-clamp-1 text-[11px] text-text-secondary">{row.subtitle}</p>
                            )}
                        </div>
                    </div>

                    <div className="text-end font-mono">
                        <div className="flex items-center justify-end gap-0.5 text-sm font-bold">
                            <span className={isInflow ? 'text-emerald-600 dark:text-emerald-400' : 'text-text-primary'}>
                                {isInflow ? '+' : '−'}
                            </span>
                            <Money amount={row.amount} size="sm" colored={isInflow} />
                        </div>
                        <span className="mt-0.5 block text-[10px] text-text-secondary">{formatted.date}</span>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <MetricCard
                    title={t('finance.activity.total_inflow', 'إجمالي التدفقات الواردة')}
                    amount={totalInflow}
                    scope="period"
                    subtitle={t('finance.activity.inflow_sub', 'مجموع الدفعات النقدية المحصلة من المرضى')}
                    icon={ArrowDownLeft}
                    colored
                    isLoading={isLoading}
                />
                <MetricCard
                    title={t('finance.activity.total_outflow', 'إجمالي المدفوعات الصادرة')}
                    amount={totalOutflow}
                    scope="period"
                    subtitle={t('finance.activity.outflow_sub', 'مجموع المصروفات، المعامل، والرواتب المسددة')}
                    icon={ArrowUpRight}
                    isLoading={isLoading}
                />
                <MetricCard
                    title={t('finance.activity.net_flow', 'صافي الحركة المالية')}
                    amount={netFlow}
                    scope="period"
                    subtitle={t('finance.activity.net_sub', 'الفارق بين المقبوضات والمدفوعات للفترة')}
                    icon={Scale}
                    colored
                    isLoading={isLoading}
                />
            </div>

            <div className="space-y-3">
                <div className="flex max-w-full items-center gap-1 overflow-x-auto pb-1">
                    {typeFilterOptions.map((opt) => (
                        <button
                            key={opt.id}
                            type="button"
                            onClick={() => updateType(opt.id)}
                            className={`whitespace-nowrap rounded-xl px-3 py-1.5 text-xs font-bold transition-all ${
                                type === opt.id
                                    ? 'bg-primary text-white shadow-xs'
                                    : 'border border-border bg-card text-text-secondary hover:bg-muted/60 hover:text-text-primary'
                            }`}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>

                <FilterBar
                    searchValue={search}
                    onSearchChange={updateSearch}
                    searchPlaceholder={t('finance.activity.search_placeholder', 'البحث في البيان، اسم المريض، الموظف، أو الملاحظات...')}
                    filters={[]}
                    activeFilters={{}}
                    onFilterChange={() => {}}
                    onClearFilters={() => {
                        updateSearch('');
                        updateType('all');
                    }}
                />
            </div>

            <DataTable
                columns={columns}
                data={events}
                keyField="id"
                page={page}
                pageSize={pageSize}
                totalItems={totalCount}
                onPageChange={setPage}
                isLoading={isLoading}
                isError={isError}
                onRetry={refetch}
                renderMobileCard={renderMobileCard}
                emptyMessage={t('finance.activity.no_events', 'لا توجد حركات مالية مسجلة في هذا النطاق')}
            />
        </div>
    );
}

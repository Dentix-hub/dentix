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
import DateRangePicker from '../components/DateRangePicker';
import DataTable from '../components/DataTable';
import Money from '../components/Money';
import ActivityTypeBadge from '../activity/components/ActivityTypeBadge';

/**
 * Financial Activity V2 Page (§17 MASTER_SPEC).
 * Normalized read-only timeline of all clinic financial movements.
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
        updateDateRange,
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

    // Format Timestamp
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

    // Columns for Desktop View
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
                        <span className="font-bold text-text-primary block">{formatted.date}</span>
                        {formatted.time && (
                            <span className="text-[11px] text-text-secondary block">{formatted.time}</span>
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
                <ActivityTypeBadge
                    sourceType={row.source_type}
                    direction={row.direction}
                />
            ),
        },
        {
            id: 'title',
            header: t('finance.activity.subject', 'البيان / الطرف'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    {row.nav_url ? (
                        <Link
                            to={row.nav_url}
                            className="font-bold text-text-primary hover:text-primary transition-colors inline-flex items-center gap-1 group"
                        >
                            <span>{row.title}</span>
                            <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-primary" />
                        </Link>
                    ) : (
                        <span className="font-bold text-text-primary block">{row.title}</span>
                    )}
                    {row.subtitle && (
                        <span className="text-[11px] text-text-secondary block line-clamp-1">{row.subtitle}</span>
                    )}
                </div>
            ),
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
                    <div className="flex items-center justify-end gap-1 font-mono font-bold text-sm">
                        <span className={isInflow ? 'text-emerald-600 dark:text-emerald-400' : 'text-text-primary'}>
                            {isInflow ? '+' : '−'}
                        </span>
                        <Money
                            amount={row.amount}
                            size="sm"
                            colored={isInflow}
                        />
                    </div>
                );
            },
        },
    ];

    // Mobile Card View
    const renderMobileCard = (row) => {
        const formatted = formatTimestamp(row.timestamp);
        const isInflow = row.direction === 'inflow';

        return (
            <div
                key={row.id}
                className="p-4 rounded-xl border border-border bg-card space-y-3 shadow-xs"
            >
                <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1">
                        <ActivityTypeBadge
                            sourceType={row.source_type}
                            direction={row.direction}
                        />
                        <div>
                            {row.nav_url ? (
                                <Link
                                    to={row.nav_url}
                                    className="text-sm font-bold text-text-primary hover:text-primary inline-flex items-center gap-1"
                                >
                                    <span>{row.title}</span>
                                    <ExternalLink className="w-3 h-3 text-text-secondary" />
                                </Link>
                            ) : (
                                <span className="text-sm font-bold text-text-primary block">{row.title}</span>
                            )}
                            {row.subtitle && (
                                <p className="text-[11px] text-text-secondary line-clamp-1">{row.subtitle}</p>
                            )}
                        </div>
                    </div>

                    <div className="text-end font-mono">
                        <div className="flex items-center justify-end gap-0.5 font-bold text-sm">
                            <span className={isInflow ? 'text-emerald-600 dark:text-emerald-400' : 'text-text-primary'}>
                                {isInflow ? '+' : '−'}
                            </span>
                            <Money amount={row.amount} size="sm" colored={isInflow} />
                        </div>
                        <span className="text-[10px] text-text-secondary block mt-0.5">
                            {formatted.date}
                        </span>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="space-y-6">
            {/* Top Headline Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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

            {/* Filter Bar & Time Control */}
            <div className="space-y-3">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                    <DateRangePicker
                        value={{ from, to }}
                        onChange={updateDateRange}
                    />

                    {/* Source Type Filter Pills */}
                    <div className="flex items-center gap-1 overflow-x-auto pb-1 max-w-full">
                        {typeFilterOptions.map((opt) => (
                            <button
                                key={opt.id}
                                type="button"
                                onClick={() => updateType(opt.id)}
                                className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all ${
                                    type === opt.id
                                        ? 'bg-primary text-white shadow-xs'
                                        : 'bg-card border border-border text-text-secondary hover:text-text-primary hover:bg-muted/60'
                                }`}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
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

            {/* Data Table */}
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

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
    UserCheck,
    DollarSign,
    Settings,
    ArrowUpRight,
    TrendingUp,
} from 'lucide-react';
import { exportProvidersReport } from '@/api/financials';
import { useDoctorCompensation } from '../compensation/hooks/useDoctorCompensation';
import { useFinancePermissions } from '../useFinancePermissions';
import MetricCard from '../components/MetricCard';
import FilterBar from '../components/FilterBar';
import DateRangePicker from '../components/DateRangePicker';
import DataTable from '../components/DataTable';
import Money from '../components/Money';
import ExportCsvButton from '../components/ExportCsvButton';
import DoctorSettingsDrawer from '../compensation/components/DoctorSettingsDrawer';

/**
 * Doctor Compensation V2 Overview Page (§15 MASTER_SPEC).
 * Displays authoritative doctor dues, commission rates, and links to routed doctor detail page.
 * PR6 owns provider CSV here so the retired duplicate Providers report stays retired.
 */
export default function DoctorCompensationPage() {
    const { t, i18n } = useTranslation();
    const { canConfigFinance, canExportReports } = useFinancePermissions();

    const {
        doctors,
        totalDoctorDues,
        totalDoctorRevenue,
        totalDoctorCollected,
        from,
        to,
        search,
        isLoading,
        isError,
        refetch,
        updateDateRange,
        updateSearch,
        updateCompensation,
        isUpdating,
    } = useDoctorCompensation();

    const [doctorToConfigure, setDoctorToConfigure] = useState(null);
    const doctorDetailsUrl = (doctorId) => `/finance/team/doctors/${doctorId}?from=${from}&to=${to}`;
    const exportProviders = () => exportProvidersReport({
        start_date: from,
        end_date: to,
        ...(search.trim() ? { search: search.trim() } : {}),
        locale: i18n.language === 'ar' ? 'ar' : 'en',
    });

    const columns = [
        {
            id: 'doctor_name',
            header: t('finance.compensation.doctor_name', 'الطبيب'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <Link
                        to={doctorDetailsUrl(row.doctor_id)}
                        className="font-bold text-text-primary hover:text-primary transition-colors block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded-sm"
                    >
                        {row.doctor_name}
                    </Link>
                    <span className="text-[11px] text-text-secondary">
                        {row.treatments} {t('appointments.treatments_count', 'إجراء علاجي')}
                    </span>
                </div>
            ),
        },
        {
            id: 'revenue',
            header: t('finance.metrics.invoiced', 'المحتسب'),
            align: 'end',
            sortable: false,
            cell: (row) => <Money amount={row.revenue} size="sm" />,
        },
        {
            id: 'collected',
            header: t('finance.metrics.collected', 'المحصل'),
            align: 'end',
            sortable: false,
            cell: (row) => <Money amount={row.collected} size="sm" colored />,
        },
        {
            id: 'lab_cost',
            header: t('finance.expenses.lab_total', 'المعامل'),
            align: 'end',
            sortable: false,
            cell: (row) => <Money amount={row.lab_cost} size="sm" colored />,
        },
        {
            id: 'rules',
            header: t('finance.compensation.rule_summary', 'قاعدة الحساب'),
            sortable: false,
            width: '140px',
            cell: (row) => (
                <div className="space-y-0.5 text-xs">
                    <span className="font-semibold text-primary block">
                        {row.commission_percent}% {t('finance.compensation.commission_short', 'عمولة')}
                    </span>
                    {row.fixed_salary > 0 && (
                        <span className="text-[11px] text-text-secondary block font-mono">
                            + {row.fixed_salary} {t('common.egp', 'ج.م')}
                        </span>
                    )}
                </div>
            ),
        },
        {
            id: 'total_due',
            header: t('finance.compensation.total_due', 'المستحق للفترة'),
            align: 'end',
            sortable: false,
            cell: (row) => <Money amount={row.total_due} size="sm" colored />,
        },
        {
            id: 'actions',
            header: t('common.actions', 'إجراءات'),
            align: 'end',
            sortable: false,
            width: '100px',
            cell: (row) => {
                const editRulesLabel = t('finance.compensation.edit_rules', 'تعديل قواعد الأتعاب');
                const viewDetailsLabel = t('common.view_details', 'عرض التفاصيل');
                return (
                    <div className="flex items-center justify-end gap-1.5">
                        {canConfigFinance && (
                            <button
                                type="button"
                                onClick={() => setDoctorToConfigure(row)}
                                className="p-1.5 rounded-lg text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                                title={editRulesLabel}
                                aria-label={`${editRulesLabel}: ${row.doctor_name}`}
                            >
                                <Settings className="w-4 h-4" aria-hidden="true" />
                            </button>
                        )}
                        <Link
                            to={doctorDetailsUrl(row.doctor_id)}
                            className="p-1.5 rounded-lg text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                            title={viewDetailsLabel}
                            aria-label={`${viewDetailsLabel}: ${row.doctor_name}`}
                        >
                            <ArrowUpRight className="w-4 h-4" aria-hidden="true" />
                        </Link>
                    </div>
                );
            },
        },
    ];

    const renderMobileCard = (row) => (
        <div key={row.doctor_id} className="p-4 rounded-xl border border-border bg-card space-y-3 shadow-xs">
            <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                    <Link
                        to={doctorDetailsUrl(row.doctor_id)}
                        className="text-sm font-bold text-text-primary hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded-sm"
                    >
                        {row.doctor_name}
                    </Link>
                    <p className="text-[11px] text-text-secondary">
                        {row.treatments} {t('appointments.treatments_count', 'إجراء')} • {row.commission_percent}% {t('finance.compensation.commission_short', 'عمولة')}
                    </p>
                </div>
                <div className="text-end">
                    <span className="text-[10px] font-semibold text-text-secondary block">
                        {t('finance.compensation.total_due', 'المستحق')}
                    </span>
                    <Money amount={row.total_due} colored size="sm" />
                </div>
            </div>

            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border/40 text-[11px]">
                <div>
                    <span className="text-text-secondary block">{t('finance.metrics.invoiced', 'المحتسب')}</span>
                    <Money amount={row.revenue} size="xs" />
                </div>
                <div>
                    <span className="text-text-secondary block">{t('finance.metrics.collected', 'المحصل')}</span>
                    <Money amount={row.collected} colored size="xs" />
                </div>
                <div className="text-end">
                    <span className="text-text-secondary block">{t('finance.expenses.lab_total', 'المعامل')}</span>
                    <Money amount={row.lab_cost} colored size="xs" />
                </div>
            </div>

            <div className="pt-2 border-t border-border/40 flex items-center justify-between">
                {canConfigFinance ? (
                    <button
                        type="button"
                        onClick={() => setDoctorToConfigure(row)}
                        className="text-xs font-semibold text-primary hover:underline flex items-center gap-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded-sm"
                    >
                        <Settings className="w-3.5 h-3.5" aria-hidden="true" />
                        <span>{t('finance.compensation.edit_rules', 'تعديل القواعد')}</span>
                    </button>
                ) : <span />}
                <Link
                    to={doctorDetailsUrl(row.doctor_id)}
                    className="text-xs font-bold text-primary hover:underline flex items-center gap-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded-sm"
                >
                    <span>{t('common.details', 'التفاصيل')}</span>
                    <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
                </Link>
            </div>
        </div>
    );

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard
                    title={t('finance.obligations.doctor_dues', 'إجمالي مستحقات الأطباء')}
                    amount={totalDoctorDues}
                    scope="period"
                    subtitle={t('finance.compensation.dues_sub', 'مجموع العمولات المحتسبة والرواتب لجميع الأطباء')}
                    icon={UserCheck}
                    colored
                    isLoading={isLoading}
                />
                <MetricCard
                    title={t('finance.compensation.total_production', 'إنتاجية الأطباء الإجمالية')}
                    amount={totalDoctorRevenue}
                    scope="period"
                    subtitle={t('finance.compensation.production_sub', 'إجمالي قيمة الخدمات العلاجية المنفذة')}
                    icon={TrendingUp}
                    isLoading={isLoading}
                />
                <MetricCard
                    title={t('finance.compensation.total_collected', 'المحصل منسوباً للأطباء')}
                    amount={totalDoctorCollected}
                    scope="period"
                    subtitle={t('finance.compensation.collected_sub', 'إجمالي الدفعات المحصلة من حالات الأطباء')}
                    icon={DollarSign}
                    colored
                    isLoading={isLoading}
                />
            </div>

            <div className="space-y-3">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                    <DateRangePicker value={{ from, to }} onChange={updateDateRange} />
                    {canExportReports && (
                        <ExportCsvButton
                            onExport={exportProviders}
                            filename="finance-providers.csv"
                            disabled={isLoading || isError || doctors.length === 0}
                            label={t('finance.reports.export_providers', 'تصدير الأطباء')}
                        />
                    )}
                </div>
                <FilterBar
                    searchValue={search}
                    onSearchChange={updateSearch}
                    searchPlaceholder={t('finance.compensation.search_placeholder', 'البحث باسم الطبيب...')}
                    filters={[]}
                    activeFilters={{}}
                    onFilterChange={() => {}}
                    onClearFilters={() => updateSearch('')}
                />
            </div>

            <DataTable
                columns={columns}
                data={doctors}
                keyField="doctor_id"
                isLoading={isLoading}
                isError={isError}
                onRetry={refetch}
                renderMobileCard={renderMobileCard}
                emptyMessage={t('finance.compensation.no_doctors', 'لا يوجد أطباء مسجلون في هذه الفترة')}
            />

            <DoctorSettingsDrawer
                doctor={doctorToConfigure}
                isOpen={Boolean(doctorToConfigure)}
                onClose={() => setDoctorToConfigure(null)}
                onSave={async (data) => {
                    await updateCompensation({
                        doctorId: doctorToConfigure.doctor_id,
                        data,
                    });
                    setDoctorToConfigure(null);
                }}
                isSaving={isUpdating}
            />
        </div>
    );
}

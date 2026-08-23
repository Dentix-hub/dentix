import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
    LayoutDashboard,
    Users,
    CreditCard,
    UserCheck,
    LineChart,
    ArrowLeft,
    ArrowRight,
    Download,
    RefreshCw,
    AlertTriangle,
    Search,
    ShieldCheck,
} from 'lucide-react';

import {
    exportMaterialMarginReport,
    exportPeriodComparisonReport,
} from '@/api/financials';
import Money from '../components/Money';
import { useFinancePermissions } from '../useFinancePermissions';
import { useReportInsights } from '../reports/hooks/useReportInsights';

function sharedPeriodSearch(search) {
    const current = new URLSearchParams(search);
    const next = new URLSearchParams();
    ['from', 'to', 'preset'].forEach((key) => {
        const value = current.get(key);
        if (value) next.set(key, value);
    });
    return next.toString();
}

function saveBlob(response, fallbackName) {
    const blob = response?.data;
    if (!(blob instanceof Blob)) throw new Error('Export response is not a file');
    const disposition = response.headers?.['content-disposition'] || '';
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const filename = match?.[1] || fallbackName;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
}

const METRIC_LABELS = {
    net_invoiced: 'صافي المحتسب',
    collected: 'التحصيلات',
    manual_expenses: 'المصروفات التشغيلية',
    lab_costs: 'تكاليف المعامل',
    doctor_dues: 'مستحقات الأطباء',
    staff_dues: 'مستحقات الموظفين',
    total_deductions: 'إجمالي الاستقطاعات',
    net_operational_result: 'صافي النتيجة التشغيلية',
};

function ReliabilityBadge({ status, confidence, t }) {
    const statusLabel = {
        complete: t('finance.reports.complete', 'مكتمل'),
        partial: t('finance.reports.partial', 'جزئي'),
        unavailable: t('finance.reports.unavailable', 'غير متاح'),
        error: t('common.error', 'خطأ'),
    }[status] || status;
    const confidenceLabel = {
        high: t('finance.reports.confidence_high', 'ثقة مرتفعة'),
        medium: t('finance.reports.confidence_medium', 'ثقة متوسطة'),
        low: t('finance.reports.confidence_low', 'ثقة منخفضة'),
        unavailable: t('finance.reports.confidence_unavailable', 'الثقة غير متاحة'),
    }[confidence] || confidence;

    return (
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-semibold">
            <span className="rounded-full border border-border bg-muted/40 px-2 py-1 text-text-primary">
                {statusLabel}
            </span>
            <span className="text-text-secondary">{confidenceLabel}</span>
        </div>
    );
}

/**
 * PR6 Reports & Insights workspace.
 * Analytical values are server-owned; this page never recreates authoritative
 * Finance formulas or downloads all report pages into the browser.
 */
export default function ReportsPage() {
    const { t, i18n } = useTranslation();
    const location = useLocation();
    const isRtl = i18n.language === 'ar';
    const locale = isRtl ? 'ar' : 'en';
    const [exporting, setExporting] = useState(null);
    const [exportError, setExportError] = useState('');
    const {
        canViewOverview,
        canViewPatientAccounts,
        canViewPayments,
        canViewExpenses,
        canViewActivity,
        canViewPayroll,
        canExportReports,
        isDoctor,
    } = useFinancePermissions();
    const {
        from,
        to,
        search,
        sort,
        page,
        pageSize,
        comparisonQuery,
        materialQuery,
        setSearch,
        setSort,
        setPage,
    } = useReportInsights();

    const periodSearch = sharedPeriodSearch(location.search);
    const withPeriod = (pathname) => ({
        pathname,
        search: periodSearch ? `?${periodSearch}` : '',
    });

    const sources = [
        {
            id: 'overview',
            title: t('finance.reports.source_overview', 'الملخص المالي المعتمد'),
            to: withPeriod('/finance/overview'),
            icon: LayoutDashboard,
            visible: canViewOverview,
        },
        {
            id: 'receivables',
            title: t('finance.reports.source_receivables', 'حسابات المرضى والذمم'),
            to: withPeriod('/finance/patient-accounts'),
            icon: Users,
            visible: canViewPatientAccounts,
        },
        {
            id: 'cash',
            title: t('finance.reports.source_cash', 'الحركات النقدية'),
            to: withPeriod('/finance/cash-movements'),
            icon: CreditCard,
            visible: canViewPayments || canViewExpenses || canViewActivity,
        },
        {
            id: 'team',
            title: t('finance.reports.source_team', 'الفريق والمستحقات'),
            to: withPeriod('/finance/team'),
            icon: UserCheck,
            visible: canViewPayroll || isDoctor,
        },
    ].filter((item) => item.visible);

    const comparison = comparisonQuery.data;
    const comparisonRows = comparison?.metrics || [];
    const material = materialQuery.data;
    const materialRows = material?.items || [];
    const pagination = material?.pagination || {};
    const totalPages = Math.max(1, Math.ceil((pagination.total || 0) / pageSize));
    const DirectionIcon = isRtl ? ArrowLeft : ArrowRight;

    const exportComparison = async () => {
        setExportError('');
        setExporting('comparison');
        try {
            const response = await exportPeriodComparisonReport({
                start_date: from,
                end_date: to,
                locale,
            });
            saveBlob(response, 'finance-period-comparison.csv');
        } catch {
            setExportError(t('finance.reports.export_failed', 'تعذر تصدير التقرير. حاول مرة أخرى.'));
        } finally {
            setExporting(null);
        }
    };

    const exportMaterials = async () => {
        setExportError('');
        setExporting('materials');
        try {
            const response = await exportMaterialMarginReport({
                search: search || undefined,
                sort,
                locale,
            });
            saveBlob(response, 'finance-material-margin.csv');
        } catch {
            setExportError(t('finance.reports.export_failed', 'تعذر تصدير التقرير. حاول مرة أخرى.'));
        } finally {
            setExporting(null);
        }
    };

    const comparisonExportDisabled =
        !canExportReports ||
        comparisonQuery.isLoading ||
        comparisonQuery.isError ||
        !comparisonQuery.isSuccess ||
        comparisonRows.length === 0 ||
        Boolean(exporting);
    const materialExportDisabled =
        !canExportReports ||
        materialQuery.isLoading ||
        materialQuery.isError ||
        !materialQuery.isSuccess ||
        materialRows.length === 0 ||
        Boolean(exporting);

    return (
        <div className="space-y-8" data-testid="reports-insights-workspace">
            <section className="space-y-2">
                <div className="flex items-center gap-2 text-primary">
                    <LineChart className="h-5 w-5" aria-hidden="true" />
                    <h2 className="text-lg font-bold text-text-primary sm:text-xl">
                        {t('finance.reports.insights_title', 'التقارير والرؤى')}
                    </h2>
                </div>
                <p className="max-w-3xl text-sm leading-6 text-text-secondary">
                    {t(
                        'finance.reports.insights_desc_pr6',
                        'تحليل مقارن مبني على مصدر الحقيقة المالي، وهامش مواد تقديري يظهر فقط عندما تكون بيانات التكلفة والاستخدام قابلة للدفاع عنها.',
                    )}
                </p>
                {exportError && (
                    <p role="alert" className="text-sm font-semibold text-destructive">
                        {exportError}
                    </p>
                )}
            </section>

            <section className="space-y-4 rounded-2xl border border-border bg-card p-4 sm:p-5" data-testid="period-comparison-report">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="space-y-1">
                        <h3 className="text-base font-bold text-text-primary">
                            {t('finance.reports.period_comparison', 'مقارنة الفترة')}
                        </h3>
                        <p className="text-xs text-text-secondary">
                            {comparison
                                ? `${comparison.current_period?.start} → ${comparison.current_period?.end} · ${t('finance.reports.vs', 'مقابل')} ${comparison.comparison_period?.start} → ${comparison.comparison_period?.end}`
                                : t('finance.reports.previous_equal_period', 'تتم المقارنة تلقائيًا بالفترة السابقة المساوية في الطول.')}
                        </p>
                    </div>
                    {canExportReports && (
                        <button
                            type="button"
                            onClick={exportComparison}
                            disabled={comparisonExportDisabled}
                            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-border px-3 py-2 text-xs font-bold text-text-primary transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            <Download className="h-4 w-4" aria-hidden="true" />
                            {exporting === 'comparison'
                                ? t('common.loading', 'جاري التحميل...')
                                : t('finance.reports.export_csv', 'تصدير CSV')}
                        </button>
                    )}
                </div>

                {comparisonQuery.isLoading ? (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label={t('common.loading', 'جاري التحميل')}>
                        {Array.from({ length: 8 }).map((_, index) => (
                            <div key={index} className="h-28 animate-pulse rounded-xl bg-muted/50" />
                        ))}
                    </div>
                ) : comparisonQuery.isError ? (
                    <div className="flex flex-col items-start gap-3 rounded-xl border border-destructive/20 bg-destructive/5 p-4">
                        <p className="text-sm font-semibold text-destructive">
                            {t('finance.reports.comparison_error', 'تعذر تحميل مقارنة الفترة، ولا يتم عرض قيم بديلة.')}
                        </p>
                        <button type="button" onClick={() => comparisonQuery.refetch()} className="inline-flex items-center gap-2 text-xs font-bold text-primary">
                            <RefreshCw className="h-4 w-4" />
                            {t('common.retry', 'إعادة المحاولة')}
                        </button>
                    </div>
                ) : comparisonRows.length === 0 ? (
                    <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-text-secondary">
                        {t('finance.reports.no_comparison_data', 'لا توجد بيانات مقارنة متاحة لهذه الفترة.')}
                    </p>
                ) : (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                        {comparisonRows.map((row) => (
                            <article key={row.metric} className="space-y-3 rounded-xl border border-border bg-background/50 p-4">
                                <h4 className="text-xs font-bold text-text-secondary">
                                    {t(`finance.reports.metric_${row.metric}`, METRIC_LABELS[row.metric] || row.metric)}
                                </h4>
                                <Money amount={row.current} size="lg" maximumFractionDigits={2} />
                                <div className="space-y-1 border-t border-border/50 pt-2 text-[11px] text-text-secondary">
                                    <div className="flex justify-between gap-2">
                                        <span>{t('finance.reports.previous_period', 'الفترة السابقة')}</span>
                                        <Money amount={row.comparison} size="xs" maximumFractionDigits={2} />
                                    </div>
                                    <div className="flex justify-between gap-2">
                                        <span>{t('finance.reports.change', 'التغير')}</span>
                                        <span className="font-mono font-bold text-text-primary" dir="ltr">
                                            {row.delta_percent === null ? '—' : `${row.delta_percent > 0 ? '+' : ''}${row.delta_percent}%`}
                                        </span>
                                    </div>
                                </div>
                            </article>
                        ))}
                    </div>
                )}
            </section>

            <section className="space-y-4 rounded-2xl border border-border bg-card p-4 sm:p-5" data-testid="material-margin-report">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-1">
                        <h3 className="text-base font-bold text-text-primary">
                            {t('finance.reports.material_margin', 'هامش المواد التقديري')}
                        </h3>
                        <p className="max-w-2xl text-xs leading-5 text-text-secondary">
                            {t(
                                'finance.reports.material_margin_scope',
                                'هذا المؤشر يقارن سعر الإجراء بتكلفة المواد فقط؛ لا يدّعي احتساب الخصومات أو المعامل أو أتعاب الأطباء أو تكاليف التشغيل.',
                            )}
                        </p>
                    </div>
                    {canExportReports && (
                        <button
                            type="button"
                            onClick={exportMaterials}
                            disabled={materialExportDisabled}
                            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-border px-3 py-2 text-xs font-bold text-text-primary transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
                            title={t('finance.reports.export_all_filtered', 'يصدر جميع النتائج المطابقة للفلاتر من الخادم')}
                        >
                            <Download className="h-4 w-4" aria-hidden="true" />
                            {exporting === 'materials'
                                ? t('common.loading', 'جاري التحميل...')
                                : t('finance.reports.export_filtered_csv', 'تصدير النتائج المفلترة')}
                        </button>
                    )}
                </div>

                <div className="flex flex-col gap-3 sm:flex-row">
                    <label className="relative min-w-0 flex-1">
                        <span className="sr-only">{t('common.search', 'بحث')}</span>
                        <Search className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-secondary" />
                        <input
                            value={search}
                            onChange={(event) => setSearch(event.target.value)}
                            placeholder={t('finance.reports.search_procedure', 'بحث باسم الإجراء...')}
                            className="min-h-11 w-full rounded-xl border border-border bg-background ps-10 pe-3 text-sm text-text-primary outline-none focus:border-primary"
                        />
                    </label>
                    <select
                        value={sort}
                        onChange={(event) => setSort(event.target.value)}
                        aria-label={t('common.sort', 'ترتيب')}
                        className="min-h-11 rounded-xl border border-border bg-background px-3 text-sm text-text-primary"
                    >
                        <option value="name_asc">{t('finance.reports.sort_name_asc', 'الاسم: أ → ي')}</option>
                        <option value="name_desc">{t('finance.reports.sort_name_desc', 'الاسم: ي → أ')}</option>
                        <option value="price_asc">{t('finance.reports.sort_price_asc', 'السعر: الأقل أولًا')}</option>
                        <option value="price_desc">{t('finance.reports.sort_price_desc', 'السعر: الأعلى أولًا')}</option>
                    </select>
                </div>

                {material?.warning && (
                    <div className="flex items-start gap-2 rounded-xl border border-amber-300/50 bg-amber-50/60 p-3 text-xs text-amber-900 dark:bg-amber-950/20 dark:text-amber-200" role="status">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                        <div className="space-y-1">
                            <p className="font-bold">
                                {t('finance.reports.incomplete_material_warning', 'بعض الإجراءات لا تملك بيانات تكلفة/استخدام مكتملة؛ تم حجب الهامش بدل افتراض تكلفة صفرية.')}
                            </p>
                            <p>
                                {t('finance.reports.current_page_completeness', 'اكتمال الصفحة الحالية')}: {material.completeness?.coverage_percent ?? 0}% · {t('common.error', 'أخطاء')}: {material.completeness?.errors ?? 0}
                            </p>
                        </div>
                    </div>
                )}

                {materialQuery.isLoading ? (
                    <div className="space-y-2" aria-label={t('common.loading', 'جاري التحميل')}>
                        {Array.from({ length: 5 }).map((_, index) => (
                            <div key={index} className="h-16 animate-pulse rounded-xl bg-muted/50" />
                        ))}
                    </div>
                ) : materialQuery.isError ? (
                    <div className="flex flex-col items-start gap-3 rounded-xl border border-destructive/20 bg-destructive/5 p-4">
                        <p className="text-sm font-semibold text-destructive">
                            {t('finance.reports.material_error', 'تعذر تحميل هامش المواد، ولا يتم عرض أصفار بديلة.')}
                        </p>
                        <button type="button" onClick={() => materialQuery.refetch()} className="inline-flex items-center gap-2 text-xs font-bold text-primary">
                            <RefreshCw className="h-4 w-4" />
                            {t('common.retry', 'إعادة المحاولة')}
                        </button>
                    </div>
                ) : materialRows.length === 0 ? (
                    <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-text-secondary">
                        {t('finance.reports.no_material_rows', 'لا توجد إجراءات مطابقة للفلاتر الحالية.')}
                    </p>
                ) : (
                    <>
                        <div className="hidden overflow-x-auto md:block">
                            <table className="w-full min-w-[760px] text-sm">
                                <thead>
                                    <tr className="border-b border-border text-start text-xs text-text-secondary">
                                        <th className="px-3 py-3 text-start">{t('finance.reports.procedure', 'الإجراء')}</th>
                                        <th className="px-3 py-3 text-end">{t('finance.reports.price', 'السعر')}</th>
                                        <th className="px-3 py-3 text-end">{t('finance.reports.material_cost', 'تكلفة المواد')}</th>
                                        <th className="px-3 py-3 text-end">{t('finance.reports.margin', 'الهامش')}</th>
                                        <th className="px-3 py-3 text-start">{t('finance.reports.coverage_confidence', 'الاكتمال / الثقة')}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {materialRows.map((row) => (
                                        <tr key={row.procedure_id} className="border-b border-border/60 last:border-0">
                                            <td className="px-3 py-3 font-bold text-text-primary">{row.procedure_name}</td>
                                            <td className="px-3 py-3 text-end"><Money amount={row.current_price} size="sm" /></td>
                                            <td className="px-3 py-3 text-end">
                                                {row.material_cost === null ? <span className="text-xs font-semibold text-text-secondary">{t('finance.reports.not_available', 'غير متاح')}</span> : <Money amount={row.material_cost} size="sm" />}
                                            </td>
                                            <td className="px-3 py-3 text-end">
                                                {row.material_margin === null ? (
                                                    <span className="text-xs font-semibold text-text-secondary">{t('finance.reports.not_available', 'غير متاح')}</span>
                                                ) : (
                                                    <div className="space-y-0.5">
                                                        <Money amount={row.material_margin} size="sm" />
                                                        <span className="block text-[11px] text-text-secondary" dir="ltr">{row.margin_percent}%</span>
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-3 py-3">
                                                <div className="space-y-1">
                                                    <span className="text-[11px] font-mono text-text-secondary" dir="ltr">{row.coverage_percent}%</span>
                                                    <ReliabilityBadge status={row.status} confidence={row.confidence} t={t} />
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="space-y-3 md:hidden">
                            {materialRows.map((row) => (
                                <article key={row.procedure_id} className="space-y-3 rounded-xl border border-border p-4">
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <h4 className="text-sm font-bold text-text-primary">{row.procedure_name}</h4>
                                            <ReliabilityBadge status={row.status} confidence={row.confidence} t={t} />
                                        </div>
                                        <Money amount={row.current_price} size="sm" />
                                    </div>
                                    <div className="grid grid-cols-2 gap-3 border-t border-border/50 pt-3 text-xs">
                                        <div>
                                            <span className="block text-text-secondary">{t('finance.reports.material_cost', 'تكلفة المواد')}</span>
                                            {row.material_cost === null ? <strong>{t('finance.reports.not_available', 'غير متاح')}</strong> : <Money amount={row.material_cost} size="xs" />}
                                        </div>
                                        <div>
                                            <span className="block text-text-secondary">{t('finance.reports.margin', 'الهامش')}</span>
                                            {row.material_margin === null ? <strong>{t('finance.reports.not_available', 'غير متاح')}</strong> : <Money amount={row.material_margin} size="xs" />}
                                        </div>
                                    </div>
                                    <p className="text-[11px] text-text-secondary">
                                        {t('finance.reports.coverage', 'الاكتمال')}: <span dir="ltr">{row.coverage_percent}%</span>
                                    </p>
                                </article>
                            ))}
                        </div>

                        <div className="flex flex-col gap-3 border-t border-border pt-4 text-xs sm:flex-row sm:items-center sm:justify-between">
                            <span className="text-text-secondary">
                                {t('finance.reports.pagination_summary', 'النتائج')}: {pagination.total || 0} · {t('common.page', 'صفحة')} {page} / {totalPages}
                            </span>
                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    disabled={page <= 1 || materialQuery.isFetching}
                                    onClick={() => setPage(page - 1)}
                                    className="min-h-10 rounded-xl border border-border px-3 font-bold disabled:opacity-40"
                                >
                                    {t('common.previous', 'السابق')}
                                </button>
                                <button
                                    type="button"
                                    disabled={page >= totalPages || materialQuery.isFetching}
                                    onClick={() => setPage(page + 1)}
                                    className="min-h-10 rounded-xl border border-border px-3 font-bold disabled:opacity-40"
                                >
                                    {t('common.next', 'التالي')}
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </section>

            <section className="space-y-3" aria-label={t('finance.reports.canonical_sources', 'مصادر البيانات المالية المعتمدة')}>
                <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-bold text-text-primary">
                        {t('finance.reports.operational_sources', 'المصادر التشغيلية الأصلية')}
                    </h3>
                </div>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
                    {sources.map((source) => {
                        const Icon = source.icon;
                        return (
                            <Link key={source.id} to={source.to} className="group flex min-h-24 items-center justify-between gap-3 rounded-xl border border-border bg-card p-4 hover:border-primary/30">
                                <div className="flex min-w-0 items-center gap-3">
                                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                                        <Icon className="h-4 w-4" />
                                    </div>
                                    <span className="min-w-0 text-sm font-bold text-text-primary">{source.title}</span>
                                </div>
                                <DirectionIcon className="h-4 w-4 shrink-0 text-primary" />
                            </Link>
                        );
                    })}
                </div>
            </section>
        </div>
    );
}

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
    ShieldCheck,
} from 'lucide-react';
import { useFinancePermissions } from '../useFinancePermissions';

function sharedPeriodSearch(search) {
    const current = new URLSearchParams(search);
    const next = new URLSearchParams();
    ['from', 'to', 'preset'].forEach((key) => {
        const value = current.get(key);
        if (value) next.set(key, value);
    });
    return next.toString();
}

/**
 * Reports & Insights destination after PR5 information-architecture cleanup.
 *
 * Operational copies of Summary, Collections, Expenses and Providers were
 * intentionally removed here. Those domains now have one live source/view.
 * Server-backed comparative reports, hardened export and material-margin
 * coverage metadata are added in PR6; this route must not recreate them in the
 * browser while those contracts are incomplete.
 */
export default function ReportsPage() {
    const { t, i18n } = useTranslation();
    const location = useLocation();
    const isRtl = i18n.language === 'ar';
    const {
        canViewOverview,
        canViewPatientAccounts,
        canViewPayments,
        canViewExpenses,
        canViewActivity,
        canViewPayroll,
        isDoctor,
    } = useFinancePermissions();

    const periodSearch = sharedPeriodSearch(location.search);
    const withPeriod = (pathname) => ({
        pathname,
        search: periodSearch ? `?${periodSearch}` : '',
    });

    const sources = [
        {
            id: 'overview',
            title: t('finance.reports.source_overview', 'الملخص المالي المعتمد'),
            description: t(
                'finance.reports.source_overview_desc',
                'المؤشرات المشتركة والنتيجة النقدية التشغيلية من مصدر الحقيقة المالي نفسه.',
            ),
            to: withPeriod('/finance/overview'),
            icon: LayoutDashboard,
            visible: canViewOverview,
        },
        {
            id: 'receivables',
            title: t('finance.reports.source_receivables', 'التحصيلات والذمم'),
            description: t(
                'finance.reports.source_receivables_desc',
                'الذمم التاريخية وكشف حساب المريض من شاشة حسابات المرضى الأصلية.',
            ),
            to: withPeriod('/finance/patient-accounts'),
            icon: Users,
            visible: canViewPatientAccounts,
        },
        {
            id: 'cash',
            title: t('finance.reports.source_cash', 'الحركات النقدية'),
            description: t(
                'finance.reports.source_cash_desc',
                'التحصيلات والمصروفات وسجل الحركة الموحد دون نسخة تقرير مكررة.',
            ),
            to: withPeriod('/finance/cash-movements'),
            icon: CreditCard,
            visible: canViewPayments || canViewExpenses || canViewActivity,
        },
        {
            id: 'team',
            title: t('finance.reports.source_team', 'الفريق والمستحقات'),
            description: t(
                'finance.reports.source_team_desc',
                'مستحقات الأطباء والرواتب من العقود المعتمدة في شاشة الفريق.',
            ),
            to: withPeriod('/finance/team'),
            icon: UserCheck,
            visible: canViewPayroll || isDoctor,
        },
    ].filter((item) => item.visible);

    const DirectionIcon = isRtl ? ArrowLeft : ArrowRight;

    return (
        <div className="space-y-6" data-testid="reports-insights-hub">
            <section className="space-y-2">
                <div className="flex items-center gap-2 text-primary">
                    <LineChart className="h-5 w-5" aria-hidden="true" />
                    <h2 className="text-lg font-bold text-text-primary sm:text-xl">
                        {t('finance.reports.insights_title', 'التقارير والرؤى')}
                    </h2>
                </div>
                <p className="max-w-3xl text-sm leading-6 text-text-secondary">
                    {t(
                        'finance.reports.insights_desc',
                        'تم توحيد التقارير التشغيلية مع صفحاتها الأصلية حتى لا توجد نسختان من نفس الرقم أو طلبات بيانات مكررة. استخدم المصادر أدناه للتحقيق التشغيلي.',
                    )}
                </p>
            </section>

            <section className="grid grid-cols-1 gap-4 md:grid-cols-2" aria-label={t('finance.reports.canonical_sources', 'مصادر البيانات المالية المعتمدة')}>
                {sources.map((source) => {
                    const Icon = source.icon;
                    return (
                        <Link
                            key={source.id}
                            to={source.to}
                            className="group flex min-h-36 flex-col justify-between rounded-2xl border border-border bg-card p-5 shadow-sm transition-colors hover:border-primary/30 hover:bg-muted/30"
                        >
                            <div className="space-y-3">
                                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                                    <Icon className="h-5 w-5" aria-hidden="true" />
                                </div>
                                <div className="space-y-1">
                                    <h3 className="text-sm font-bold text-text-primary">{source.title}</h3>
                                    <p className="text-xs leading-5 text-text-secondary">{source.description}</p>
                                </div>
                            </div>
                            <span className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-primary">
                                {t('finance.reports.open_source', 'فتح المصدر')}
                                <DirectionIcon className="h-3.5 w-3.5" aria-hidden="true" />
                            </span>
                        </Link>
                    );
                })}
            </section>

            <section
                className="rounded-2xl border border-border bg-card p-5"
                data-testid="advanced-insights-deferred"
            >
                <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                        <ShieldCheck className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <div className="space-y-1">
                        <h3 className="text-sm font-bold text-text-primary">
                            {t('finance.reports.verified_insights_only', 'الرؤى المتقدمة تظهر فقط بعقد موثوق')}
                        </h3>
                        <p className="text-xs leading-5 text-text-secondary">
                            {t(
                                'finance.reports.verified_insights_only_desc',
                                'مقارنة الفترات والاتجاهات والتصدير وهامش المواد ستُبنى من تجميعات الخادم وبيانات coverage/confidence. لا يعرض Dentix هنا تقديرات ناقصة أو أصفارًا مصطنعة أثناء مرحلة الانتقال.',
                            )}
                        </p>
                    </div>
                </div>
            </section>
        </div>
    );
}

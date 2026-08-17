import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
    Users,
    UserCheck,
    UserMinus,
    ArrowRight,
    AlertTriangle,
} from 'lucide-react';
import Money from '../../components/Money';
import ScopeBadge from '../../components/ScopeBadge';

/**
 * Obligations and Receivables Section for Overview V2.
 * Summarizes actionable balances: Patient Receivables (All-time), Doctor Dues, and Staff Payroll.
 * Period-scoped cards inherit the page-level date range and therefore do not repeat it.
 */
export default function ObligationsSection({
    allTimeOutstanding = 0,
    doctorDuesTotal = 0,
    staffDuesTotal = 0,
    isLoading = false,
    currency = 'EGP',
}) {
    const { t } = useTranslation();

    const items = [
        {
            id: 'receivables',
            title: t('finance.obligations.patient_debt', 'مستحقات المرضى (الديون التراكمية)'),
            amount: allTimeOutstanding,
            scope: 'all_time',
            scopeLabel: t('finance.scope.all_time', 'الرصيد التراكمي (الكل)'),
            description: t('finance.obligations.patient_debt_desc', 'إجمالي المبالغ المتبقية بذمة المرضى عبر جميع الفترات'),
            icon: Users,
            iconBg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
            to: '/finance/patient-accounts',
            actionText: t('finance.obligations.view_debtors', 'عرض كشف المديونيات'),
        },
        {
            id: 'doctors',
            title: t('finance.obligations.doctor_dues', 'مستحقات الأطباء غير المسددة'),
            amount: doctorDuesTotal,
            description: t('finance.obligations.doctor_dues_desc', 'عمولات الجلسات المحصلة والرواتب الثابتة للفترة'),
            icon: UserCheck,
            iconBg: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
            to: '/finance/compensation/doctors',
            actionText: t('finance.obligations.view_doctors', 'تفصيل مستحقات الأطباء'),
        },
        {
            id: 'staff',
            title: t('finance.obligations.staff_dues', 'التزامات رواتب الموظفين'),
            amount: staffDuesTotal,
            description: t('finance.obligations.staff_dues_desc', 'رواتب وبدلات طاقم التمريض والاستقبال والإدارة'),
            icon: UserMinus,
            iconBg: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
            to: '/finance/compensation/payroll',
            actionText: t('finance.obligations.view_payroll', 'مسير الرواتب'),
        },
    ];

    if (isLoading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="p-5 rounded-2xl border border-border bg-card shadow-sm animate-pulse space-y-3">
                        <div className="h-4 w-32 bg-muted rounded"></div>
                        <div className="h-7 w-28 bg-muted rounded"></div>
                        <div className="h-3 w-44 bg-muted rounded"></div>
                    </div>
                ))}
            </div>
        );
    }

    return (
        <section aria-label={t('finance.obligations.title', 'الالتزامات والمستحقات القائمة')} className="space-y-3">
            <div className="flex items-center justify-between">
                <h2 className="text-sm sm:text-base font-bold text-text-primary flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    <span>{t('finance.obligations.section_title', 'الالتزامات والذمم المالية القائمة')}</span>
                </h2>
                <span className="text-xs text-text-secondary">
                    {t('finance.obligations.actionable_hint', 'مؤشرات قابلة للمتابعة الفورية')}
                </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {items.map((item) => {
                    const Icon = item.icon;
                    return (
                        <div
                            key={item.id}
                            className="p-5 rounded-2xl border border-border bg-card hover:border-primary/30 transition-all duration-200 shadow-sm flex flex-col justify-between"
                        >
                            <div className="space-y-3">
                                <div className="flex items-center justify-between gap-2">
                                    <div className="flex items-center gap-2.5">
                                        <div className={`p-2 rounded-xl ${item.iconBg}`}>
                                            <Icon className="w-4 h-4" />
                                        </div>
                                        <h3 className="text-xs sm:text-sm font-bold text-text-primary line-clamp-1">
                                            {item.title}
                                        </h3>
                                    </div>
                                    {item.scopeLabel && (
                                        <ScopeBadge scope={item.scope} label={item.scopeLabel} />
                                    )}
                                </div>

                                <div className="pt-1">
                                    <Money
                                        amount={item.amount}
                                        currency={currency}
                                        size="xl"
                                    />
                                </div>

                                <p className="text-xs text-text-secondary leading-relaxed">
                                    {item.description}
                                </p>
                            </div>

                            <div className="mt-4 pt-3 border-t border-border/50">
                                <Link
                                    to={item.to}
                                    className="inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:text-primary/80 transition-colors"
                                >
                                    <span>{item.actionText}</span>
                                    <ArrowRight className="w-3.5 h-3.5 rtl:rotate-180" />
                                </Link>
                            </div>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}

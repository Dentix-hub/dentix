import { NavLink, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
    LayoutDashboard,
    Users,
    CreditCard,
    UserCheck,
    FileText,
} from 'lucide-react';
import { useFinancePermissions } from '../useFinancePermissions';

/**
 * Canonical Finance V2 navigation.
 *
 * PR5 intentionally exposes five destinations only. Operational children live
 * under Cash Movements and Team, while legacy routes are compatibility-only.
 */
export default function FinanceNav({ className = '' }) {
    const { t } = useTranslation();
    const location = useLocation();
    const {
        canViewOverview,
        canViewPatientAccounts,
        canViewPayments,
        canViewExpenses,
        canViewPayroll,
        canViewActivity,
        canViewReports,
        isDoctor,
    } = useFinancePermissions();

    const currentParams = new URLSearchParams(location.search);
    const sharedPeriodParams = new URLSearchParams();
    ['from', 'to', 'preset'].forEach((key) => {
        const value = currentParams.get(key);
        if (value) sharedPeriodParams.set(key, value);
    });
    const sharedSearch = sharedPeriodParams.toString();

    const navItems = [
        {
            id: 'overview',
            to: '/finance/overview',
            label: t('finance.nav.overview', 'الملخص'),
            icon: LayoutDashboard,
            visible: canViewOverview,
        },
        {
            id: 'patient-accounts',
            to: '/finance/patient-accounts',
            label: t('finance.nav.patient_accounts', 'حسابات المرضى'),
            icon: Users,
            visible: canViewPatientAccounts,
        },
        {
            id: 'cash-movements',
            to: '/finance/cash-movements',
            label: t('finance.nav.cash_movements', 'الحركات النقدية'),
            icon: CreditCard,
            visible: canViewPayments || canViewExpenses || canViewActivity,
        },
        {
            id: 'team',
            to: '/finance/team',
            label: t('finance.nav.team', 'الفريق'),
            icon: UserCheck,
            visible: canViewPayroll || isDoctor,
        },
        {
            id: 'reports',
            to: '/finance/reports',
            label: t('finance.nav.reports_insights', 'التقارير والرؤى'),
            icon: FileText,
            visible: canViewReports,
        },
    ];

    const visibleItems = navItems.filter((item) => item.visible);

    return (
        <nav
            aria-label={t('finance.nav.aria_label', 'التنقل في قسم المالية')}
            className={`no-scrollbar w-full overflow-x-auto overscroll-x-contain border-b border-border bg-card/50 backdrop-blur-sm ${className}`}
        >
            <div className="flex min-w-max snap-x snap-mandatory items-center gap-1 px-2 py-1.5 sm:gap-1.5 sm:px-4">
                {visibleItems.map((item) => {
                    const Icon = item.icon;
                    const isActive =
                        location.pathname === item.to ||
                        (item.to !== '/finance/overview' && location.pathname.startsWith(`${item.to}/`)) ||
                        (item.to === '/finance/overview' && (location.pathname === '/finance' || location.pathname === '/finance/'));

                    return (
                        <NavLink
                            key={item.id}
                            to={{
                                pathname: item.to,
                                search: sharedSearch ? `?${sharedSearch}` : '',
                            }}
                            className={`inline-flex min-h-10 shrink-0 snap-start items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold transition-all duration-150 select-none sm:gap-2 sm:px-3.5 sm:text-sm ${
                                isActive
                                    ? 'bg-primary text-white shadow-sm'
                                    : 'text-text-secondary hover:bg-muted/80 hover:text-text-primary'
                            }`}
                        >
                            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                            <span className="whitespace-nowrap">{item.label}</span>
                        </NavLink>
                    );
                })}
            </div>
        </nav>
    );
}

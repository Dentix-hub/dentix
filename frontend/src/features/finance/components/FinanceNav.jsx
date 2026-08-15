import { NavLink, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
    LayoutDashboard,
    Users,
    CreditCard,
    Receipt,
    UserCheck,
    History,
    FileText,
} from 'lucide-react';
import { useFinancePermissions } from '../useFinancePermissions';

/**
 * Navigation Bar for Finance V2 (§4 MASTER_SPEC, GEMINI_REPAIR_PLAN R4).
 * Enforces granular RBAC visibility for each financial domain.
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

    const navItems = [
        {
            id: 'overview',
            to: '/finance/overview',
            label: t('finance.nav.overview', 'نظرة عامة'),
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
            id: 'payments',
            to: '/finance/payments',
            label: t('finance.nav.payments', 'المدفوعات'),
            icon: CreditCard,
            visible: canViewPayments,
        },
        {
            id: 'expenses',
            to: '/finance/expenses',
            label: t('finance.nav.expenses', 'المصروفات'),
            icon: Receipt,
            visible: canViewExpenses,
        },
        {
            id: 'compensation',
            to: isDoctor ? '/finance/compensation/doctors' : '/finance/compensation',
            label: t('finance.nav.compensation', 'المستحقات والرواتب'),
            icon: UserCheck,
            visible: canViewPayroll || isDoctor,
        },
        {
            id: 'activity',
            to: '/finance/activity',
            label: t('finance.nav.activity', 'سجل المعاملات'),
            icon: History,
            visible: canViewActivity,
        },
        {
            id: 'reports',
            to: '/finance/reports',
            label: t('finance.nav.reports', 'التقارير المالية'),
            icon: FileText,
            visible: canViewReports,
        },
    ];

    const visibleItems = navItems.filter((item) => item.visible);

    return (
        <nav
            aria-label={t('finance.nav.aria_label', 'التنقل في قسم المالية')}
            className={`w-full overflow-x-auto no-scrollbar border-b border-border bg-card/50 backdrop-blur-sm ${className}`}
        >
            <div className="flex items-center gap-1.5 px-2 sm:px-4 py-1.5 min-w-max">
                {visibleItems.map((item) => {
                    const Icon = item.icon;
                    const isActive =
                        location.pathname === item.to ||
                        (item.to !== '/finance/overview' && location.pathname.startsWith(item.to)) ||
                        (item.to === '/finance/overview' && (location.pathname === '/finance' || location.pathname === '/finance/'));

                    return (
                        <NavLink
                            key={item.id}
                            to={item.to}
                            className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all duration-150 select-none ${
                                isActive
                                    ? 'bg-primary text-white shadow-sm'
                                    : 'text-text-secondary hover:text-text-primary hover:bg-muted/80'
                            }`}
                        >
                            <Icon className="w-4 h-4" />
                            <span>{item.label}</span>
                        </NavLink>
                    );
                })}
            </div>
        </nav>
    );
}

import { NavLink, Outlet, useLocation, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { UserCheck, Users } from 'lucide-react';
import { useFinancePermissions } from '../useFinancePermissions';

export default function CompensationLayout() {
    const { t } = useTranslation();
    const location = useLocation();
    const { isAdmin, isAccountant } = useFinancePermissions();

    // If exactly on /finance/compensation, redirect to /finance/compensation/doctors
    if (location.pathname === '/finance/compensation' || location.pathname === '/finance/compensation/') {
        return <Navigate to="/finance/compensation/doctors" replace />;
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-2 border-b border-border pb-3">
                <NavLink
                    to="/finance/compensation/doctors"
                    className={({ isActive }) =>
                        `inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs sm:text-sm font-bold transition-colors ${
                            isActive || location.pathname.startsWith('/finance/compensation/doctors')
                                ? 'bg-primary/10 text-primary border border-primary/20'
                                : 'text-text-secondary hover:text-text-primary hover:bg-muted'
                        }`
                    }
                >
                    <UserCheck className="w-4 h-4" />
                    <span>{t('finance.compensation.doctors', 'مستحقات الأطباء')}</span>
                </NavLink>

                {(isAdmin || isAccountant) && (
                    <NavLink
                        to="/finance/compensation/payroll"
                        className={({ isActive }) =>
                            `inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs sm:text-sm font-bold transition-colors ${
                                isActive
                                    ? 'bg-primary/10 text-primary border border-primary/20'
                                    : 'text-text-secondary hover:text-text-primary hover:bg-muted'
                            }`
                        }
                    >
                        <Users className="w-4 h-4" />
                        <span>{t('finance.compensation.payroll', 'رواتب الموظفين')}</span>
                    </NavLink>
                )}
            </div>

            <Outlet />
        </div>
    );
}

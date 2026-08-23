import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { UserCheck, Users } from 'lucide-react';
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

export default function TeamLayout() {
    const { t } = useTranslation();
    const location = useLocation();
    const { isDoctor, canViewPayroll } = useFinancePermissions();
    const periodSearch = sharedPeriodSearch(location.search);

    const doctorsTarget = {
        pathname: '/finance/team/doctors',
        search: periodSearch ? `?${periodSearch}` : '',
    };
    const payrollTarget = {
        pathname: '/finance/team/payroll',
        search: periodSearch ? `?${periodSearch}` : '',
    };

    const isIndex = location.pathname === '/finance/team' || location.pathname === '/finance/team/';
    if (isIndex) {
        return <Navigate replace to={doctorsTarget} />;
    }

    return (
        <div className="space-y-6">
            <div
                className="flex max-w-full items-center gap-2 overflow-x-auto border-b border-border pb-3"
                aria-label={t('finance.team.navigation', 'التنقل داخل قسم الفريق')}
            >
                <NavLink
                    to={doctorsTarget}
                    className={({ isActive }) =>
                        `inline-flex min-h-10 shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-bold transition-colors sm:text-sm ${
                            isActive || location.pathname.startsWith('/finance/team/doctors')
                                ? 'border border-primary/20 bg-primary/10 text-primary'
                                : 'text-text-secondary hover:bg-muted hover:text-text-primary'
                        }`
                    }
                >
                    <UserCheck className="h-4 w-4" aria-hidden="true" />
                    <span>{t('finance.compensation.doctors', 'مستحقات الأطباء')}</span>
                </NavLink>

                {!isDoctor && canViewPayroll && (
                    <NavLink
                        to={payrollTarget}
                        className={({ isActive }) =>
                            `inline-flex min-h-10 shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-bold transition-colors sm:text-sm ${
                                isActive
                                    ? 'border border-primary/20 bg-primary/10 text-primary'
                                    : 'text-text-secondary hover:bg-muted hover:text-text-primary'
                            }`
                        }
                    >
                        <Users className="h-4 w-4" aria-hidden="true" />
                        <span>{t('finance.compensation.payroll', 'رواتب الموظفين')}</span>
                    </NavLink>
                )}
            </div>

            <Outlet />
        </div>
    );
}

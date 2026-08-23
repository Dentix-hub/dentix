import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CreditCard, Receipt, History } from 'lucide-react';
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

export default function CashMovementsLayout() {
    const { t } = useTranslation();
    const location = useLocation();
    const { canViewPayments, canViewExpenses, canViewActivity } = useFinancePermissions();
    const periodSearch = sharedPeriodSearch(location.search);

    const items = [
        {
            id: 'payments',
            to: '/finance/cash-movements/payments',
            label: t('finance.nav.payments', 'التحصيلات'),
            icon: CreditCard,
            visible: canViewPayments,
        },
        {
            id: 'expenses',
            to: '/finance/cash-movements/expenses',
            label: t('finance.nav.expenses', 'المصروفات'),
            icon: Receipt,
            visible: canViewExpenses,
        },
        {
            id: 'activity',
            to: '/finance/cash-movements/activity',
            label: t('finance.nav.activity', 'سجل الحركة'),
            icon: History,
            visible: canViewActivity,
        },
    ].filter((item) => item.visible);

    const isIndex =
        location.pathname === '/finance/cash-movements' ||
        location.pathname === '/finance/cash-movements/';

    if (isIndex && items.length > 0) {
        return (
            <Navigate
                replace
                to={{
                    pathname: items[0].to,
                    search: periodSearch ? `?${periodSearch}` : '',
                }}
            />
        );
    }

    return (
        <div className="space-y-5">
            <div className="flex max-w-full items-center gap-1 overflow-x-auto border-b border-border pb-3">
                {items.map((item) => {
                    const Icon = item.icon;
                    return (
                        <NavLink
                            key={item.id}
                            to={{
                                pathname: item.to,
                                search: periodSearch ? `?${periodSearch}` : '',
                            }}
                            className={({ isActive }) =>
                                `inline-flex min-h-10 shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-bold transition-colors sm:text-sm ${
                                    isActive
                                        ? 'border border-primary/20 bg-primary/10 text-primary'
                                        : 'text-text-secondary hover:bg-muted hover:text-text-primary'
                                }`
                            }
                        >
                            <Icon className="h-4 w-4" aria-hidden="true" />
                            <span>{item.label}</span>
                        </NavLink>
                    );
                })}
            </div>
            <Outlet />
        </div>
    );
}

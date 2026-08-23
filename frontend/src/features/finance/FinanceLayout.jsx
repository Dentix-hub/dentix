import { Suspense } from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ShieldAlert, ArrowRight, ArrowLeft } from 'lucide-react';
import FinanceHeader from './components/FinanceHeader';
import FinanceNav from './components/FinanceNav';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { useFinancePermissions } from './useFinancePermissions';

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
 * Routed Finance V2 shell for the canonical five-destination information
 * architecture. Legacy routes may still pass through this shell while their
 * redirect component normalizes them to the new destination tree.
 */
export default function FinanceLayout() {
    const { t, i18n } = useTranslation();
    const location = useLocation();
    const isRtl = i18n.language === 'ar';
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

    const path = location.pathname;
    const isPayrollRoute =
        path.startsWith('/finance/team/payroll') ||
        path.startsWith('/finance/compensation/payroll');
    const routeOwnsLocalPeriodPicker =
        path.startsWith('/finance/cash-movements/expenses') ||
        path.startsWith('/finance/team/doctors') ||
        path.startsWith('/finance/expenses') ||
        path.startsWith('/finance/compensation/doctors');
    const showDatePicker = !isPayrollRoute && !routeOwnsLocalPeriodPicker;

    const canViewAnyCashMovement = canViewPayments || canViewExpenses || canViewActivity;
    const canViewTeam = isDoctor || canViewPayroll;

    let isAuthorized = true;
    let fallbackPath = '/finance/overview';

    if (path.startsWith('/finance/overview') && !canViewOverview) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/team/doctors' : '/finance/cash-movements/payments';
    } else if (path.startsWith('/finance/patient-accounts') && !canViewPatientAccounts) {
        isAuthorized = false;
        fallbackPath = canViewAnyCashMovement ? '/finance/cash-movements' : '/finance/overview';
    } else if (
        (path.startsWith('/finance/cash-movements/payments') || path.startsWith('/finance/payments')) &&
        !canViewPayments
    ) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/team/doctors' : '/finance/overview';
    } else if (
        (path.startsWith('/finance/cash-movements/expenses') || path.startsWith('/finance/expenses')) &&
        !canViewExpenses
    ) {
        isAuthorized = false;
        fallbackPath = canViewPayments ? '/finance/cash-movements/payments' : '/finance/overview';
    } else if (
        (path.startsWith('/finance/cash-movements/activity') || path.startsWith('/finance/activity')) &&
        !canViewActivity
    ) {
        isAuthorized = false;
        fallbackPath = canViewPayments ? '/finance/cash-movements/payments' : '/finance/overview';
    } else if (path.startsWith('/finance/cash-movements') && !canViewAnyCashMovement) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/team/doctors' : '/finance/overview';
    } else if (
        (path.startsWith('/finance/team/payroll') || path.startsWith('/finance/compensation/payroll')) &&
        !canViewPayroll
    ) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/team/doctors' : '/finance/overview';
    } else if (
        (path.startsWith('/finance/team') || path.startsWith('/finance/compensation')) &&
        !canViewTeam
    ) {
        isAuthorized = false;
        fallbackPath = canViewAnyCashMovement ? '/finance/cash-movements' : '/finance/overview';
    } else if (path.startsWith('/finance/reports') && !canViewReports) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/team/doctors' : '/finance/cash-movements';
    }

    const periodSearch = sharedPeriodSearch(location.search);
    const fallbackTarget = {
        pathname: fallbackPath,
        search: periodSearch ? `?${periodSearch}` : '',
    };

    return (
        <div className="flex min-h-[calc(100vh-4rem)] flex-col bg-background">
            <FinanceHeader showDatePicker={showDatePicker} />
            <FinanceNav />
            <main className="mx-auto w-full max-w-7xl flex-1 p-3 sm:p-5 lg:p-8">
                <Suspense
                    fallback={
                        <div className="flex items-center justify-center py-12">
                            <LoadingSpinner />
                        </div>
                    }
                >
                    {isAuthorized ? (
                        <Outlet />
                    ) : (
                        <div className="mx-auto my-12 max-w-lg space-y-4 rounded-2xl border border-border bg-card p-6 text-center shadow-sm sm:p-8">
                            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
                                <ShieldAlert className="h-6 w-6" />
                            </div>
                            <h3 className="text-lg font-bold text-text-primary">
                                {t('finance.permissions.access_denied', 'غير مصرح بالوصول إلى هذا القسم')}
                            </h3>
                            <p className="text-sm text-text-secondary">
                                {t('finance.permissions.access_denied_desc', 'صلاحيات حسابك الحالية لا تسمح بالاطلاع على هذه البيانات المالية.')}
                            </p>
                            <div className="pt-2">
                                <Link
                                    to={fallbackTarget}
                                    className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-white transition-all hover:bg-primary/90"
                                >
                                    <span>{t('finance.permissions.go_to_allowed', 'الانتقال إلى القسم المصرح')}</span>
                                    {isRtl ? <ArrowLeft className="h-4 w-4" /> : <ArrowRight className="h-4 w-4" />}
                                </Link>
                            </div>
                        </div>
                    )}
                </Suspense>
            </main>
        </div>
    );
}

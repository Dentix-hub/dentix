import { Suspense } from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ShieldAlert, ArrowRight, ArrowLeft } from 'lucide-react';
import FinanceHeader from './components/FinanceHeader';
import FinanceNav from './components/FinanceNav';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { useFinancePermissions } from './useFinancePermissions';

/**
 * Lightweight routed layout for Finance V2 with strict domain-level RBAC gating (§4 MASTER_SPEC, GEMINI_REPAIR_PLAN R4).
 * Renders persistent header and sub-navigation, delegating content to routed sub-pages.
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
    let isAuthorized = true;
    let fallbackPath = '/finance/overview';

    if (path.startsWith('/finance/overview') && !canViewOverview) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/compensation/doctors' : '/finance/payments';
    } else if (path.startsWith('/finance/expenses') && !canViewExpenses) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/compensation/doctors' : '/finance/payments';
    } else if (path.startsWith('/finance/reports') && !canViewReports) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/compensation/doctors' : '/finance/payments';
    } else if (path.startsWith('/finance/compensation/payroll') && !canViewPayroll) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/compensation/doctors' : '/finance/payments';
    } else if (path.startsWith('/finance/compensation') && !isDoctor && !canViewPayroll) {
        isAuthorized = false;
        fallbackPath = '/finance/payments';
    } else if (path.startsWith('/finance/patient-accounts') && !canViewPatientAccounts) {
        isAuthorized = false;
        fallbackPath = '/finance/payments';
    } else if (path.startsWith('/finance/payments') && !canViewPayments) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/compensation/doctors' : '/finance/overview';
    } else if (path.startsWith('/finance/activity') && !canViewActivity) {
        isAuthorized = false;
        fallbackPath = isDoctor ? '/finance/compensation/doctors' : '/finance/payments';
    }

    return (
        <div className="flex min-h-[calc(100vh-4rem)] flex-col bg-background">
            <FinanceHeader />
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
                                    to={fallbackPath}
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

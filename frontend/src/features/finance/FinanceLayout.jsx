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
        isReceptionist,
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
        <div className="flex flex-col min-h-[calc(100vh-4rem)] bg-background">
            <FinanceHeader />
            <FinanceNav />
            <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
                <Suspense
                    fallback={
                        <div className="py-12 flex justify-center items-center">
                            <LoadingSpinner />
                        </div>
                    }
                >
                    {isAuthorized ? (
                        <Outlet />
                    ) : (
                        <div className="p-8 max-w-lg mx-auto text-center space-y-4 my-12 bg-card border border-border rounded-2xl shadow-sm">
                            <div className="w-12 h-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mx-auto">
                                <ShieldAlert className="w-6 h-6" />
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
                                    className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold text-white bg-primary hover:bg-primary/90 rounded-xl transition-all"
                                >
                                    <span>{t('finance.permissions.go_to_allowed', 'الانتقال إلى القسم المصرح')}</span>
                                    {isRtl ? <ArrowLeft className="w-4 h-4" /> : <ArrowRight className="w-4 h-4" />}
                                </Link>
                            </div>
                        </div>
                    )}
                </Suspense>
            </main>
        </div>
    );
}

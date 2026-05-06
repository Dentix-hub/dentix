import { useMemo } from 'react';
import { AlertTriangle, Info, ShieldAlert, CreditCard } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useTenantStore } from '@/store/tenant.store';
import { useAuth } from '@/auth/useAuth';

const SubscriptionBanner = () => {
    const { t } = useTranslation();
    const { tenant } = useTenantStore();
    const { user } = useAuth();
    const isSuperAdmin = user?.role === 'super_admin';

    const bannerInfo = useMemo(() => {
        if (!tenant || isSuperAdmin) return null;

        const now = new Date();
        const endDate = tenant.subscription_end_date ? new Date(tenant.subscription_end_date) : null;
        const graceDate = tenant.grace_period_until ? new Date(tenant.grace_period_until) : null;

        if (!endDate) return null;

        const daysLeft = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));

        if (daysLeft < 0) {
            // Expired. Check Grace Period.
            if (graceDate && now <= graceDate) {
                const graceDaysLeft = Math.ceil((graceDate - now) / (1000 * 60 * 60 * 24));
                return {
                    message: t('sidebar.subscription.grace_period', { count: graceDaysLeft }),
                    type: 'warning',
                    icon: AlertTriangle,
                    bg: 'bg-amber-500',
                };
            } else {
                // Subscription AND Grace Period expired
                return {
                    message: t('sidebar.subscription.expired_readonly'),
                    type: 'error',
                    icon: ShieldAlert,
                    bg: 'bg-red-600',
                };
            }
        } else if (daysLeft >= 0 && daysLeft <= 3) {
            // Expiring soon (3 days or less)
            return {
                message: t('sidebar.subscription.expiring_soon', { count: daysLeft }),
                type: 'info',
                icon: Info,
                bg: 'bg-indigo-600',
            };
        }

        return null;
    }, [tenant, isSuperAdmin, t]);

    if (!bannerInfo) return null;

    return (
        <div className={`${bannerInfo.bg} text-white px-4 py-2 shadow-lg relative animate-in slide-in-from-top duration-300 z-50 border-b border-white/10`}>
            <div className="container mx-auto flex items-center justify-center gap-3 text-sm font-bold text-center">
                <bannerInfo.icon size={18} className="shrink-0 animate-pulse" />
                <span>{bannerInfo.message}</span>
                <button 
                    onClick={() => window.location.href = '/settings'}
                    className="ml-4 px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg transition-colors flex items-center gap-2 text-xs"
                >
                    <CreditCard size={14} />
                    {t('settings.tabs.subscription')}
                </button>
            </div>
        </div>
    );
};

export default SubscriptionBanner;

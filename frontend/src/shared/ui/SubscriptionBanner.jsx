import { useMemo } from 'react';
import { AlertTriangle, Info, ShieldAlert, CreditCard } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useTenantStore } from '@/store/tenant.store';
import { useAuth } from '@/auth/useAuth';

const SubscriptionBanner = () => {
    const { t } = useTranslation();
    const { tenant, entitlements } = useTenantStore();
    const { user } = useAuth();
    const isSuperAdmin = user?.role === 'super_admin';

    const bannerInfo = useMemo(() => {
        if (isSuperAdmin) return null;

        // Authoritative entitlements snapshot
        if (entitlements) {
            const status = entitlements.effective_subscription_status;
            if (status === 'EXPIRED' || (entitlements.is_past_end && !entitlements.is_in_grace)) {
                return {
                    message: t('sidebar.subscription.expired_readonly', 'تم انتهاء الاشتراك — وضع القراءة فقط مفعل'),
                    type: 'error',
                    icon: ShieldAlert,
                    bg: 'bg-red-600',
                };
            }
            if (status === 'GRACE' || entitlements.is_in_grace) {
                let graceDays = 0;
                if (entitlements.grace_period_until) {
                    const graceDate = new Date(entitlements.grace_period_until);
                    graceDays = Math.max(0, Math.ceil((graceDate - new Date()) / (1000 * 60 * 60 * 24)));
                }
                return {
                    message: t('sidebar.subscription.grace_period', { count: graceDays, defaultValue: `فترة السماح سارية (متبقي ${graceDays} يوم)` }),
                    type: 'warning',
                    icon: AlertTriangle,
                    bg: 'bg-amber-500',
                };
            }
            if (status === 'TRIAL') {
                if (entitlements.subscription_end_date) {
                    const endDate = new Date(entitlements.subscription_end_date);
                    const daysLeft = Math.max(0, Math.ceil((endDate - new Date()) / (1000 * 60 * 60 * 24)));
                    if (daysLeft <= 3) {
                        return {
                            message: t('sidebar.subscription.trial_ending_soon', { count: daysLeft, defaultValue: `الباقة التجريبية تنتهي قريباً (متبقي ${daysLeft} يوم)` }),
                            type: 'info',
                            icon: Info,
                            bg: 'bg-indigo-600',
                        };
                    }
                }
            }
            if (status === 'HARD_DISABLED' || entitlements.is_hard_disabled) {
                return {
                    message: t('sidebar.subscription.security_disabled', 'تم تعطيل الحساب لأسباب أمنية. يرجى التواصل مع إدارة النظام.'),
                    type: 'error',
                    icon: ShieldAlert,
                    bg: 'bg-red-700',
                };
            }
            if (status === 'SUSPENDED') {
                return {
                    message: t('sidebar.subscription.commercial_suspended', 'تم تعليق الاشتراك تجارياً. تواصل مع الدعم الفني للتفعيل.'),
                    type: 'error',
                    icon: ShieldAlert,
                    bg: 'bg-rose-600',
                };
            }
            if (entitlements.subscription_end_date) {
                const endDate = new Date(entitlements.subscription_end_date);
                const daysLeft = Math.ceil((endDate - new Date()) / (1000 * 60 * 60 * 24));
                if (daysLeft <= 3 && daysLeft >= 0) {
                    return {
                        message: t('sidebar.subscription.expiring_soon', { count: daysLeft }),
                        type: 'info',
                        icon: Info,
                        bg: 'bg-indigo-600',
                    };
                }
            }
            return null;
        }

        // Fallback for legacy tenant state before snapshot
        if (!tenant) return null;
        const now = new Date();
        const endDate = tenant.subscription_end_date ? new Date(tenant.subscription_end_date) : null;
        const graceDate = tenant.grace_period_until ? new Date(tenant.grace_period_until) : null;

        if (!endDate) return null;
        const daysLeft = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));

        if (daysLeft < 0) {
            if (graceDate && now <= graceDate) {
                const graceDaysLeft = Math.ceil((graceDate - now) / (1000 * 60 * 60 * 24));
                return {
                    message: t('sidebar.subscription.grace_period', { count: graceDaysLeft }),
                    type: 'warning',
                    icon: AlertTriangle,
                    bg: 'bg-amber-500',
                };
            }
            return {
                message: t('sidebar.subscription.expired_readonly'),
                type: 'error',
                icon: ShieldAlert,
                bg: 'bg-red-600',
            };
        }

        if (daysLeft <= 3) {
            return {
                message: t('sidebar.subscription.expiring_soon', { count: daysLeft }),
                type: 'info',
                icon: Info,
                bg: 'bg-indigo-600',
            };
        }

        return null;
    }, [entitlements, tenant, isSuperAdmin, t]);

    if (!bannerInfo) return null;

    const BannerIcon = bannerInfo.icon;

    return (
        <div className={`${bannerInfo.bg} relative z-50 border-b border-white/10 px-2 py-2 text-white shadow-lg animate-in slide-in-from-top duration-300 sm:px-4`}>
            <div className="mx-auto flex min-w-0 max-w-7xl flex-col items-stretch justify-center gap-2 text-xs font-bold sm:flex-row sm:items-center sm:gap-3 sm:text-sm sm:text-center">
                <div className="flex min-w-0 items-start gap-2 sm:items-center">
                    <BannerIcon size={18} className="mt-0.5 shrink-0 text-white motion-reduce:animate-none sm:mt-0" aria-hidden="true" />
                    <span className="min-w-0 break-words text-white">{bannerInfo.message}</span>
                </div>
                <button
                    type="button"
                    onClick={() => { window.location.href = '/settings'; }}
                    className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-white/20 px-3 py-2 text-xs text-white transition-colors hover:bg-white/30 sm:ms-2 sm:w-auto"
                >
                    <CreditCard size={14} aria-hidden="true" />
                    {t('settings.tabs.subscription')}
                </button>
            </div>
        </div>
    );
};

export default SubscriptionBanner;

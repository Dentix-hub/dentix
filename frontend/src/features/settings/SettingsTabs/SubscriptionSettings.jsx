import { Shield, CreditCard, Calendar } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const SubscriptionSettings = ({ currentUser }) => {
    const { t } = useTranslation();
    if (!currentUser?.tenant) return null;

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-6 bg-slate-50 dark:bg-slate-900/30 rounded-2xl border border-slate-100 dark:border-white/5">
                <div className="flex items-center gap-3 text-slate-500 mb-2">
                    <Shield size={20} />
                    <span className="font-bold">{t('settings.subscription.clinic_name')}</span>
                </div>
                <p className="text-2xl font-black text-slate-800 dark:text-white">{currentUser.tenant.name}</p>
            </div>

            <div className="p-6 bg-slate-50 dark:bg-slate-900/30 rounded-2xl border border-slate-100 dark:border-white/5">
                <div className="flex items-center gap-3 text-slate-500 mb-2">
                    <CreditCard size={20} />
                    <span className="font-bold">{t('settings.subscription.current_plan')}</span>
                </div>
                <p className={`text-2xl font-black ${currentUser.tenant.plan === 'premium' ? 'text-amber-500' : 'text-blue-600'
                    }`}>
                    {currentUser.tenant.plan === 'premium' ? t('settings.subscription.premium') : t('settings.subscription.basic')}
                </p>
            </div>

            <div className="p-6 bg-slate-50 dark:bg-slate-900/30 rounded-2xl border border-slate-100 dark:border-white/5 md:col-span-2">
                <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                    <div>
                        <div className="flex items-center gap-2 text-slate-500 mb-1">
                            <Calendar size={18} />
                            <span className="font-bold">{t('settings.subscription.expiry_date')}</span>
                        </div>
                        <p className="text-xl font-bold text-slate-800 dark:text-white">
                            {currentUser.tenant.subscription_end_date
                                ? new Date(currentUser.tenant.subscription_end_date).toLocaleDateString(t('language.code') === 'ar' ? 'ar-EG' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric' })
                                : t('settings.subscription.unlimited')}
                        </p>
                    </div>

                    {currentUser.tenant.subscription_end_date && (() => {
                        const daysLeft = Math.ceil((new Date(currentUser.tenant.subscription_end_date) - new Date()) / (1000 * 60 * 60 * 24));
                        return (
                            <div className={`px-4 py-2 rounded-lg font-bold ${daysLeft < 7 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                                {daysLeft <= 0 ? t('settings.subscription.expired') : t('settings.subscription.days_remaining', { count: daysLeft })}
                            </div>
                        );
                    })()}
                </div>
            </div>
        </div>
    );
};

export default SubscriptionSettings;

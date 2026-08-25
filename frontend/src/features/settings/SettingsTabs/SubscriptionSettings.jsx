import { Shield, CreditCard, Calendar, Info, CheckCircle2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const SubscriptionSettings = ({ currentUser }) => {
    const { t } = useTranslation();
    if (!currentUser?.tenant) return null;

    const tenant = currentUser.tenant;
    const isGrace = tenant.subscription_status === 'grace';

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-6 bg-slate-50 dark:bg-slate-900/30 rounded-2xl border border-slate-100 dark:border-white/5">
                    <div className="flex items-center gap-3 text-slate-500 mb-2">
                        <Shield size={20} />
                        <span className="font-bold">{t('settings.subscription.clinic_name')}</span>
                    </div>
                    <p className="text-2xl font-bold text-slate-800 dark:text-white">{tenant.name}</p>
                </div>

                <div className="p-6 bg-slate-50 dark:bg-slate-900/30 rounded-2xl border border-slate-100 dark:border-white/5">
                    <div className="flex items-center gap-3 text-slate-500 mb-2">
                        <CreditCard size={20} />
                        <span className="font-bold">{t('settings.subscription.current_plan')}</span>
                    </div>
                    <p className={`text-2xl font-bold ${tenant.plan === 'premium' ? 'text-amber-500' : 'text-blue-600'}`}>
                        {tenant.plan === 'premium' ? t('settings.subscription.premium') : (tenant.plan || t('settings.subscription.basic'))}
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
                                {tenant.subscription_end_date
                                    ? new Date(tenant.subscription_end_date).toLocaleDateString(t('language.code') === 'ar' ? 'ar-EG' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric' })
                                    : t('settings.subscription.unlimited')}
                            </p>
                        </div>

                        {tenant.subscription_end_date && (() => {
                            const daysLeft = Math.ceil((new Date(tenant.subscription_end_date) - new Date()) / (1000 * 60 * 60 * 24));
                            return (
                                <div className={`px-4 py-2 rounded-lg font-bold ${daysLeft < 7 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'}`}>
                                    {daysLeft <= 0 ? (isGrace ? 'فترة سماح' : t('settings.subscription.expired')) : t('settings.subscription.days_remaining', { count: daysLeft })}
                                </div>
                            );
                        })()}
                    </div>
                </div>
            </div>

            {/* Policy & Invariant Card */}
            <div className="p-6 bg-indigo-50/50 dark:bg-indigo-950/20 rounded-2xl border border-indigo-100 dark:border-indigo-900/30">
                <div className="flex items-start gap-3">
                    <Info size={20} className="text-indigo-600 dark:text-indigo-400 mt-1 shrink-0" />
                    <div className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
                        <p className="font-bold text-indigo-950 dark:text-indigo-200">
                            سياسة الاشتراك والبيانات الطبية:
                        </p>
                        <div className="flex items-center gap-2 text-xs">
                            <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
                            <span>سجلات المرضى، العلاجات، والملفات الطبية متاحة للقراءة والاطلاع الدائم دون انقطاع.</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs">
                            <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
                            <span>يتم تجديد الاشتراكات حصرياً عبر التواصل المباشر مع إدارة المنظومة والدعم الفني.</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SubscriptionSettings;

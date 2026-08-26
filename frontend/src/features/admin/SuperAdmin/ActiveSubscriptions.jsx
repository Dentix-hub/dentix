import { CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const ActiveSubscriptions = ({ tenants, plans, getDaysRemaining }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    const safeGetDaysRemaining = typeof getDaysRemaining === 'function' 
        ? getDaysRemaining 
        : (endDate) => {
            if (!endDate) return null;
            const diff = new Date(endDate) - new Date();
            return Math.ceil(diff / (1000 * 60 * 60 * 24));
        };

    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="overflow-x-auto w-full">
                <table className={`w-full ${isRtl ? 'text-right' : 'text-left'}`}>
                    <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase tracking-wider">
                        <tr>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.tenants.clinic_name') || t('super_admin.tenants.title') || 'العيادة'}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.plans.current_plan') || 'الخطة الحالية'}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.plans.price_label') || 'السعر'}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.plans.remaining_duration') || 'المدة المتبقية'}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.plans.expiry') || 'تاريخ الانتهاء'}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.tenants.status') || 'الحالة'}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {(Array.isArray(tenants) && tenants.length > 0) ? tenants.map((tenant) => {
                            const daysLeft = safeGetDaysRemaining(tenant.subscription_end_date);
                            const plan = Array.isArray(plans) ? plans.find(p => p.id === tenant.plan_id) : null;
                            const isActive = tenant.is_active && (daysLeft === null || daysLeft > 0);
                            const tenantName = tenant.name || tenant.clinic_name || 'Clinic';
                            const planName = plan ? (isRtl ? plan.display_name_ar : plan.display_name_en || plan.name) : (t('super_admin.plans.trial') || 'تجريبية');
                            const priceFormatted = plan?.price != null ? Number(plan.price).toLocaleString(isRtl ? 'ar-EG' : 'en-US') : '0';
                            const dateFormatted = tenant.subscription_end_date ? new Date(tenant.subscription_end_date).toLocaleDateString(isRtl ? 'ar-EG' : 'en-US') : '-';

                            return (
                                <tr key={tenant.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                                    <td className="p-6 whitespace-nowrap">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold">
                                                {tenantName.charAt(0).toUpperCase()}
                                            </div>
                                            <span className="font-bold text-slate-800 dark:text-slate-200">{tenantName}</span>
                                        </div>
                                    </td>
                                    <td className="p-6 whitespace-nowrap">
                                        <span className="font-medium text-slate-600 dark:text-slate-400">
                                            {planName}
                                        </span>
                                    </td>
                                    <td className="p-6 whitespace-nowrap">
                                        <span className="font-bold text-emerald-600 dark:text-emerald-400">
                                            {priceFormatted} {t('super_admin.finance.currency') || 'ج.م'}
                                        </span>
                                    </td>
                                    <td className="p-6 whitespace-nowrap">
                                        {daysLeft !== null ? (
                                            <div className={`flex items-center gap-2 font-bold ${daysLeft < 7 ? 'text-rose-500' : 'text-slate-600 dark:text-slate-400'}`}>
                                                <Clock size={16} />
                                                {daysLeft} {t('common.days') || 'يوم'}
                                            </div>
                                        ) : (
                                            <span className="text-slate-500 text-2xl">∞</span>
                                        )}
                                    </td>
                                    <td className="p-6 font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
                                        {dateFormatted}
                                    </td>
                                    <td className="p-6 whitespace-nowrap">
                                        <span className={`px-4 py-1.5 rounded-full text-xs font-bold inline-flex items-center gap-1.5 ${isActive
                                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                            : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400'}`}>
                                            {isActive ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                                            {isActive ? (t('common.active') || 'نشط') : (t('common.expired') || 'منتهي')}
                                        </span>
                                    </td>
                                </tr>
                            );
                        }) : (
                            <tr>
                                <td colSpan="6" className="p-10 text-center text-slate-500">
                                    {t('super_admin.tenants.no_tenants') || 'لا توجد اشتراكات نشطة'}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ActiveSubscriptions;

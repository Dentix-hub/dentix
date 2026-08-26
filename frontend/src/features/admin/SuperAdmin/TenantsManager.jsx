import { Edit3, Clock, Trash2, Key, CalendarPlus, RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const TenantsManager = ({ 
    tenants, 
    plans, 
    handlePlanChange, 
    getDaysRemaining, 
    handleArchiveTenant, 
    handleRestoreTenant, 
    handlePermanentDelete, 
    onResetPassword,
    onManualRenew,
    onSelectTenant
}) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="overflow-x-auto min-w-full">
                <table className="w-full text-start">
                    <thead>
                        <tr className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-xs font-bold uppercase tracking-wider text-start">
                            <th className="p-5 text-start">{t('super_admin.tenants.title', 'العيادة والمستأجر')}</th>
                            <th className="p-5 text-start">{t('super_admin.tenants.plan', 'الباقة')}</th>
                            <th className="p-5 text-center">{t('super_admin.tenants.status', 'الحالة')}</th>
                            <th className="p-5 text-center">{t('super_admin.tenants.duration', 'المدة المتبقية')}</th>
                            <th className="p-5 text-start">{t('super_admin.tenants.revenue', 'الإيرادات')}</th>
                            <th className="p-5 text-center">{t('super_admin.tenants.actions', 'الإجراءات')}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {(tenants || []).map((tenant) => {
                            const daysLeft = getDaysRemaining(tenant.subscription_end_date);
                            const isDeleted = tenant.is_deleted;
                            const domainDisplay = tenant.domain ? `${tenant.domain}.dentix.com` : '—';

                            return (
                                <tr key={tenant.id} className={`transition-colors ${isDeleted ? 'bg-red-50/50 dark:bg-red-900/10' : 'hover:bg-slate-50/50 dark:hover:bg-slate-800/50'}`}>
                                    <td className="p-5 font-bold text-slate-800 dark:text-slate-200">
                                        <div className="flex items-center gap-3 cursor-pointer group" onClick={() => onSelectTenant && onSelectTenant(tenant.id)}>
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold transition-transform shrink-0 ${isDeleted ? 'bg-red-100 text-red-600' : 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/50 dark:text-indigo-400'}`}>
                                                {tenant.name?.charAt(0) || '?'}
                                            </div>
                                            <div className="flex flex-col text-start">
                                                <span className="group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors text-sm font-extrabold">{tenant.name || 'بدون اسم'}</span>
                                                <span className="text-[11px] text-slate-400 font-medium" dir="ltr">{domainDisplay}</span>
                                                {isDeleted && <span className="text-xs text-rose-500 font-bold">({t('super_admin.tenants.archived', 'مؤرشفة')})</span>}
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-5">
                                        {!isDeleted ? (
                                            <div className="relative">
                                                <select
                                                    value={tenant.plan_id || ''}
                                                    onChange={(e) => handlePlanChange(e, tenant.id)}
                                                    className={`appearance-none w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 py-2 ${isRtl ? 'pe-4 ps-10' : 'ps-4 pe-10'} rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 font-bold text-xs cursor-pointer`}
                                                >
                                                    <option value="" disabled>{t('super_admin.tenants.select_plan', 'اختر الباقة')}</option>
                                                    {(plans || []).map(p => (
                                                        <option key={p.id} value={p.id}>{i18n.language === 'ar' ? (p.display_name_ar || p.name) : (p.display_name_en || p.name)}</option>
                                                    ))}
                                                </select>
                                                <Edit3 size={15} className={`absolute ${isRtl ? 'start-3' : 'end-3'} top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none`} />
                                            </div>
                                        ) : (
                                            <span className="text-slate-400 text-sm font-bold">—</span>
                                        )}
                                    </td>
                                    <td className="p-5 text-center">
                                        <span className={`px-3 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1.5 ${!isDeleted && tenant.is_active && (daysLeft === null || daysLeft >= 0)
                                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                            : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400'
                                            }`}>
                                            <span className={`w-1.5 h-1.5 rounded-full ${!isDeleted && tenant.is_active && (daysLeft === null || daysLeft >= 0) ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                                            {isDeleted ? (t('super_admin.tenants.archived', 'مؤرشف') || 'مؤرشف') : (!tenant.is_active || (daysLeft !== null && daysLeft < 0) ? (t('super_admin.tenants.inactive', 'غير نشط') || 'غير نشط') : (t('super_admin.tenants.active', 'نشط') || 'نشط'))}
                                        </span>
                                    </td>

                                    <td className="p-5 text-center">
                                        <div className="flex justify-center">
                                            {daysLeft !== null ? (
                                                <div className={`flex items-center gap-1.5 font-bold text-xs ${daysLeft < 7 ? 'text-rose-500' : 'text-slate-600 dark:text-slate-400'}`}>
                                                    <Clock size={15} />
                                                    <span>{daysLeft} {t('common.days', 'يوم')}</span>
                                                </div>
                                            ) : (
                                                <span className="text-slate-400 text-xl font-bold">∞</span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="p-5 font-extrabold text-emerald-600 dark:text-emerald-400 text-sm text-start">
                                        {Number(tenant.total_revenue || 0).toLocaleString()} {t('super_admin.finance.currency', 'USD')}
                                    </td>
                                    <td className="p-5 text-center">
                                        {!isDeleted ? (
                                            <div className="flex items-center justify-center gap-1.5">
                                                <button
                                                    type="button"
                                                    onClick={() => onSelectTenant && onSelectTenant(tenant.id)}
                                                    className="inline-flex items-center justify-center w-8 h-8 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:hover:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 rounded-xl transition-all cursor-pointer"
                                                    title={t('super_admin.tenants.details', 'تفاصيل العيادة')}
                                                >
                                                    <Edit3 size={15} />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => onManualRenew && onManualRenew(tenant)}
                                                    className="inline-flex items-center justify-center w-8 h-8 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:hover:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 rounded-xl transition-all cursor-pointer"
                                                    title={t('super_admin.tenants.manual_renewal', 'تجديد اشتراك يدوي')}
                                                >
                                                    <CalendarPlus size={15} />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => onResetPassword && onResetPassword(tenant.id)}
                                                    className="inline-flex items-center justify-center w-8 h-8 bg-amber-50 hover:bg-amber-100 dark:bg-amber-900/30 dark:hover:bg-amber-900/50 text-amber-600 dark:text-amber-400 rounded-xl transition-all cursor-pointer"
                                                    title={t('super_admin.tenants.reset_password', 'إعادة تعيين كلمة المرور')}
                                                >
                                                    <Key size={15} />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => handleArchiveTenant(tenant.id)}
                                                    className="inline-flex items-center justify-center w-8 h-8 bg-rose-50 hover:bg-rose-100 dark:bg-rose-900/30 dark:hover:bg-rose-900/50 text-rose-600 dark:text-rose-400 rounded-xl transition-all cursor-pointer"
                                                    title={t('super_admin.tenants.archive_action', 'أرشفة العيادة (قابلة للاستعادة)')}
                                                >
                                                    <Trash2 size={15} />
                                                </button>
                                            </div>
                                        ) : (
                                            <div className="flex items-center justify-center gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => handleRestoreTenant(tenant.id)}
                                                    className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-emerald-100 hover:bg-emerald-200 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 rounded-xl text-xs font-bold transition-all cursor-pointer"
                                                >
                                                    <RotateCcw size={14} />
                                                    <span>{t('super_admin.tenants.restore', 'استعادة')}</span>
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => handlePermanentDelete(tenant.id)}
                                                    className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm cursor-pointer"
                                                    title={t('super_admin.tenants.permanent_delete_title', 'حذف نهائي مدمر')}
                                                >
                                                    <Trash2 size={14} />
                                                    <span>{t('super_admin.tenants.permanent_short', 'حذف نهائي')}</span>
                                                </button>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                        {tenants.length === 0 && (
                            <tr>
                                <td colSpan="6" className="p-10 text-center text-slate-400 font-bold">{t('super_admin.tenants.no_tenants', 'لا توجد عيادات مسجلة')}</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default TenantsManager;

import React from 'react';
import { Edit3, Clock, PlusCircle, Trash2, Key } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const TenantsManager = ({ 
    tenants, 
    plans, 
    handlePlanChange, 
    setShowPaymentModal, 
    setPaymentForm, 
    getDaysRemaining, 
    handleArchiveTenant, 
    handleRestoreTenant, 
    handlePermanentDelete, 
    onResetPassword,
    onSelectTenant
}) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="overflow-x-auto">
                <table className={`w-full ${isRtl ? 'text-right' : 'text-left'}`}>
                    <thead>
                        <tr className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase tracking-wider">
                            <th className="p-6">{t('super_admin.tenants.title')}</th>
                            <th className="p-6">{t('super_admin.tenants.plan')}</th>
                            <th className="p-6 text-center">{t('super_admin.tenants.status')}</th>
                            <th className="p-6 text-center">{t('super_admin.tenants.duration')}</th>
                            <th className="p-6">{t('super_admin.tenants.revenue')}</th>
                            <th className="p-6 text-center">{t('super_admin.tenants.actions')}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {(tenants || []).map((tenant) => {
                            const daysLeft = getDaysRemaining(tenant.subscription_end_date);
                            const isDeleted = tenant.is_deleted;

                            return (
                                <tr key={tenant.id} className={`transition-colors ${isDeleted ? 'bg-red-50 dark:bg-red-900/10' : 'hover:bg-slate-50/50 dark:hover:bg-slate-800/50'}`}>
                                    <td className="p-6 font-bold text-slate-800 dark:text-slate-200">
                                        <div className="flex items-center gap-3 cursor-pointer group" onClick={() => onSelectTenant && onSelectTenant(tenant.id)}>
                                            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-transform group-hover:scale-110 ${isDeleted ? 'bg-red-100 text-red-600' : 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/50 dark:text-indigo-400'}`}>
                                                {tenant.name.charAt(0)}
                                            </div>
                                            <div className="flex flex-col">
                                                <span className="group-hover:text-indigo-600 transition-colors">{tenant.name}</span>
                                                <span className="text-[10px] text-slate-400 font-normal" dir="ltr">{tenant.domain}.dentix.com</span>
                                                {isDeleted && <span className="text-xs text-red-500 font-bold">({t('super_admin.tenants.archived')})</span>}
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-6">
                                        {!isDeleted ? (
                                            <div className="relative">
                                                <select
                                                    value={tenant.plan_id || ''}
                                                    onChange={(e) => handlePlanChange(e, tenant.id)}
                                                    className={`appearance-none w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 py-2 ${isRtl ? 'pr-4 pl-10' : 'pl-4 pr-10'} rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium cursor-pointer`}
                                                >
                                                    <option value="" disabled>{t('super_admin.tenants.select_plan')}</option>
                                                    {(plans || []).map(p => (
                                                        <option key={p.id} value={p.id}>{i18n.language === 'ar' ? p.display_name_ar : p.display_name_en || p.name}</option>
                                                    ))}
                                                </select>
                                                <Edit3 size={16} className={`absolute ${isRtl ? 'left-3' : 'right-3'} top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none`} />
                                            </div>
                                        ) : (
                                            <span className="text-slate-500">-</span>
                                        )}
                                    </td>
                                    <td className="p-6 text-center">
                                        <span className={`px-4 py-1.5 rounded-full text-xs font-bold inline-flex items-center gap-1.5 ${tenant.is_active && (!daysLeft || daysLeft > 0)
                                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                            : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400'
                                            }`}>
                                            <span className={`w-2 h-2 rounded-full ${tenant.is_active && (!daysLeft || daysLeft > 0) ? 'bg-emerald-500' : 'bg-rose-500'
                                                }`} />
                                            {tenant.is_active && (!daysLeft || daysLeft > 0) ? t('super_admin.tenants.active') : t('super_admin.tenants.inactive')}
                                        </span>
                                    </td>
                                    <td className="p-6">
                                        <div className="flex justify-center">
                                            {daysLeft !== null ? (
                                                <div className={`flex items-center gap-2 font-bold ${daysLeft < 7 ? 'text-rose-500' : 'text-slate-600 dark:text-slate-400'
                                                    }`}>
                                                    <Clock size={16} />
                                                    {t('super_admin.tenants.days_remaining', { count: daysLeft })}
                                                </div>
                                            ) : (
                                                <span className="text-slate-500 text-2xl">∞</span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="p-6 font-bold text-emerald-600 dark:text-emerald-400">
                                        {tenant.total_revenue?.toLocaleString() || 0} {t('super_admin.finance.currency')}
                                    </td>
                                    <td className="p-6 text-center flex items-center justify-center gap-2">
                                        {!isDeleted ? (
                                            <>
                                                <button
                                                    onClick={() => onSelectTenant && onSelectTenant(tenant.id)}
                                                    className="inline-flex items-center gap-2 px-3 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-xl text-xs font-bold transition-all"
                                                    title={t('super_admin.tenants.details')}
                                                >
                                                    <Edit3 size={16} />
                                                </button>
                                                <button
                                                    onClick={() => {
                                                        onResetPassword && onResetPassword(tenant.id);
                                                    }}
                                                    className="inline-flex items-center gap-2 px-3 py-2 bg-amber-100 hover:bg-amber-200 text-amber-600 rounded-xl text-xs font-bold transition-all"
                                                    title={t('super_admin.tenants.reset_password')}
                                                >
                                                    <Key size={16} />
                                                </button>
                                                <button
                                                    onClick={() => handleArchiveTenant(tenant.id)}
                                                    className="inline-flex items-center gap-2 px-3 py-2 bg-rose-100 hover:bg-rose-200 text-rose-600 rounded-xl text-xs font-bold transition-all"
                                                    title={t('super_admin.tenants.delete')}
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </>
                                        ) : (
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => handleRestoreTenant(tenant.id)}
                                                    className="inline-flex items-center gap-2 px-3 py-2 bg-emerald-100 hover:bg-emerald-200 text-emerald-600 rounded-xl text-xs font-bold transition-all"
                                                >
                                                    {t('super_admin.tenants.restore')}
                                                </button>
                                                <button
                                                    onClick={() => handlePermanentDelete(tenant.id)}
                                                    className="inline-flex items-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-red-500/30"
                                                    title={t('super_admin.tenants.permanent_delete_confirm')}
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                        {tenants.length === 0 && (
                            <tr>
                                <td colSpan="6" className="p-10 text-center text-slate-500">{t('super_admin.tenants.no_tenants')}</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default TenantsManager;


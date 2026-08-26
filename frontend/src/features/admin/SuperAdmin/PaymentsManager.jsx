import { Banknote, Landmark, CreditCard, Check, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const PaymentsManager = ({ payments, tenants, plans, onDelete }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="overflow-x-auto w-full">
                <table className={`w-full ${isRtl ? 'text-right' : 'text-left'}`}>
                    <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase">
                        <tr>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.payments.date_col')}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.payments.tenant_col')}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.payments.plan_col')}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.payments.amount_col')}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.payments.paid_by_col')}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.payments.method_col')}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.payments.status_col')}</th>
                            <th className="p-6 whitespace-nowrap">{t('super_admin.payments.actions_col')}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {(Array.isArray(payments) && payments.length > 0) ? payments.map(payment => {
                            const tenantName = Array.isArray(tenants) ? (tenants.find(t => t.id === payment.tenant_id)?.name || tenants.find(t => t.id === payment.tenant_id)?.clinic_name) : '-';
                            const planObj = Array.isArray(plans) ? plans.find(p => p.id === payment.plan_id) : null;
                            const planName = planObj ? (isRtl ? planObj.display_name_ar : planObj.display_name_en || planObj.name) : '-';
                            const amountFormatted = payment.amount != null ? Number(payment.amount).toLocaleString(isRtl ? 'ar-EG' : 'en-US') : '0';
                            const dateFormatted = payment.payment_date ? new Date(payment.payment_date).toLocaleDateString(isRtl ? 'ar-EG' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : '-';

                            return (
                                <tr key={payment.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                                    <td className="p-6 font-medium text-sm text-slate-600 dark:text-slate-400 whitespace-nowrap">
                                        {dateFormatted}
                                    </td>
                                    <td className="p-6 font-bold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                                        {tenantName || '-'}
                                    </td>
                                    <td className="p-6 text-sm font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
                                        {planName || '-'}
                                    </td>
                                    <td className="p-6 font-bold text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                                        +{amountFormatted} {t('super_admin.finance.currency')}
                                    </td>
                                    <td className="p-6 text-sm font-bold text-slate-700 dark:text-slate-300 whitespace-nowrap">
                                        {payment.paid_by || '-'}
                                    </td>
                                    <td className="p-6 whitespace-nowrap">
                                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold ${payment.payment_method === 'cash' ? 'bg-green-100 text-green-700' :
                                            payment.payment_method === 'bank_transfer' ? 'bg-blue-100 text-blue-700' :
                                                'bg-teal-100 text-teal-700'
                                            }`}>
                                            {payment.payment_method === 'cash' && <Banknote size={14} />}
                                            {payment.payment_method === 'bank_transfer' && <Landmark size={14} />}
                                            {payment.payment_method === 'credit_card' && <CreditCard size={14} />}

                                            {payment.payment_method === 'cash' ? t('super_admin.payments.cash') :
                                                payment.payment_method === 'bank_transfer' ? t('super_admin.payments.bank_transfer') :
                                                    t('super_admin.payments.credit_card')}
                                        </span>
                                    </td>
                                    <td className="p-6 whitespace-nowrap">
                                        <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-sm font-bold">
                                            <Check size={16} /> {t('super_admin.payments.completed')}
                                        </div>
                                    </td>
                                    <td className="p-6 whitespace-nowrap">
                                        <button
                                            onClick={() => onDelete && onDelete(payment.id)}
                                            className="p-2 text-rose-500 hover:bg-rose-50 rounded-lg transition-colors"
                                            title={t('super_admin.payments.delete_title')}
                                            aria-label={t('super_admin.payments.delete_title') || 'Delete Payment'}
                                        >
                                            <Trash2 size={18} />
                                        </button>
                                    </td>
                                </tr>
                            );
                        }) : (
                            <tr>
                                <td colSpan="8" className="p-10 text-center text-slate-500">{t('super_admin.payments.no_payments')}</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default PaymentsManager;

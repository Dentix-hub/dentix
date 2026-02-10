import { useState } from 'react';
import { Printer, Trash2 } from 'lucide-react';
import { fdiToPalmer } from '@/utils/toothUtils';
import { useTranslation } from 'react-i18next';
const PatientBilling = ({
    patientId,
    history,
    payments,
    onAddPayment,
    onDeletePayment,
    onPrintInvoice
}) => {
    const { t } = useTranslation();
    const [billingTab, setBillingTab] = useState('invoices');
    const totalTreatments = history.reduce((acc, curr) => acc + (curr.cost - (curr.discount || 0)), 0);
    const totalPayments = payments.reduce((acc, curr) => acc + curr.amount, 0);
    const totalRemaining = totalTreatments - totalPayments;
    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
            {/* Sub Tabs and Print Button */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-200 pb-4">
                <div className="flex bg-slate-100 p-1.5 rounded-xl">
                    <button
                        onClick={() => setBillingTab('invoices')}
                        className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${billingTab === 'invoices' ? 'bg-white text-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        {t('patientDetails.billing.tabs.invoices')}
                    </button>
                    <button
                        onClick={() => setBillingTab('payments')}
                        className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${billingTab === 'payments' ? 'bg-white text-emerald-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        {t('patientDetails.billing.tabs.payments')}
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={onAddPayment} className="text-white bg-emerald-500 hover:bg-emerald-600 px-4 py-2 rounded-xl text-sm font-bold transition-colors shadow-lg shadow-emerald-500/20">
                        {t('patientDetails.billing.add_payment')}
                    </button>
                    <button onClick={onPrintInvoice} className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white font-bold rounded-xl hover:bg-slate-900 shadow-lg shadow-slate-800/20 text-sm">
                        <Printer size={16} /> {t('patientDetails.billing.print_invoice')}
                    </button>
                </div>
            </div>
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                    <p className="text-xs text-slate-500 font-bold uppercase mb-1">{t('patientDetails.billing.stats.total_treatments')}</p>
                    <p className="text-2xl font-bold text-slate-800">
                        {totalTreatments}
                    </p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                    <p className="text-xs text-slate-500 font-bold uppercase mb-1">{t('patientDetails.billing.stats.paid')}</p>
                    <p className="text-2xl font-bold text-emerald-600">{totalPayments}</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                    <p className="text-xs text-slate-500 font-bold uppercase mb-1">{t('patientDetails.billing.stats.remaining')}</p>
                    <p className="text-2xl font-bold text-slate-400">
                        {totalRemaining}
                    </p>
                </div>
            </div>
            {/* Invoices Tab Content */}
            {billingTab === 'invoices' && (
                <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                    <div className="p-4 border-b border-slate-50 bg-slate-50/50 flex justify-between items-center">
                        <h3 className="font-bold text-slate-700">{t('patientDetails.billing.invoices_title')}</h3>
                        <span className="text-xs bg-slate-200 text-slate-600 px-2 py-1 rounded-md">{t('patientDetails.billing.procedure_count', { count: history.length })}</span>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-right">
                            <thead className="bg-slate-50 text-slate-600 text-sm font-bold">
                                <tr>
                                    <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.table.date')}</th>
                                    <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.table.treatment')}</th>
                                    <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.table.cost')}</th>
                                    <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.table.discount')}</th>
                                    <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.table.net')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50">
                                {history.map(item => (
                                    <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="p-4 whitespace-nowrap text-sm text-slate-600">{new Date(item.date).toLocaleDateString()}</td>
                                        <td className="p-4 font-bold text-slate-700">{item.procedure} <span className="text-xs font-normal text-slate-400">({fdiToPalmer(item.tooth_number) || ''})</span></td>
                                        <td className="p-4 font-bold text-slate-800">{item.cost}</td>
                                        <td className="p-4 text-red-500">{item.discount > 0 ? item.discount : '-'}</td>
                                        <td className="p-4 font-bold text-emerald-600">{item.cost - (item.discount || 0)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {history.length === 0 && <div className="p-8 text-center text-slate-400">{t('patientDetails.billing.empty_treatments')}</div>}
                </div>
            )}
            {/* Payments Tab Content */}
            {billingTab === 'payments' && (
                <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                    <div className="p-4 border-b border-slate-50 flex justify-between items-center bg-slate-50/50">
                        <h3 className="font-bold text-slate-700">{t('patientDetails.billing.payments_title')}</h3>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-right">
                            <thead className="bg-slate-50 text-slate-600 text-sm font-bold">
                                <tr>
                                    <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.table.date')}</th>
                                    <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.table.amount')}</th>
                                    <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.table.notes')}</th>
                                    <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.table.actions')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50">
                                {payments.map(item => (
                                    <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="p-4 whitespace-nowrap">{new Date(item.date).toLocaleDateString()}</td>
                                        <td className="p-4 font-bold text-emerald-600 text-lg">{item.amount}</td>
                                        <td className="p-4 text-slate-500">{item.notes || '-'}</td>
                                        <td className="p-4">
                                            <button onClick={() => onDeletePayment(item.id)} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"><Trash2 size={16} /></button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {payments.length === 0 && <div className="p-8 text-center text-slate-400">{t('patientDetails.billing.empty_payments')}</div>}
                </div>
            )}
        </div>
    );
};
export default PatientBilling;

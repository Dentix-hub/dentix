import { useState } from 'react';
import { Printer, Trash2 } from 'lucide-react';
import { fdiToPalmer } from '@/utils/toothUtils';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTenantFeatures } from '@/hooks/usePatientDetails';
import { getPatientClinicalCharges, invoiceClinicalCharge, voidClinicalCharge } from '@/api/clinicalCharges';
import { toast } from '@/shared/ui';

const PatientBilling = ({
    _patientId,
    patientId,
    history = [],
    payments = [],
    onAddPayment,
    onDeletePayment,
    onPrintInvoice,
    tenantFeatures: propTenantFeatures,
}) => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [billingTab, setBillingTab] = useState('invoices');
    const [actionLoadingId, setActionLoadingId] = useState(null);

    const effectivePatientId = patientId || _patientId;
    const { data: queriedFeatures = [] } = useTenantFeatures();
    const effectiveFeatures = propTenantFeatures || queriedFeatures || [];
    const isFinanceReadEnabled = Array.isArray(effectiveFeatures) && effectiveFeatures.includes('clinical_vnext_finance_read');

    const { data: chargesResponse, isLoading: isLoadingCharges } = useQuery({
        queryKey: ['patient-clinical-charges', effectivePatientId],
        queryFn: () => getPatientClinicalCharges(effectivePatientId),
        enabled: Boolean(isFinanceReadEnabled && effectivePatientId),
    });

    const charges = chargesResponse?.data?.data?.charges || chargesResponse?.data?.charges || [];

    const invoiceMutation = useMutation({
        mutationFn: ({ chargeId, versionId }) =>
            invoiceClinicalCharge(chargeId, { expected_version_id: versionId }),
        onSuccess: () => {
            toast.success(t('patientDetails.billing.pending_charges.invoiced_success', 'Charge marked as invoiced'));
            queryClient.invalidateQueries({ queryKey: ['patient-clinical-charges', effectivePatientId] });
        },
        onError: (err) => {
            toast.error(err?.response?.data?.detail || t('patientDetails.billing.pending_charges.error_action', 'Failed to update charge'));
        },
        onSettled: () => setActionLoadingId(null),
    });

    const voidMutation = useMutation({
        mutationFn: ({ chargeId, versionId }) =>
            voidClinicalCharge(chargeId, { expected_version_id: versionId }),
        onSuccess: () => {
            toast.success(t('patientDetails.billing.pending_charges.voided_success', 'Charge voided'));
            queryClient.invalidateQueries({ queryKey: ['patient-clinical-charges', effectivePatientId] });
        },
        onError: (err) => {
            toast.error(err?.response?.data?.detail || t('patientDetails.billing.pending_charges.error_action', 'Failed to update charge'));
        },
        onSettled: () => setActionLoadingId(null),
    });

    const handleInvoice = (charge) => {
        setActionLoadingId(charge.id);
        invoiceMutation.mutate({ chargeId: charge.id, versionId: charge.version_id });
    };

    const handleVoid = (charge) => {
        setActionLoadingId(charge.id);
        voidMutation.mutate({ chargeId: charge.id, versionId: charge.version_id });
    };

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
                    <p className="text-2xl font-bold text-slate-500">
                        {totalRemaining}
                    </p>
                </div>
            </div>

            {/* Pending Clinical Charges Card (gated by clinical_vnext_finance_read) */}
            {isFinanceReadEnabled && (
                <div data-testid="pending-clinical-charges-card" className="bg-white rounded-2xl border border-slate-100 overflow-hidden shadow-sm animate-in fade-in zoom-in-95 duration-200">
                    <div className="p-4 border-b border-slate-50 bg-slate-50/50 flex justify-between items-center">
                        <h3 className="font-bold text-slate-700">
                            {t('patientDetails.billing.pending_charges.title', 'Pending Clinical Charges')}
                        </h3>
                        <span className="text-xs bg-amber-100 text-amber-700 font-semibold px-2.5 py-1 rounded-md">
                            {charges.filter(c => c.status === 'pending').length}
                        </span>
                    </div>
                    {isLoadingCharges ? (
                        <div className="p-8 text-center text-slate-400">...</div>
                    ) : charges.length === 0 ? (
                        <div className="p-8 text-center text-slate-500">
                            {t('patientDetails.billing.pending_charges.empty', 'No pending clinical charges')}
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-right">
                                <thead className="bg-slate-50 text-slate-600 text-sm font-bold">
                                    <tr>
                                        <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.pending_charges.table.date', 'Date')}</th>
                                        <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.pending_charges.table.work_item', 'Work Item')}</th>
                                        <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.pending_charges.table.amount', 'Amount')}</th>
                                        <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.pending_charges.table.status', 'Status')}</th>
                                        <th className="p-4 whitespace-nowrap">{t('patientDetails.billing.pending_charges.table.actions', 'Actions')}</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-50">
                                    {charges.map(charge => (
                                        <tr key={charge.id} className="hover:bg-slate-50 transition-colors">
                                            <td className="p-4 whitespace-nowrap text-sm text-slate-600">
                                                {charge.created_at ? new Date(charge.created_at).toLocaleDateString() : '-'}
                                            </td>
                                            <td className="p-4 font-bold text-slate-700">
                                                #{charge.work_item_id}
                                            </td>
                                            <td className="p-4 font-bold text-slate-800">
                                                {charge.amount}
                                            </td>
                                            <td className="p-4">
                                                {charge.status === 'pending' && (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                                                        {t('patientDetails.billing.pending_charges.status_pending', 'Pending')}
                                                    </span>
                                                )}
                                                {charge.status === 'invoiced' && (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                                                        {t('patientDetails.billing.pending_charges.status_invoiced', 'Invoiced')}
                                                    </span>
                                                )}
                                                {charge.status === 'voided' && (
                                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">
                                                        {t('patientDetails.billing.pending_charges.status_voided', 'Voided')}
                                                    </span>
                                                )}
                                            </td>
                                            <td className="p-4 whitespace-nowrap">
                                                {charge.status === 'pending' ? (
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            type="button"
                                                            onClick={() => handleInvoice(charge)}
                                                            disabled={actionLoadingId === charge.id}
                                                            className="px-3 py-1 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-sm transition-colors"
                                                        >
                                                            {t('patientDetails.billing.pending_charges.invoice_btn', 'Invoice')}
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() => handleVoid(charge)}
                                                            disabled={actionLoadingId === charge.id}
                                                            className="px-3 py-1 bg-slate-200 hover:bg-red-100 hover:text-red-700 disabled:opacity-50 text-slate-700 text-xs font-bold rounded-lg transition-colors"
                                                        >
                                                            {t('patientDetails.billing.pending_charges.void_btn', 'Void')}
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <span className="text-xs text-slate-400">-</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

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
                                        <td className="p-4 font-bold text-slate-700">{item.procedure} <span className="text-xs font-normal text-slate-500">({fdiToPalmer(item.tooth_number) || ''})</span></td>
                                        <td className="p-4 font-bold text-slate-800">{item.cost}</td>
                                        <td className="p-4 text-red-500">{item.discount > 0 ? item.discount : '-'}</td>
                                        <td className="p-4 font-bold text-emerald-600">{item.cost - (item.discount || 0)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {history.length === 0 && <div className="p-8 text-center text-slate-500">{t('patientDetails.billing.empty_treatments')}</div>}
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
                                            <button onClick={() => onDeletePayment(item.id)} className="p-2 text-slate-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"><Trash2 size={16} /></button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {payments.length === 0 && <div className="p-8 text-center text-slate-500">{t('patientDetails.billing.empty_payments')}</div>}
                </div>
            )}
        </div>
    );
};

export default PatientBilling;

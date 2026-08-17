import { Modal } from '@/shared/ui';
import { Calendar, Phone, Clock, FileText, Landmark } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { getPatientReportDetails } from '@/api';

export default function PatientFinancialModal({
    isOpen,
    onClose,
    patientId,
    startDate,
    endDate,
    periodLabel,
    formatCurrency
}) {
    const { t } = useTranslation();

    const { data: detailData, isLoading: detailLoading } = useQuery({
        queryKey: ['patient_report_details', patientId, startDate, endDate],
        queryFn: async () => {
            if (!patientId) return null;
            const res = await getPatientReportDetails(patientId, {
                start_date: startDate,
                end_date: endDate,
            });
            return res.data;
        },
        enabled: !!patientId && isOpen
    });

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={t('billing.summary.patient_details_title', 'Patient Financial File')}
            size="xl"
        >
            {detailLoading ? (
                <div className="p-12 text-center text-slate-500 font-bold">{t('common.loading', 'Loading details...')}</div>
            ) : !detailData ? (
                <div className="p-6 text-center text-red-500 font-bold">{t('common.error_loading_data', 'Error loading data.')}</div>
            ) : (
                <div className="space-y-6">
                    {periodLabel && (
                        <div className="flex items-center gap-2 text-sm font-bold text-primary bg-primary/5 border border-primary/10 rounded-xl px-3 py-2">
                            <Calendar size={15} />
                            {t('billing.summary.details_scope', 'Financial activity in')}: {periodLabel}
                        </div>
                    )}
                    {/* Patient Summary Header */}
                    <div className="bg-slate-50 dark:bg-slate-800/30 p-6 rounded-2xl border border-border grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="space-y-1">
                            <span className="text-xs font-bold uppercase tracking-widest text-text-secondary">{t('billing.summary.patient_name', 'Patient Name')}</span>
                            <div className="flex items-center gap-2">
                                <span className="px-2 py-0.5 rounded-lg bg-primary text-white font-bold text-xs">#{detailData.file_number || detailData.patient_id}</span>
                                <h4 className="text-lg font-black text-slate-800 dark:text-white">{detailData.patient_name}</h4>
                            </div>
                            <div className="flex items-center gap-1.5 text-xs text-text-secondary font-bold font-mono">
                                <Phone size={12} />
                                <span>{detailData.patient_phone}</span>
                            </div>
                        </div>
                        <div className="space-y-1">
                            <span className="text-xs font-bold uppercase tracking-widest text-text-secondary">{t('billing.summary.next_due_date', 'Next Appointment Date')}</span>
                            <div className="flex items-center gap-1.5 text-sm text-text-primary font-bold">
                                <Clock size={14} className="text-primary" />
                                <span>
                                    {detailData.next_due_date
                                        ? new Date(detailData.next_due_date).toLocaleString()
                                        : t('common.none', 'None')}
                                </span>
                            </div>
                        </div>
                        <div className="space-y-1">
                            <span className="text-xs font-bold uppercase tracking-widest text-text-secondary">{t('billing.summary.period_balance', 'Period Balance')}</span>
                            <div className={`text-2xl font-black font-mono ${(detailData.period_balance ?? detailData.outstanding_balance) > 0 ? 'text-amber-600 dark:text-amber-400 animate-pulse' : 'text-emerald-600 dark:text-emerald-400'}`}>
                                {formatCurrency(detailData.period_balance ?? detailData.outstanding_balance)}
                            </div>
                        </div>
                    </div>

                    {/* Totals Section */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 bg-slate-50 dark:bg-slate-800/30 rounded-xl border border-border flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-600 dark:text-slate-400">
                                    <FileText size={20} />
                                </div>
                                <span className="text-sm font-bold text-text-secondary">{t('billing.summary.total_invoiced', 'Total Invoiced')}</span>
                            </div>
                            <span className="text-lg font-black font-mono">{formatCurrency(detailData.total_invoiced)}</span>
                        </div>
                        <div className="p-4 bg-emerald-50 dark:bg-emerald-950/10 rounded-xl border border-emerald-100 dark:border-emerald-950/20 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 bg-emerald-100 dark:bg-emerald-900/30 rounded-xl text-emerald-600 dark:text-emerald-400">
                                    <Landmark size={20} />
                                </div>
                                <span className="text-sm font-bold text-emerald-700 dark:text-emerald-400">{t('billing.summary.total_paid', 'Total Paid')}</span>
                            </div>
                            <span className="text-lg font-black font-mono text-emerald-600 dark:text-emerald-400">{formatCurrency(detailData.total_paid)}</span>
                        </div>
                    </div>

                    {/* History Lists */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Payment History */}
                        <div className="space-y-3">
                            <h5 className="font-bold text-base text-text-primary flex items-center gap-2 border-b border-border pb-2">
                                <Landmark size={18} className="text-emerald-500" />
                                {t('billing.summary.payment_history', 'Payment History')}
                            </h5>
                            <div className="max-h-[300px] overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                                {detailData.payment_history?.length === 0 ? (
                                    <p className="text-sm text-text-muted italic py-4 text-center">
                                        {t('billing.summary.no_payments', 'No payments recorded.')}
                                    </p>
                                ) : (
                                    detailData.payment_history?.map((p) => (
                                        <div key={p.id} className="p-3 bg-white dark:bg-slate-900 rounded-xl border border-border flex justify-between items-start gap-4 hover:shadow-sm transition-shadow">
                                            <div className="space-y-0.5">
                                                <span className="text-xs text-text-secondary font-mono">{new Date(p.date).toLocaleDateString()}</span>
                                                {p.notes && <p className="text-xs text-text-muted leading-relaxed">{p.notes}</p>}
                                            </div>
                                            <span className="font-bold font-mono text-emerald-600 dark:text-emerald-400">{formatCurrency(p.amount)}</span>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Treatment History */}
                        <div className="space-y-3">
                            <h5 className="font-bold text-base text-text-primary flex items-center gap-2 border-b border-border pb-2">
                                <FileText size={18} className="text-primary" />
                                {t('billing.summary.treatment_history', 'Treatment & Procedure History')}
                            </h5>
                            <div className="max-h-[300px] overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                                {detailData.treatment_history?.length === 0 ? (
                                    <p className="text-sm text-text-muted italic py-4 text-center">
                                        {t('billing.summary.no_treatments', 'No treatments recorded.')}
                                    </p>
                                ) : (
                                    detailData.treatment_history?.map((t_item) => (
                                        <div key={t_item.id} className="p-3 bg-white dark:bg-slate-900 rounded-xl border border-border space-y-2 hover:shadow-sm transition-shadow">
                                            <div className="flex justify-between items-start">
                                                <div className="space-y-0.5">
                                                    <span className="text-xs text-text-secondary font-mono">{new Date(t_item.date).toLocaleDateString()}</span>
                                                    <h6 className="font-bold text-sm">{t_item.procedure}</h6>
                                                    <p className="text-xs text-text-secondary">{t_item.diagnosis}</p>
                                                </div>
                                                <span className="font-bold font-mono text-slate-800 dark:text-white">{formatCurrency(t_item.net)}</span>
                                            </div>
                                            {(t_item.discount > 0 || t_item.cost !== t_item.net) && (
                                                <div className="flex gap-4 text-[10px] text-text-secondary font-bold font-mono border-t border-dashed border-border pt-1.5">
                                                    <span>{t('billing.summary.cost', 'Cost')}: {formatCurrency(t_item.cost)}</span>
                                                    <span className="text-red-500">{t('billing.summary.discount', 'Discount')}: -{formatCurrency(t_item.discount)}</span>
                                                </div>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Modal>
    );
}

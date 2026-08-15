import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    TrendingUp,
    Banknote,
    DollarSign,
    Calendar,
    ChevronLeft,
    ChevronRight,
    X,
    Phone,
    Clock,
    FileText,
    Landmark
} from 'lucide-react';
import { Button, Card, StatCard, DateTimePicker, PatientSelect, Modal } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
import { getPatientsReport, getPatientReportDetails } from '@/api';

const SummaryTab = ({
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    comprehensiveStats,
    _loading,
    patients = [],
    selectedPatientId,
    setSelectedPatientId
}) => {
    const { t } = useTranslation();
    const [page, setPage] = useState(0);
    const [outstandingOnly, setOutstandingOnly] = useState(false);
    const [detailPatientId, setDetailPatientId] = useState(null);
    const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
    const limit = 10;

    const { data: reportData, isLoading: reportLoading } = useQuery({
        queryKey: ['patients_report', selectedPatientId, outstandingOnly, page],
        queryFn: async () => {
            const res = await getPatientsReport({
                patient_id: selectedPatientId || undefined,
                outstanding_only: outstandingOnly,
                skip: page * limit,
                limit: limit
            });
            return res.data;
        }
    });

    const { data: detailData, isLoading: detailLoading } = useQuery({
        queryKey: ['patient_report_details', detailPatientId],
        queryFn: async () => {
            if (!detailPatientId) return null;
            const res = await getPatientReportDetails(detailPatientId);
            return res.data;
        },
        enabled: !!detailPatientId
    });

    const handleViewDetails = (patientId) => {
        setDetailPatientId(patientId);
        setIsDetailModalOpen(true);
    };

    const handleCloseDetails = () => {
        setIsDetailModalOpen(false);
        setDetailPatientId(null);
    };

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-EG', { style: 'currency', currency: 'EGP', maximumFractionDigits: 0 }).format(amount);
    };

    const reportPatients = reportData?.patients || [];
    const reportTotal = reportData?.total || 0;
    const totalPages = Math.ceil(reportTotal / limit);

    return (
        <div className="space-y-6">
            {/* Filter Panel: Date Range and Patient Filter */}
            <Card className="p-6">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-end">
                    <div className="lg:col-span-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                        <DateTimePicker
                            label={t('billing.summary.from')}
                            mode="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                        />
                        <DateTimePicker
                            label={t('billing.summary.to')}
                            mode="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                        />
                    </div>
                    <div className="lg:col-span-6 flex flex-col md:flex-row items-end gap-4">
                        <div className="flex-1 w-full">
                            <label className="block text-sm font-bold text-text-primary mb-1.5">
                                {t('billing.summary.patient_filter', 'Filter by Patient')}
                            </label>
                            <PatientSelect
                                patients={patients}
                                value={selectedPatientId}
                                onChange={(e) => {
                                    setSelectedPatientId(e.target.value);
                                    setPage(0);
                                }}
                                placeholder={t('billing.summary.patient_filter', 'Filter by Patient')}
                            />
                        </div>
                        {selectedPatientId && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                    setSelectedPatientId('');
                                    setPage(0);
                                }}
                                className="text-red-500 hover:text-red-700 font-bold border border-red-200 hover:border-red-300 px-4 py-3 rounded-xl transition-all"
                            >
                                <X size={16} className="inline me-1" />
                                {t('billing.summary.clear_filter', 'Clear')}
                            </Button>
                        )}
                    </div>
                </div>
            </Card>

            {/* Header Cards - Income */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard
                    title={t('billing.summary.total_revenue')}
                    value={`${(comprehensiveStats?.income?.total_revenue || 0).toLocaleString()}`}
                    icon={TrendingUp}
                    color="success"
                />
                <StatCard
                    title={t('billing.summary.total_collected')}
                    value={`${(comprehensiveStats?.income?.total_collected || 0).toLocaleString()}`}
                    icon={Banknote}
                    color="info"
                />
                <StatCard
                    title={t('billing.summary.outstanding')}
                    value={`${(comprehensiveStats?.income?.outstanding || 0).toLocaleString()}`}
                    icon={DollarSign}
                    color="warning"
                />
                <StatCard
                    title={t('billing.summary.patient_count')}
                    value={comprehensiveStats?.income?.unique_patients || 0}
                    icon={Calendar}
                    color="primary"
                />
            </div>

            {/* Deductions Breakdown */}
            <Card className="overflow-hidden">
                <div className="p-6 border-b border-border flex items-center gap-4 bg-surface">
                    <div className="w-1.5 h-8 bg-danger rounded-full"></div>
                    <h3 className="font-bold text-xl text-text-primary">{t('billing.summary.deductions_title')}</h3>
                </div>
                <div className="p-6 space-y-4">
                    {/* Doctor Dues */}
                    <div className="p-4 bg-teal-50 dark:bg-teal-900/10 rounded-xl border border-teal-100 dark:border-teal-900/20">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="font-bold text-teal-700 dark:text-teal-400">{t('billing.summary.doctor_dues')}</h4>
                            <span className="font-bold text-xl text-teal-600">-{(comprehensiveStats?.deductions?.doctor_dues?.total || 0).toLocaleString()}</span>
                        </div>
                        {comprehensiveStats?.deductions?.doctor_dues?.details?.map(doc => (
                            <div key={doc.id} className="flex items-center justify-between text-sm py-1 border-t border-teal-100 dark:border-teal-900/20">
                                <span className="text-text-secondary">{doc.name} - {t('billing.summary.commission')} {doc.commission_percent}% + {t('billing.summary.salary')} {doc.fixed_salary}</span>
                                <span className="font-bold text-teal-600">{doc.total_due.toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                    {/* Staff Dues */}
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-xl border border-blue-100 dark:border-blue-900/20">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="font-bold text-blue-700 dark:text-blue-400">{t('billing.summary.staff_dues')}</h4>
                            <span className="font-bold text-xl text-blue-600">-{(comprehensiveStats?.deductions?.staff_dues?.total || 0).toLocaleString()}</span>
                        </div>
                        {comprehensiveStats?.deductions?.staff_dues?.details?.map(s => (
                            <div key={s.id} className="flex items-center justify-between text-sm py-1 border-t border-blue-100 dark:border-blue-900/20">
                                <span className="text-text-secondary">{s.name} - {t('billing.summary.salary')} {s.fixed_salary} + ({s.per_appointment_fee} × {s.appointments_in_period} {t('billing.summary.appointment')})</span>
                                <span className="font-bold text-blue-600">{s.total_due.toLocaleString()}</span>
                            </div>
                        ))}
                        {(!comprehensiveStats?.deductions?.staff_dues?.details?.length) && (
                            <p className="text-sm text-text-muted">{t('billing.summary.no_employees')}</p>
                        )}
                    </div>
                    {/* Lab Costs */}
                    <div className="p-4 bg-orange-50 dark:bg-orange-900/10 rounded-xl border border-orange-100 dark:border-orange-900/20">
                        <div className="flex items-center justify-between">
                            <h4 className="font-bold text-orange-700 dark:text-orange-400">{t('billing.summary.lab_costs')}</h4>
                            <span className="font-bold text-xl text-orange-600">-{(comprehensiveStats?.deductions?.lab_costs || 0).toLocaleString()}</span>
                        </div>
                    </div>
                    {/* Expenses */}
                    <div className="p-4 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-100 dark:border-red-900/20">
                        <div className="flex items-center justify-between">
                            <h4 className="font-bold text-red-700 dark:text-red-400">{t('billing.summary.other_expenses')}</h4>
                            <span className="font-bold text-xl text-red-600">-{(comprehensiveStats?.deductions?.expenses || 0).toLocaleString()}</span>
                        </div>
                    </div>
                </div>
            </Card>

            {/* Net Profit */}
            <div className={`p-8 rounded-2xl text-center ${(comprehensiveStats?.net_profit || 0) >= 0 ? 'bg-gradient-to-br from-emerald-500 to-emerald-600' : 'bg-gradient-to-br from-red-500 to-red-600'} text-white shadow-xl`}>
                <p className="text-white/80 font-bold mb-2">{t('billing.summary.net_profit_after')}</p>
                <p className="text-5xl font-bold">{(comprehensiveStats?.net_profit || 0).toLocaleString()}</p>
                <p className="text-sm text-white/60 mt-3">{t('billing.summary.net_profit_equation')}</p>
            </div>

            {/* Patients Financial Report Section */}
            <Card className="overflow-hidden">
                <div className="p-6 border-b border-border flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface">
                    <div className="flex items-center gap-4">
                        <div className="w-1.5 h-8 bg-primary rounded-full"></div>
                        <h3 className="font-bold text-xl text-text-primary">{t('billing.summary.patients_report_title', 'Patients Financial Report')}</h3>
                    </div>
                    <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 cursor-pointer select-none text-sm font-bold text-text-secondary">
                            <input
                                type="checkbox"
                                checked={outstandingOnly}
                                onChange={(e) => {
                                    setOutstandingOnly(e.target.checked);
                                    setPage(0);
                                }}
                                className="w-4 h-4 rounded border-border text-primary focus:ring-primary/20 cursor-pointer"
                            />
                            {t('billing.summary.outstanding_only', 'Outstanding Balance Only')}
                        </label>
                    </div>
                </div>

                <div className="p-0 overflow-x-auto">
                    {reportLoading ? (
                        <div className="p-8 text-center text-slate-500 font-bold">{t('common.loading', 'Loading data...')}</div>
                    ) : reportPatients.length === 0 ? (
                        <div className="p-12 text-center text-slate-500 italic font-bold">
                            {t('billing.summary.no_patients', 'No patient records found.')}
                        </div>
                    ) : (
                        <table className="w-full text-start border-collapse">
                            <thead>
                                <tr className="border-b border-border bg-slate-50 dark:bg-slate-800/50 text-[11px] font-bold uppercase tracking-widest text-text-secondary">
                                    <th className="p-4 text-start">{t('billing.summary.patient_name', 'Patient Name')}</th>
                                    <th className="p-4 text-end">{t('billing.summary.total_invoiced', 'Total Invoiced')}</th>
                                    <th className="p-4 text-end">{t('billing.summary.total_paid', 'Total Paid')}</th>
                                    <th className="p-4 text-end">{t('billing.summary.outstanding_balance', 'Outstanding Balance')}</th>
                                    <th className="p-4 text-center">{t('billing.summary.actions', 'Actions')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border text-sm font-medium text-text-primary">
                                {reportPatients.map((pat) => (
                                    <tr key={pat.patient_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                                        <td className="p-4">
                                            <div className="flex flex-col">
                                                <span className="font-bold text-slate-800 dark:text-white">{pat.patient_name}</span>
                                                <span className="text-xs text-text-secondary font-mono">{pat.patient_phone}</span>
                                            </div>
                                        </td>
                                        <td className="p-4 text-end font-bold font-mono">{formatCurrency(pat.total_invoiced)}</td>
                                        <td className="p-4 text-end font-bold font-mono text-emerald-600 dark:text-emerald-400">{formatCurrency(pat.total_paid)}</td>
                                        <td className={`p-4 text-end font-bold font-mono ${pat.outstanding_balance > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-500'}`}>
                                            {formatCurrency(pat.outstanding_balance)}
                                        </td>
                                        <td className="p-4 text-center">
                                            <Button
                                                variant="secondary"
                                                size="sm"
                                                onClick={() => handleViewDetails(pat.patient_id)}
                                                className="rounded-xl px-3 py-1.5 text-xs font-bold"
                                            >
                                                {t('billing.summary.view_details', 'Details')}
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Pagination */}
                {!reportLoading && totalPages > 1 && (
                    <div className="p-4 border-t border-border flex items-center justify-between">
                        <span className="text-xs font-bold text-text-secondary">
                            {t('common.page', 'Page')} {page + 1} {t('common.of', 'of')} {totalPages}
                        </span>
                        <div className="flex gap-2">
                            <Button
                                variant="secondary"
                                size="sm"
                                disabled={page === 0}
                                onClick={() => setPage(p => Math.max(0, p - 1))}
                                className="rounded-xl p-2"
                            >
                                <ChevronLeft size={16} />
                            </Button>
                            <Button
                                variant="secondary"
                                size="sm"
                                disabled={page >= totalPages - 1}
                                onClick={() => setPage(p => p + 1)}
                                className="rounded-xl p-2"
                            >
                                <ChevronRight size={16} />
                            </Button>
                        </div>
                    </div>
                )}
            </Card>

            {/* Drill-down Patient Financial Details Modal */}
            <Modal
                isOpen={isDetailModalOpen}
                onClose={handleCloseDetails}
                title={t('billing.summary.patient_details_title', 'Patient Financial File')}
                size="xl"
            >
                {detailLoading ? (
                    <div className="p-12 text-center text-slate-500 font-bold">{t('common.loading', 'Loading details...')}</div>
                ) : !detailData ? (
                    <div className="p-6 text-center text-red-500 font-bold">{t('common.error_loading_data', 'Error loading data.')}</div>
                ) : (
                    <div className="space-y-6">
                        {/* Patient Summary Header */}
                        <div className="bg-slate-50 dark:bg-slate-800/30 p-6 rounded-2xl border border-border grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="space-y-1">
                                <span className="text-xs font-bold uppercase tracking-widest text-text-secondary">{t('billing.summary.patient_name', 'Patient Name')}</span>
                                <h4 className="text-lg font-black text-slate-800 dark:text-white">{detailData.patient_name}</h4>
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
                                <span className="text-xs font-bold uppercase tracking-widest text-text-secondary">{t('billing.summary.outstanding_balance', 'Outstanding Balance')}</span>
                                <div className={`text-2xl font-black font-mono ${detailData.outstanding_balance > 0 ? 'text-amber-600 dark:text-amber-400 animate-pulse' : 'text-emerald-600 dark:text-emerald-400'}`}>
                                    {formatCurrency(detailData.outstanding_balance)}
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

                        {/* History Tabs / Lists */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Payment History */}
                            <div className="space-y-3">
                                <h5 className="font-bold text-base text-text-primary flex items-center gap-2 border-b border-border pb-2">
                                    <Landmark size={18} className="text-emerald-500" />
                                    {t('billing.summary.payment_history', 'Payment History')}
                                </h5>
                                <div className="max-h-[300px] overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                                    {detailData.payment_history.length === 0 ? (
                                        <p className="text-sm text-text-muted italic py-4 text-center">
                                            {t('billing.summary.no_payments', 'No payments recorded.')}
                                        </p>
                                    ) : (
                                        detailData.payment_history.map((p) => (
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
                                    {detailData.treatment_history.length === 0 ? (
                                        <p className="text-sm text-text-muted italic py-4 text-center">
                                            {t('billing.summary.no_treatments', 'No treatments recorded.')}
                                        </p>
                                    ) : (
                                        detailData.treatment_history.map((t_item) => (
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
        </div>
    );
};

export default SummaryTab;

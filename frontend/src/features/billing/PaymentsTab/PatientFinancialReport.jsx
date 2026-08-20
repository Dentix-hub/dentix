import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, Button, DateTimePicker, PatientSelect } from '@/shared/ui';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getPatientsReport, getPatients } from '@/api';
import PatientFinancialModal from './PatientFinancialModal';

export default function PatientFinancialReport() {
    const { t } = useTranslation();
    const today = new Date();
    const oneMonthAgo = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate()).toISOString().split('T')[0];
    const currentDay = today.toISOString().split('T')[0];

    const [startDate, setStartDate] = useState(oneMonthAgo);
    const [endDate, setEndDate] = useState(currentDay);
    const [selectedPatientId, setSelectedPatientId] = useState('');
    const [outstandingOnly, setOutstandingOnly] = useState(false);
    const [page, setPage] = useState(0);
    const limit = 10;

    const [detailPatientId, setDetailPatientId] = useState(null);
    const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

    const { data: patientsData } = useQuery({
        queryKey: ['patients_select_list'],
        queryFn: async () => {
            const res = await getPatients();
            return res.data || [];
        }
    });

    const { data: reportData, isLoading: reportLoading } = useQuery({
        queryKey: ['patients_report', startDate, endDate, selectedPatientId, outstandingOnly, page],
        queryFn: async () => {
            const res = await getPatientsReport({
                start_date: startDate,
                end_date: endDate,
                patient_id: selectedPatientId || undefined,
                outstanding_only: outstandingOnly,
                skip: page * limit,
                limit: limit
            });
            return res.data;
        }
    });

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-EG', { style: 'currency', currency: 'EGP', maximumFractionDigits: 0 }).format(amount || 0);
    };

    const reportPatients = reportData?.patients || [];
    const reportTotal = reportData?.total || 0;
    const totalPages = Math.ceil(reportTotal / limit) || 1;

    const handleViewDetails = (patientId) => {
        setDetailPatientId(patientId);
        setIsDetailModalOpen(true);
    };

    return (
        <div className="space-y-6">
            <Card className="overflow-hidden">
                <div className="p-6 border-b border-border space-y-4 bg-surface">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="flex items-center gap-4">
                            <div className="w-1.5 h-8 bg-primary rounded-full"></div>
                            <div>
                                <h3 className="font-bold text-xl text-text-primary">{t('billing.summary.patients_report_title', 'Patients Financial Report')}</h3>
                                <p className="text-sm text-text-secondary mt-0.5">{t('billing.summary.patient_report_scope', 'Only patients with financial activity in the selected period are shown.')}</p>
                            </div>
                        </div>
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

                    {/* Filter Panel: Dates & Patient Select */}
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-end pt-2">
                        <div className="lg:col-span-6 grid grid-cols-1 md:grid-cols-2 gap-3">
                            <DateTimePicker
                                label={t('billing.summary.from')}
                                mode="date"
                                value={startDate}
                                onChange={(e) => {
                                    setStartDate(e.target.value);
                                    setPage(0);
                                }}
                                compact
                            />
                            <DateTimePicker
                                label={t('billing.summary.to')}
                                mode="date"
                                value={endDate}
                                onChange={(e) => {
                                    setEndDate(e.target.value);
                                    setPage(0);
                                }}
                                compact
                            />
                        </div>
                        <div className="lg:col-span-6 flex items-center gap-3">
                            <div className="flex-1">
                                <PatientSelect
                                    patients={patientsData || []}
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
                                    className="text-red-500 hover:text-red-700 font-bold border border-red-200 shrink-0"
                                >
                                    <X size={16} className="me-1 inline" />
                                    {t('billing.summary.clear_filter', 'Clear')}
                                </Button>
                            )}
                        </div>
                    </div>
                </div>

                {/* Table */}
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
                                    <th className="p-4 text-end">{t('billing.summary.period_invoiced', 'Period Invoiced')}</th>
                                    <th className="p-4 text-end">{t('billing.summary.period_paid', 'Period Paid')}</th>
                                    <th className="p-4 text-end">{t('billing.summary.period_balance', 'Period Balance')}</th>
                                    <th className="p-4 text-center">{t('billing.summary.actions', 'Actions')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border text-sm font-medium text-text-primary">
                                {reportPatients.map((pat) => (
                                    <tr key={pat.patient_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                                        <td className="p-4">
                                            <div className="flex items-center gap-2.5">
                                                <span className="px-2 py-0.5 rounded-lg bg-primary/10 text-primary font-bold text-xs shrink-0">#{pat.file_number || pat.patient_id}</span>
                                                <div className="flex flex-col">
                                                    <span className="font-bold text-slate-800 dark:text-white">{pat.patient_name}</span>
                                                    <span className="text-xs text-text-secondary font-mono">{pat.patient_phone}</span>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="p-4 text-end font-bold font-mono">{formatCurrency(pat.total_invoiced)}</td>
                                        <td className="p-4 text-end font-bold font-mono text-emerald-600 dark:text-emerald-400">{formatCurrency(pat.total_paid)}</td>
                                        <td className={`p-4 text-end font-bold font-mono ${pat.outstanding_balance > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
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

            {/* Modal */}
            <PatientFinancialModal
                isOpen={isDetailModalOpen}
                onClose={() => {
                    setIsDetailModalOpen(false);
                    setDetailPatientId(null);
                }}
                patientId={detailPatientId}
                startDate={startDate}
                endDate={endDate}
                formatCurrency={formatCurrency}
            />
        </div>
    );
}

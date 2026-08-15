import { useState, useMemo } from 'react';
import { Banknote, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, EmptyState, Button, Input, DateTimePicker, TabGroup, SkeletonBox } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAllPayments } from '@/api';
import PatientFinancialReport from './PatientFinancialReport';

export default function PaymentsTab() {
    const { t } = useTranslation();
    const navigate = useNavigate();

    const [activeSubTab, setActiveSubTab] = useState('payments'); // 'payments' or 'reports'
    const [search, setSearch] = useState('');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [page, setPage] = useState(0);
    const limit = 10;

    const { data: payments = [], isLoading: loading } = useQuery({
        queryKey: ['payments_tab_list'],
        queryFn: async () => {
            const res = await getAllPayments();
            return res.data || [];
        }
    });

    const filteredPayments = useMemo(() => {
        return payments.filter(pay => {
            if (search) {
                const query = search.toLowerCase();
                const nameMatch = (pay.patient_name || '').toLowerCase().includes(query);
                const notesMatch = (pay.notes || '').toLowerCase().includes(query);
                const idMatch = String(pay.patient_id || '').includes(query);
                if (!nameMatch && !notesMatch && !idMatch) return false;
            }
            if (startDate && new Date(pay.date) < new Date(startDate)) {
                return false;
            }
            if (endDate && new Date(pay.date) > new Date(`${endDate}T23:59:59`)) {
                return false;
            }
            return true;
        });
    }, [payments, search, startDate, endDate]);

    const totalPages = Math.ceil(filteredPayments.length / limit) || 1;
    const paginatedPayments = useMemo(() => {
        const start = page * limit;
        return filteredPayments.slice(start, start + limit);
    }, [filteredPayments, page, limit]);

    const subTabs = useMemo(() => [
        { id: 'payments', label: t('billing.payments.title', 'Patient Payments') },
        { id: 'reports', label: t('billing.summary.patients_report_title', 'Patients Financial Report') }
    ], [t]);

    return (
        <div className="space-y-6">
            <TabGroup
                variant="underline"
                tabs={subTabs}
                activeTab={activeSubTab}
                onChange={setActiveSubTab}
            />

            {activeSubTab === 'payments' ? (
                <Card className="overflow-hidden">
                    {/* Header and Controls */}
                    <div className="p-6 border-b border-border space-y-4 bg-surface">
                        <div className="flex items-center gap-4">
                            <div className="w-1.5 h-8 bg-primary rounded-full"></div>
                            <div>
                                <h3 className="font-bold text-xl text-text-primary">{t('billing.payments.title')}</h3>
                                <p className="text-xs text-text-secondary">{filteredPayments.length} {t('common.records', 'records')}</p>
                            </div>
                        </div>

                        {/* Search & Date Filters */}
                        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
                            <div className="md:col-span-6 relative">
                                <Input
                                    placeholder={t('common.search_patient', 'Search by patient name or notes...')}
                                    value={search}
                                    onChange={(e) => {
                                        setSearch(e.target.value);
                                        setPage(0);
                                    }}
                                    className="ps-10"
                                />
                                <Search size={16} className="absolute start-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                            </div>
                            <div className="md:col-span-6 flex items-center gap-3">
                                <div className="flex-1">
                                    <DateTimePicker
                                        mode="date"
                                        value={startDate}
                                        onChange={(e) => {
                                            setStartDate(e.target.value);
                                            setPage(0);
                                        }}
                                        compact
                                    />
                                </div>
                                <span className="text-text-secondary">-</span>
                                <div className="flex-1">
                                    <DateTimePicker
                                        mode="date"
                                        value={endDate}
                                        onChange={(e) => {
                                            setEndDate(e.target.value);
                                            setPage(0);
                                        }}
                                        compact
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Table */}
                    <div className="overflow-x-auto">
                        {loading ? (
                            <div className="p-6 space-y-4">
                                {[1, 2, 3].map(i => <SkeletonBox key={i} className="h-12 w-full rounded-xl" />)}
                            </div>
                        ) : paginatedPayments.length > 0 ? (
                            <table className="w-full text-right align-middle text-sm">
                                <thead className="bg-surface-hover text-text-secondary font-bold text-xs uppercase tracking-widest border-b border-border">
                                    <tr>
                                        <th className="p-4">{t('billing.payments.patient')}</th>
                                        <th className="p-4">{t('billing.payments.date')}</th>
                                        <th className="p-4">{t('billing.payments.amount')}</th>
                                        <th className="p-4">{t('billing.payments.notes')}</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                    {paginatedPayments.map(pay => (
                                        <tr key={pay.id} className="hover:bg-surface-hover transition-all group">
                                            <td className="p-4">
                                                <button onClick={() => navigate(`/patients/${pay.patient_id}`)} className="flex items-center gap-2 hover:opacity-80 transition-opacity text-right">
                                                    <span className="px-2 py-0.5 rounded-lg bg-primary/10 text-primary font-bold text-xs">#{pay.patient_file_number || pay.patient_id}</span>
                                                    <span className="font-bold text-text-primary hover:underline">{pay.patient_name || '---'}</span>
                                                </button>
                                            </td>
                                            <td className="p-4 text-text-secondary font-bold" dir="ltr">
                                                {new Date(pay.date).toLocaleString('ar-EG', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                            </td>
                                            <td className="p-4">
                                                <span className="font-bold text-lg text-success">{pay.amount?.toLocaleString()}</span>
                                            </td>
                                            <td className="p-4 text-text-secondary font-medium">{pay.notes || '---'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <EmptyState
                                icon={Banknote}
                                title={t('billing.payments.no_data')}
                                description={t('billing.payments.no_data_desc')}
                            />
                        )}
                    </div>

                    {/* Pagination */}
                    {!loading && totalPages > 1 && (
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
            ) : (
                <PatientFinancialReport />
            )}
        </div>
    );
}

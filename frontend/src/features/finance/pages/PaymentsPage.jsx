import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
    Plus,
    CreditCard,
    Eye,
    Trash2,
    X,
} from 'lucide-react';
import { usePayments } from '../payments/hooks/usePayments';
import { useFinancePermissions } from '../useFinancePermissions';
import FilterBar from '../components/FilterBar';
import DataTable from '../components/DataTable';
import Money from '../components/Money';
import PaymentDetailDrawer from '../payments/components/PaymentDetailDrawer';
import RecordPaymentModal from '../payments/components/RecordPaymentModal';

/**
 * Payments V2 Page (§12 MASTER_SPEC).
 * URL-owned patient/file/receipt identifiers make Activity links, refresh, and
 * browser navigation reproduce the same server-filtered collection view.
 */
export default function PaymentsPage() {
    const { t, i18n } = useTranslation();
    const isArabic = i18n.language === 'ar';
    const { canWriteFinance } = useFinancePermissions();

    const {
        items,
        search,
        patientId,
        fileNumber,
        paymentId,
        doctorId,
        currentPage,
        pageSize,
        hasNextPage,
        hasIdentifierFilters,
        isLoading,
        isError,
        refetch,
        updateSearch,
        updateDateRange,
        setPage,
        setPaymentSelection,
        clearPaymentSelection,
        clearIdentifierFilters,
        createPayment,
        isCreating,
        deletePayment,
        isDeleting,
    } = usePayments(20);

    const [selectedPayment, setSelectedPayment] = useState(null);
    const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);

    useEffect(() => {
        if (!paymentId) return;
        const match = items.find((item) => Number(item.id) === Number(paymentId));
        if (match) setSelectedPayment(match);
    }, [items, paymentId]);

    const openPayment = (payment) => {
        setSelectedPayment(payment);
        setPaymentSelection(payment.id);
    };

    const closePayment = () => {
        setSelectedPayment(null);
        if (paymentId) clearPaymentSelection();
    };

    const columns = [
        {
            id: 'id',
            header: t('finance.payments.receipt_num', 'رقم السند'),
            sortable: false,
            width: '100px',
            cell: (row) => (
                <span className="font-mono font-bold text-text-primary">#{row.id}</span>
            ),
        },
        {
            id: 'patient',
            header: t('finance.payments.patient', 'المريض'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <button
                        type="button"
                        onClick={() => openPayment(row)}
                        className="block text-start font-bold text-text-primary transition-colors hover:text-primary"
                    >
                        {row.patient_name || row.patient?.name || `${t('patients.patient', 'مريض')} #${row.patient_id}`}
                    </button>
                    <span className="font-mono text-[11px] text-text-secondary">
                        {t('patients.file_number', 'الملف')}: {row.patient_file_number || row.patient_id}
                    </span>
                </div>
            ),
        },
        {
            id: 'amount',
            header: t('finance.payments.amount', 'المبلغ المحصل'),
            align: 'end',
            sortable: false,
            cell: (row) => <Money amount={row.amount} colored size="sm" />,
        },
        {
            id: 'date',
            header: t('finance.payments.date', 'تاريخ التحصيل'),
            sortable: false,
            cell: (row) => {
                if (!row.date) return '—';
                try {
                    const date = new Date(row.date);
                    return (
                        <span className="font-mono text-xs text-text-secondary">
                            {date.toLocaleDateString(isArabic ? 'ar-EG' : 'en-US', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                            })}
                        </span>
                    );
                } catch {
                    return <span className="font-mono text-xs text-text-secondary">{String(row.date).split('T')[0]}</span>;
                }
            },
        },
        {
            id: 'notes',
            header: t('finance.payments.notes', 'ملاحظات'),
            sortable: false,
            cell: (row) => (
                <span className="line-clamp-1 max-w-[200px] text-xs text-text-secondary" title={row.notes}>
                    {row.notes || '—'}
                </span>
            ),
        },
        {
            id: 'actions',
            header: t('common.actions', 'إجراءات'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <div className="flex items-center justify-end gap-1.5">
                    <button
                        type="button"
                        onClick={() => openPayment(row)}
                        className="rounded-lg p-1.5 text-text-secondary transition-colors hover:bg-primary/10 hover:text-primary"
                        title={t('common.view_details', 'عرض التفاصيل')}
                    >
                        <Eye className="h-4 w-4" />
                    </button>
                    {canWriteFinance && (
                        <button
                            type="button"
                            onClick={() => openPayment(row)}
                            className="rounded-lg p-1.5 text-text-secondary transition-colors hover:bg-rose-500/10 hover:text-rose-600"
                            title={t('common.delete', 'حذف')}
                        >
                            <Trash2 className="h-4 w-4" />
                        </button>
                    )}
                </div>
            ),
        },
    ];

    const renderMobileCard = (row) => (
        <div
            key={row.id}
            onClick={() => openPayment(row)}
            className="cursor-pointer space-y-3 rounded-xl border border-border bg-card p-4 shadow-xs transition-all hover:border-primary/30"
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-text-secondary">#{row.id}</span>
                    <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                        {t('finance.payments.detail_badge', 'تحصيل نقدي')}
                    </span>
                </div>
                <Money amount={row.amount} colored size="sm" />
            </div>

            <div className="space-y-1">
                <p className="text-sm font-bold text-text-primary">
                    {row.patient_name || row.patient?.name || `${t('patients.patient', 'مريض')} #${row.patient_id}`}
                </p>
                <div className="flex items-center gap-3 font-mono text-xs text-text-secondary">
                    <span>{t('patients.file_number', 'الملف')}: {row.patient_file_number || row.patient_id}</span>
                    <span>•</span>
                    <span>{row.date ? String(row.date).split('T')[0] : '—'}</span>
                </div>
                {row.notes && <p className="line-clamp-1 pt-1 text-xs text-text-secondary">{row.notes}</p>}
            </div>
        </div>
    );

    const totalVisibleAmount = items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
    const estimatedTotal = hasNextPage
        ? currentPage * pageSize + 1
        : (currentPage - 1) * pageSize + items.length;

    return (
        <div className="space-y-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div>
                    <h2 className="flex items-center gap-2 text-base font-bold text-text-primary sm:text-lg">
                        <CreditCard className="h-5 w-5 text-emerald-500" />
                        <span>{t('finance.payments.title', 'سجل التحصيلات النقدية')}</span>
                    </h2>
                    <p className="text-xs text-text-secondary">
                        {t('finance.payments.subtitle', 'كشف حركات القبض الصادرة من المرضى')}
                    </p>
                </div>

                {canWriteFinance && (
                    <button
                        type="button"
                        onClick={() => setIsRecordModalOpen(true)}
                        className="inline-flex self-start items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-white shadow-sm transition-all hover:bg-primary/90 sm:self-auto sm:text-sm"
                    >
                        <Plus className="h-4 w-4" />
                        <span>{t('finance.payments.record_btn', 'تسجيل دفعة جديدة')}</span>
                    </button>
                )}
            </div>

            <FilterBar
                searchValue={search}
                onSearchChange={updateSearch}
                searchPlaceholder={t('finance.payments.search_placeholder', 'البحث برقم السند أو الملف، اسم المريض، أو البيان...')}
                filters={[]}
                activeFilters={{}}
                onFilterChange={() => {}}
                onClearFilters={() => {
                    updateSearch('');
                    updateDateRange('', '');
                    clearIdentifierFilters();
                }}
            />

            {hasIdentifierFilters && (
                <div className="flex flex-wrap items-center gap-2 rounded-xl border border-primary/15 bg-primary/5 px-3 py-2 text-xs">
                    <span className="font-bold text-text-secondary">
                        {t('finance.payments.active_identifier_filters', 'فلاتر الرابط النشطة')}:
                    </span>
                    {patientId && <span className="rounded-lg bg-card px-2 py-1 font-mono">patient #{patientId}</span>}
                    {fileNumber && <span className="rounded-lg bg-card px-2 py-1 font-mono">file #{fileNumber}</span>}
                    {paymentId && <span className="rounded-lg bg-card px-2 py-1 font-mono">receipt #{paymentId}</span>}
                    {doctorId && <span className="rounded-lg bg-card px-2 py-1 font-mono">doctor #{doctorId}</span>}
                    <button
                        type="button"
                        onClick={clearIdentifierFilters}
                        className="ms-auto inline-flex items-center gap-1 rounded-lg px-2 py-1 font-bold text-primary hover:bg-primary/10"
                    >
                        <X className="h-3.5 w-3.5" />
                        {t('common.clear', 'مسح')}
                    </button>
                </div>
            )}

            <div className="flex items-center justify-between rounded-xl border border-border bg-card p-4 text-xs">
                <span className="text-text-secondary">
                    {t('finance.payments.visible_count', 'عدد السندات المعروضة')}: <strong className="font-mono text-text-primary">{items.length}</strong>
                </span>
                <div className="flex items-center gap-2">
                    <span className="text-text-secondary">{t('finance.payments.visible_total', 'إجمالي المعروض')}:</span>
                    <Money amount={totalVisibleAmount} size="sm" colored />
                </div>
            </div>

            <DataTable
                columns={columns}
                data={items}
                keyField="id"
                isLoading={isLoading}
                isError={isError}
                onRetry={refetch}
                renderMobileCard={renderMobileCard}
                emptyMessage={t('finance.payments.no_payments', 'لا توجد سندات تحصيل')}
                page={currentPage}
                pageSize={pageSize}
                totalItems={estimatedTotal}
                onPageChange={setPage}
            />

            <PaymentDetailDrawer
                payment={selectedPayment}
                isOpen={Boolean(selectedPayment)}
                onClose={closePayment}
                onDelete={deletePayment}
                isDeleting={isDeleting}
            />

            <RecordPaymentModal
                isOpen={isRecordModalOpen}
                initialPatientId={patientId || fileNumber || ''}
                onClose={() => setIsRecordModalOpen(false)}
                onSubmit={createPayment}
                isSubmitting={isCreating}
            />
        </div>
    );
}

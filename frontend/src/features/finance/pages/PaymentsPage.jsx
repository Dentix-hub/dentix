import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
    Plus,
    CreditCard,
    Eye,
    Trash2,
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
 * Displays paginated, searchable, date-filtered cash collections with detail drawer and recording modal.
 */
export default function PaymentsPage() {
    const { t, i18n } = useTranslation();
    const isArabic = i18n.language === 'ar';
    const { canWriteFinance } = useFinancePermissions();

    const {
        items,
        search,
        currentPage,
        pageSize,
        hasNextPage,
        isLoading,
        isError,
        refetch,
        updateSearch,
        updateDateRange,
        setPage,
        createPayment,
        isCreating,
        deletePayment,
        isDeleting,
    } = usePayments(20);

    const [selectedPayment, setSelectedPayment] = useState(null);
    const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);

    // Columns Definition for DataTable
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
                        onClick={() => setSelectedPayment(row)}
                        className="font-bold text-text-primary hover:text-primary transition-colors text-start block"
                    >
                        {row.patient_name || row.patient?.name || `مريض #${row.patient_id}`}
                    </button>
                    <span className="text-[11px] text-text-secondary font-mono">
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
            cell: (row) => (
                <Money
                    amount={row.amount}
                    colored
                    size="sm"
                />
            ),
        },
        {
            id: 'date',
            header: t('finance.payments.date', 'تاريخ التحصيل'),
            sortable: false,
            cell: (row) => {
                if (!row.date) return '—';
                try {
                    const d = new Date(row.date);
                    return (
                        <span className="font-mono text-xs text-text-secondary">
                            {d.toLocaleDateString(isArabic ? 'ar-EG' : 'en-US', {
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
                <span className="text-xs text-text-secondary line-clamp-1 max-w-[200px]" title={row.notes}>
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
                        onClick={() => setSelectedPayment(row)}
                        className="p-1.5 rounded-lg text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors"
                        title={t('common.view_details', 'عرض التفاصيل')}
                    >
                        <Eye className="w-4 h-4" />
                    </button>
                    {canWriteFinance && (
                        <button
                            type="button"
                            onClick={() => setSelectedPayment(row)}
                            className="p-1.5 rounded-lg text-text-secondary hover:text-rose-600 hover:bg-rose-500/10 transition-colors"
                            title={t('common.delete', 'حذف')}
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    )}
                </div>
            ),
        },
    ];

    // Mobile Card Render
    const renderMobileCard = (row) => (
        <div
            key={row.id}
            onClick={() => setSelectedPayment(row)}
            className="p-4 rounded-xl border border-border bg-card hover:border-primary/30 transition-all cursor-pointer space-y-3 shadow-xs"
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-text-secondary">#{row.id}</span>
                    <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                        {t('finance.payments.detail_badge', 'تحصيل نقدي')}
                    </span>
                </div>
                <Money amount={row.amount} colored size="sm" />
            </div>

            <div className="space-y-1">
                <p className="text-sm font-bold text-text-primary">
                    {row.patient_name || row.patient?.name || `مريض #${row.patient_id}`}
                </p>
                <div className="flex items-center gap-3 text-xs text-text-secondary font-mono">
                    <span>{t('patients.file_number', 'الملف')}: {row.patient_file_number || row.patient_id}</span>
                    <span>•</span>
                    <span>{row.date ? String(row.date).split('T')[0] : '—'}</span>
                </div>
                {row.notes && (
                    <p className="text-xs text-text-secondary line-clamp-1 pt-1">
                        {row.notes}
                    </p>
                )}
            </div>
        </div>
    );

    const totalVisibleAmount = items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
    const estimatedTotal = hasNextPage ? (currentPage * pageSize + 1) : (currentPage - 1) * pageSize + items.length;

    return (
        <div className="space-y-6">
            {/* Top Action Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h2 className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                        <CreditCard className="w-5 h-5 text-emerald-500" />
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
                        className="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-xl text-xs sm:text-sm font-bold transition-all shadow-sm self-start sm:self-auto"
                    >
                        <Plus className="w-4 h-4" />
                        <span>{t('finance.payments.record_btn', 'تسجيل دفعة جديدة')}</span>
                    </button>
                )}
            </div>

            {/* Filter Bar */}
            <FilterBar
                searchValue={search}
                onSearchChange={updateSearch}
                searchPlaceholder={t('finance.payments.search_placeholder', 'البحث برقم السند، اسم المريض، أو البيان...')}
                filters={[]}
                activeFilters={{}}
                onFilterChange={() => {}}
                onClearFilters={() => {
                    updateSearch('');
                    updateDateRange('', '');
                }}
            />

            {/* Total summary bar */}
            <div className="p-4 rounded-xl border border-border bg-card flex items-center justify-between text-xs">
                <span className="text-text-secondary">
                    {t('finance.payments.visible_count', 'عدد السندات المعروضة')}: <strong className="text-text-primary font-mono">{items.length}</strong>
                </span>
                <div className="flex items-center gap-2">
                    <span className="text-text-secondary">{t('finance.payments.visible_total', 'إجمالي المعروض')}:</span>
                    <Money amount={totalVisibleAmount} size="sm" colored />
                </div>
            </div>

            {/* Data Table */}
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

            {/* Detail Drawer */}
            <PaymentDetailDrawer
                payment={selectedPayment}
                isOpen={Boolean(selectedPayment)}
                onClose={() => setSelectedPayment(null)}
                onDelete={deletePayment}
                isDeleting={isDeleting}
            />

            {/* Record Payment Modal */}
            <RecordPaymentModal
                isOpen={isRecordModalOpen}
                onClose={() => setIsRecordModalOpen(false)}
                onSubmit={createPayment}
                isSubmitting={isCreating}
            />
        </div>
    );
}

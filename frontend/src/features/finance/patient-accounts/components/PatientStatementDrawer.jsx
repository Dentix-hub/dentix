import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
    Phone,
    FileSpreadsheet,
    CreditCard,
    Plus,
    ExternalLink,
    AlertTriangle,
    CalendarDays,
} from 'lucide-react';
import DentixDrawer from '@/shared/ui/DentixDrawer';
import Money from '../../components/Money';
import ScopeBadge from '../../components/ScopeBadge';
import { useFinancePermissions } from '../../useFinancePermissions';
import { usePatientStatement } from '../hooks/usePatientStatement';

/**
 * Patient Financial Statement Drawer.
 * The route patientId is authoritative; period activity and all-time debt come
 * from RECEIVABLE_READ server contracts rather than page-row calculations.
 */
export default function PatientStatementDrawer({
    patient,
    patientId,
    from,
    to,
    isOpen,
    onClose,
    onRecordPayment,
}) {
    const { t, i18n } = useTranslation();
    const { canWriteFinance } = useFinancePermissions();
    const isArabic = i18n.language === 'ar';
    const resolvedId = patientId || patient?.patient_id || patient?.id;
    const { data, isLoading, isError, refetch } = usePatientStatement(
        resolvedId,
        { from, to },
    );

    const resolvedPatient = data || patient;
    const allTimeDebt = Number(resolvedPatient?.all_time_outstanding ?? 0);
    const totalInvoiced = Number(resolvedPatient?.total_invoiced ?? 0);
    const totalPaid = Number(resolvedPatient?.total_paid ?? 0);
    const periodBalance = Number(
        resolvedPatient?.period_balance
        ?? resolvedPatient?.outstanding_balance
        ?? (totalInvoiced - totalPaid),
    );
    const paymentHistory = Array.isArray(resolvedPatient?.payment_history)
        ? resolvedPatient.payment_history
        : [];
    const treatmentHistory = Array.isArray(resolvedPatient?.treatment_history)
        ? resolvedPatient.treatment_history
        : [];

    const formatDate = (value) => {
        if (!value) return '—';
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return String(value).split('T')[0];
        return parsed.toLocaleDateString(isArabic ? 'ar-EG' : 'en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    const title = resolvedPatient?.patient_name
        || patient?.patient_name
        || t('finance.receivables.view_statement', 'عرض كشف الحساب');

    return (
        <DentixDrawer
            open={Boolean(isOpen)}
            onOpenChange={(open) => {
                if (!open) onClose?.();
            }}
            title={title}
            size="lg"
            closeLabel={t('common.close', 'إغلاق')}
        >
            <div data-testid="patient-statement-panel" className="space-y-6">
                <div className="space-y-2 border-b border-border pb-4">
                    <span className="block text-xs font-mono font-bold text-text-secondary">
                        #{resolvedPatient?.file_number || resolvedPatient?.patient_id || resolvedId || '—'}
                    </span>
                    {resolvedPatient?.patient_phone && (
                        <span className="flex items-center gap-1 text-xs font-mono text-text-secondary" dir="ltr">
                            <Phone className="h-3 w-3 text-primary" />
                            {resolvedPatient.patient_phone}
                        </span>
                    )}
                </div>

                {isLoading ? (
                    <div className="space-y-3" data-testid="patient-statement-loading">
                        <div className="h-24 animate-pulse rounded-2xl bg-muted" />
                        <div className="h-16 animate-pulse rounded-xl bg-muted" />
                        <div className="h-40 animate-pulse rounded-xl bg-muted" />
                    </div>
                ) : isError || !resolvedPatient ? (
                    <div className="space-y-3 rounded-xl border border-destructive/20 bg-destructive/5 p-5 text-center">
                        <p className="text-sm font-bold text-destructive">
                            {t('common.error_loading_data', 'تعذر تحميل بيانات كشف الحساب')}
                        </p>
                        <button
                            type="button"
                            onClick={refetch}
                            className="rounded-lg bg-primary px-3 py-2 text-xs font-bold text-white"
                        >
                            {t('common.retry', 'إعادة المحاولة')}
                        </button>
                    </div>
                ) : (
                    <>
                        <div className="space-y-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/50 dark:bg-amber-950/30">
                            <div className="flex items-center justify-between gap-3">
                                <span className="flex items-center gap-1.5 text-xs font-bold text-amber-700 dark:text-amber-400">
                                    <AlertTriangle className="h-4 w-4" />
                                    <span>{t('finance.receivables.total_debt', 'المديونية التراكمية (الذمة القائمة)')}</span>
                                </span>
                                <ScopeBadge scope="all_time" />
                            </div>
                            <Money amount={allTimeDebt} size="2xl" colored />
                            <p className="text-[11px] text-text-secondary">
                                {t('finance.receivables.debt_desc', 'إجمالي المبالغ غير المسددة عبر جميع الفترات العلاجية')}
                            </p>
                        </div>

                        <div className="space-y-3">
                            <div className="flex items-center justify-between gap-3">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                                    {t('finance.receivables.period_summary', 'ملخص الفترة المختارة')}
                                </h4>
                                {from && to && (
                                    <span className="flex items-center gap-1 text-[11px] font-mono text-text-secondary">
                                        <CalendarDays className="h-3.5 w-3.5" />
                                        {from} – {to}
                                    </span>
                                )}
                            </div>

                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                                <div className="rounded-xl border border-border bg-surface-subtle p-3">
                                    <div className="mb-1 flex items-center gap-1.5 text-[11px] text-text-secondary">
                                        <FileSpreadsheet className="h-3.5 w-3.5 text-primary" />
                                        {t('finance.metrics.invoiced', 'المحتسب')}
                                    </div>
                                    <Money amount={totalInvoiced} size="sm" />
                                </div>
                                <div className="rounded-xl border border-border bg-surface-subtle p-3">
                                    <div className="mb-1 flex items-center gap-1.5 text-[11px] text-text-secondary">
                                        <CreditCard className="h-3.5 w-3.5 text-emerald-500" />
                                        {t('finance.metrics.collected', 'المسدد')}
                                    </div>
                                    <Money amount={totalPaid} size="sm" colored />
                                </div>
                                <div className="rounded-xl border border-border bg-surface-subtle p-3">
                                    <div className="mb-1 text-[11px] text-text-secondary">
                                        {t('finance.receivables.period_balance', 'فارق الفترة')}
                                    </div>
                                    <Money amount={periodBalance} size="sm" colored />
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                            <section className="space-y-3" aria-labelledby="patient-statement-payments-heading">
                                <h4 id="patient-statement-payments-heading" className="flex items-center gap-2 border-b border-border pb-2 text-sm font-bold text-text-primary">
                                    <CreditCard className="h-4 w-4 text-emerald-500" />
                                    {t('finance.receivables.payment_history', 'حركات السداد')}
                                </h4>
                                <div className="max-h-72 space-y-2 overflow-y-auto">
                                    {paymentHistory.length === 0 ? (
                                        <p className="py-4 text-center text-xs text-text-secondary">
                                            {t('finance.receivables.no_payments_in_period', 'لا توجد دفعات في الفترة المختارة')}
                                        </p>
                                    ) : paymentHistory.map((entry) => (
                                        <div key={`payment-${entry.id}`} className="flex items-start justify-between gap-3 rounded-xl border border-border bg-surface-subtle p-3">
                                            <div className="space-y-0.5">
                                                <span className="block text-[11px] font-mono text-text-secondary">{formatDate(entry.date)}</span>
                                                {entry.notes && <p className="text-[11px] text-text-secondary">{entry.notes}</p>}
                                            </div>
                                            <Money amount={entry.amount} size="xs" colored />
                                        </div>
                                    ))}
                                </div>
                            </section>

                            <section className="space-y-3" aria-labelledby="patient-statement-treatments-heading">
                                <h4 id="patient-statement-treatments-heading" className="flex items-center gap-2 border-b border-border pb-2 text-sm font-bold text-text-primary">
                                    <FileSpreadsheet className="h-4 w-4 text-primary" />
                                    {t('finance.receivables.treatment_history', 'حركات العلاج والخصم')}
                                </h4>
                                <div className="max-h-72 space-y-2 overflow-y-auto">
                                    {treatmentHistory.length === 0 ? (
                                        <p className="py-4 text-center text-xs text-text-secondary">
                                            {t('finance.receivables.no_treatments_in_period', 'لا توجد خدمات علاجية في الفترة المختارة')}
                                        </p>
                                    ) : treatmentHistory.map((entry) => (
                                        <div key={`treatment-${entry.id}`} className="space-y-2 rounded-xl border border-border bg-surface-subtle p-3">
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="space-y-0.5">
                                                    <span className="block text-[11px] font-mono text-text-secondary">{formatDate(entry.date)}</span>
                                                    <p className="text-xs font-bold text-text-primary">{entry.procedure || '—'}</p>
                                                    {entry.diagnosis && <p className="text-[11px] text-text-secondary">{entry.diagnosis}</p>}
                                                </div>
                                                <Money amount={entry.net} size="xs" />
                                            </div>
                                            {Number(entry.discount || 0) > 0 && (
                                                <div className="border-t border-dashed border-border pt-1.5 text-[10px] text-text-secondary">
                                                    {t('finance.receivables.discount', 'خصم')}: <Money amount={entry.discount} size="xs" />
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </section>
                        </div>

                        <div className="flex items-center justify-between rounded-xl border border-border bg-surface-subtle p-4">
                            <div className="space-y-0.5">
                                <p className="text-xs font-bold text-text-primary">{t('patients.full_record', 'الملف الطبي والمالي الكامل')}</p>
                                <p className="text-[11px] text-text-secondary">{t('patients.view_timeline', 'عرض سجل المريض الكامل')}</p>
                            </div>
                            <Link
                                to={`/patients/${resolvedPatient.patient_id || resolvedId}`}
                                className="inline-flex items-center gap-1 rounded-lg bg-primary/10 px-3 py-1.5 text-xs font-bold text-primary transition-colors hover:bg-primary/20"
                            >
                                <span>{t('common.view', 'عرض')}</span>
                                <ExternalLink className="h-3.5 w-3.5" />
                            </Link>
                        </div>

                        {canWriteFinance && (
                            <div className="border-t border-border pt-4">
                                <button
                                    type="button"
                                    onClick={() => onRecordPayment?.(resolvedPatient)}
                                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white shadow-sm transition-all hover:bg-primary/90"
                                >
                                    <Plus className="h-4 w-4" />
                                    <span>{t('finance.payments.record_btn', 'تسجيل دفعة لهذا المريض')}</span>
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>
        </DentixDrawer>
    );
}

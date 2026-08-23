import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
    User,
    Calendar,
    FileText,
    Trash2,
    ExternalLink,
    AlertTriangle,
} from 'lucide-react';
import DentixDrawer from '@/shared/ui/DentixDrawer';
import Money from '../../components/Money';
import { useFinancePermissions } from '../../useFinancePermissions';

/**
 * Payment Detail Drawer / Slide-over sheet.
 * Displays comprehensive details for a specific payment and provides authorized actions.
 */
export default function PaymentDetailDrawer({
    payment,
    isOpen,
    onClose,
    onDelete,
    isDeleting = false,
}) {
    const { t, i18n } = useTranslation();
    const isArabic = i18n.language === 'ar';
    const { canWriteFinance } = useFinancePermissions();
    const [showConfirmDelete, setShowConfirmDelete] = useState(false);

    const formattedDate = payment?.date
        ? new Date(payment.date).toLocaleString(isArabic ? 'ar-EG' : 'en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
          })
        : '—';

    const handleDelete = async () => {
        if (onDelete && payment) {
            await onDelete(payment.id);
            setShowConfirmDelete(false);
            onClose();
        }
    };

    return (
        <DentixDrawer
            open={Boolean(isOpen && payment)}
            onOpenChange={(open) => {
                if (!open) {
                    setShowConfirmDelete(false);
                    onClose?.();
                }
            }}
            title={t('finance.payments.detail_title', 'تفاصيل سند التحصيل')}
            size="md"
            closeLabel={t('common.close', 'إغلاق')}
            closeOnOutside={!isDeleting}
        >
            {payment && (
                <div className="space-y-6">
                    <div className="space-y-3 border-b border-border pb-5">
                        <span className="block text-xs font-mono font-bold text-text-secondary" dir="ltr">
                            #{payment.id}
                        </span>
                        <span className="inline-block rounded-lg bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                            {t('finance.payments.detail_badge', 'دفعة مسددة')}
                        </span>
                        <Money amount={payment.amount} size="2xl" colored />
                    </div>

                    <section className="space-y-2" aria-labelledby={`payment-patient-${payment.id}`}>
                        <div id={`payment-patient-${payment.id}`} className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
                            <User className="w-4 h-4 text-primary" aria-hidden="true" />
                            <span>{t('finance.payments.patient', 'المريض')}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3 rounded-xl border border-border bg-muted/20 p-3.5">
                            <div className="min-w-0 space-y-0.5">
                                <p className="break-words text-sm font-bold text-text-primary" dir="auto">
                                    {payment.patient_name || payment.patient?.name || `مريض #${payment.patient_id}`}
                                </p>
                                <p className="text-xs font-mono text-text-secondary">
                                    {t('patients.file_number', 'رقم الملف')}: <bdi>{payment.patient_file_number || payment.patient_id}</bdi>
                                </p>
                            </div>
                            {payment.patient_id && (
                                <Link
                                    to={`/patients/${payment.patient_id}`}
                                    className="rounded-lg p-2 text-primary transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                                    aria-label={t('patients.view_profile', 'عرض ملف المريض')}
                                >
                                    <ExternalLink className="w-4 h-4" aria-hidden="true" />
                                </Link>
                            )}
                        </div>
                    </section>

                    <section className="space-y-2" aria-labelledby={`payment-date-${payment.id}`}>
                        <div id={`payment-date-${payment.id}`} className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
                            <Calendar className="w-4 h-4 text-primary" aria-hidden="true" />
                            <span>{t('finance.payments.date_time', 'تاريخ ووقت التحصيل')}</span>
                        </div>
                        <div className="rounded-xl border border-border bg-muted/20 p-3 text-xs font-mono text-text-primary" dir="auto">
                            {formattedDate}
                        </div>
                    </section>

                    {payment.doctor_name && (
                        <section className="space-y-2" aria-labelledby={`payment-doctor-${payment.id}`}>
                            <div id={`payment-doctor-${payment.id}`} className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
                                <User className="w-4 h-4 text-primary" aria-hidden="true" />
                                <span>{t('finance.payments.doctor', 'الطبيب المعالج')}</span>
                            </div>
                            <div className="rounded-xl border border-border bg-muted/20 p-3 text-xs font-bold text-text-primary" dir="auto">
                                د. {payment.doctor_name}
                            </div>
                        </section>
                    )}

                    <section className="space-y-2" aria-labelledby={`payment-notes-${payment.id}`}>
                        <div id={`payment-notes-${payment.id}`} className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
                            <FileText className="w-4 h-4 text-primary" aria-hidden="true" />
                            <span>{t('finance.payments.notes', 'ملاحظات وسند التحصيل')}</span>
                        </div>
                        <div className="min-h-[60px] whitespace-pre-wrap rounded-xl border border-border bg-muted/20 p-3 text-xs text-text-primary" dir="auto">
                            {payment.notes || t('finance.payments.no_notes', 'لا توجد ملاحظات إضافية')}
                        </div>
                    </section>

                    {canWriteFinance && (
                        <div className="border-t border-border pt-4">
                            {showConfirmDelete ? (
                                <div className="space-y-3 rounded-xl border border-rose-200 bg-rose-50 p-4 dark:border-rose-900/50 dark:bg-rose-950/20" role="alert">
                                    <div className="flex items-center gap-2 text-xs font-bold text-rose-600 dark:text-rose-400">
                                        <AlertTriangle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                                        <span>{t('finance.payments.confirm_delete_title', 'تأكيد حذف سند التحصيل؟')}</span>
                                    </div>
                                    <p className="text-[11px] text-text-secondary">
                                        {t('finance.payments.confirm_delete_desc', 'سيتم إرجاع المبلغ لذمة المريض التراكمية فوراً.')}
                                    </p>
                                    <div className="flex items-center gap-2 pt-1">
                                        <button
                                            type="button"
                                            onClick={handleDelete}
                                            disabled={isDeleting}
                                            className="flex-1 rounded-lg bg-rose-600 px-3 py-2 text-xs font-bold text-white transition-colors hover:bg-rose-700 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600"
                                        >
                                            {isDeleting ? t('common.deleting', 'جاري الحذف...') : t('common.delete', 'حذف')}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setShowConfirmDelete(false)}
                                            disabled={isDeleting}
                                            className="rounded-lg bg-muted px-3 py-2 text-xs font-bold text-text-primary transition-colors hover:bg-muted/80 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                                        >
                                            {t('common.cancel', 'إلغاء')}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmDelete(true)}
                                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-rose-500/10 px-4 py-2.5 text-xs font-bold text-rose-600 transition-colors hover:bg-rose-500/20 dark:text-rose-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600"
                                >
                                    <Trash2 className="w-4 h-4" aria-hidden="true" />
                                    <span>{t('finance.payments.delete_payment', 'حذف سند التحصيل')}</span>
                                </button>
                            )}
                        </div>
                    )}
                </div>
            )}
        </DentixDrawer>
    );
}

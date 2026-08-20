import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
    X,
    User,
    Calendar,
    FileText,
    Trash2,
    ExternalLink,
    AlertTriangle,
} from 'lucide-react';
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

    if (!isOpen || !payment) return null;

    const formattedDate = payment.date
        ? new Date(payment.date).toLocaleString(isArabic ? 'ar-EG' : 'en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
          })
        : '—';

    const handleDelete = async () => {
        if (onDelete) {
            await onDelete(payment.id);
            setShowConfirmDelete(false);
            onClose();
        }
    };

    return (
        <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity duration-300"
                onClick={onClose}
                aria-hidden="true"
            />

            <div className="fixed inset-y-0 end-0 max-w-full flex pl-10 rtl:pl-0 rtl:pr-10">
                <div className="w-screen max-w-md bg-card border-s border-border shadow-2xl flex flex-col justify-between overflow-y-auto">
                    {/* Header */}
                    <div className="p-6 border-b border-border space-y-3">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-mono font-bold text-text-secondary">
                                #{payment.id}
                            </span>
                            <button
                                type="button"
                                onClick={onClose}
                                className="p-2 rounded-xl text-text-secondary hover:text-text-primary hover:bg-muted/60 transition-colors"
                                aria-label={t('common.close', 'إغلاق')}
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-1">
                            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg inline-block">
                                {t('finance.payments.detail_badge', 'دفعة مسددة')}
                            </span>
                            <div className="pt-2">
                                <Money
                                    amount={payment.amount}
                                    size="2xl"
                                    colored
                                />
                            </div>
                        </div>
                    </div>

                    {/* Details Body */}
                    <div className="p-6 space-y-6 flex-1">
                        {/* Patient info */}
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-text-secondary flex items-center gap-1.5">
                                <User className="w-4 h-4 text-primary" />
                                <span>{t('finance.payments.patient', 'المريض')}</span>
                            </label>
                            <div className="p-3.5 rounded-xl border border-border bg-muted/20 flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <p className="text-sm font-bold text-text-primary">
                                        {payment.patient_name || payment.patient?.name || `مريض #${payment.patient_id}`}
                                    </p>
                                    <p className="text-xs text-text-secondary font-mono">
                                        {t('patients.file_number', 'رقم الملف')}: {payment.patient_file_number || payment.patient_id}
                                    </p>
                                </div>
                                {payment.patient_id && (
                                    <Link
                                        to={`/patients/${payment.patient_id}`}
                                        className="p-2 text-primary hover:bg-primary/10 rounded-lg transition-colors"
                                        title={t('patients.view_profile', 'عرض ملف المريض')}
                                    >
                                        <ExternalLink className="w-4 h-4" />
                                    </Link>
                                )}
                            </div>
                        </div>

                        {/* Date and Time */}
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-text-secondary flex items-center gap-1.5">
                                <Calendar className="w-4 h-4 text-primary" />
                                <span>{t('finance.payments.date_time', 'تاريخ ووقت التحصيل')}</span>
                            </label>
                            <div className="p-3 rounded-xl border border-border bg-muted/20 text-xs font-mono text-text-primary">
                                {formattedDate}
                            </div>
                        </div>

                        {/* Doctor info if available */}
                        {payment.doctor_name && (
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-text-secondary flex items-center gap-1.5">
                                    <User className="w-4 h-4 text-primary" />
                                    <span>{t('finance.payments.doctor', 'الطبيب المعالج')}</span>
                                </label>
                                <div className="p-3 rounded-xl border border-border bg-muted/20 text-xs font-bold text-text-primary">
                                    د. {payment.doctor_name}
                                </div>
                            </div>
                        )}

                        {/* Notes */}
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-text-secondary flex items-center gap-1.5">
                                <FileText className="w-4 h-4 text-primary" />
                                <span>{t('finance.payments.notes', 'ملاحظات وسند التحصيل')}</span>
                            </label>
                            <div className="p-3 rounded-xl border border-border bg-muted/20 text-xs text-text-primary min-h-[60px] whitespace-pre-wrap">
                                {payment.notes || t('finance.payments.no_notes', 'لا توجد ملاحظات إضافية')}
                            </div>
                        </div>
                    </div>

                    {/* Footer Actions */}
                    <div className="p-6 border-t border-border bg-muted/10 space-y-3">
                        {canWriteFinance && (
                            <>
                                {showConfirmDelete ? (
                                    <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/20 space-y-3">
                                        <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 text-xs font-bold">
                                            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
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
                                                className="flex-1 py-2 px-3 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                                            >
                                                {isDeleting ? t('common.deleting', 'جاري الحذف...') : t('common.delete', 'حذف')}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setShowConfirmDelete(false)}
                                                className="py-2 px-3 bg-muted hover:bg-muted/80 text-text-primary rounded-lg text-xs font-bold transition-colors"
                                            >
                                                {t('common.cancel', 'إلغاء')}
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <button
                                        type="button"
                                        onClick={() => setShowConfirmDelete(true)}
                                        className="w-full flex items-center justify-center gap-2 py-2.5 px-4 text-xs font-bold text-rose-600 dark:text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 rounded-xl transition-colors"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                        <span>{t('finance.payments.delete_payment', 'حذف سند التحصيل')}</span>
                                    </button>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Loader2 } from 'lucide-react';
import Money from '../../components/Money';
import useModalFocusManagement from '../../hooks/useModalFocusManagement';

/**
 * Explicit confirmation modal for deleting an expense record.
 * Explains specific financial impact and verifies record identity (§35 MASTER_SPEC).
 */
export default function DeleteExpenseModal({
    expense,
    isOpen,
    onClose,
    onConfirm,
    isDeleting = false,
}) {
    const { t } = useTranslation();
    const titleId = useId();
    const descriptionId = useId();
    const dialogRef = useModalFocusManagement(Boolean(isOpen && expense), onClose);

    if (!isOpen || !expense) return null;

    return (
        <div
            className="fixed inset-0 z-50 overflow-y-auto"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
        >
            <div
                className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity duration-300"
                onClick={onClose}
                aria-hidden="true"
            />

            <div className="flex min-h-full items-center justify-center p-4">
                <div
                    ref={dialogRef}
                    tabIndex={-1}
                    className="relative w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl overflow-hidden space-y-4 p-6 outline-none"
                >
                    <div className="flex items-center gap-3">
                        <div className="p-3 rounded-xl bg-destructive/10 text-destructive">
                            <AlertTriangle className="w-6 h-6" aria-hidden="true" />
                        </div>
                        <div>
                            <h3 id={titleId} className="text-base font-bold text-text-primary">
                                {t('finance.expenses.delete_title', 'تأكيد حذف المصروف')}
                            </h3>
                            <p id={descriptionId} className="text-xs text-text-secondary">
                                {t('finance.expenses.delete_sub', 'إلغاء قيد المصروف من السجلات المالية')}
                            </p>
                        </div>
                    </div>

                    <div className="p-4 rounded-xl border border-destructive/20 bg-destructive/5 space-y-2.5 text-xs">
                        <div className="flex items-center justify-between gap-3">
                            <span className="font-bold text-text-primary" dir="auto">{expense.item_name}</span>
                            <Money amount={expense.cost} size="sm" colored />
                        </div>
                        {expense.category && (
                            <div className="text-[11px] text-text-secondary">
                                <span>{t('finance.expenses.category', 'التصنيف')}: </span>
                                <span className="font-semibold text-text-primary" dir="auto">{expense.category}</span>
                            </div>
                        )}
                        <p className="text-[11px] text-text-secondary pt-1 border-t border-destructive/10">
                            {t(
                                'finance.expenses.delete_impact_warning',
                                'سيؤدي حذف هذا المصروف إلى خفض إجمالي المصروفات التشغيلية المسجلة وتعديل صافي الأرباح التشغيلية للفترة.'
                            )}
                        </p>
                    </div>

                    <div className="flex items-center justify-end gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-xs font-bold text-text-secondary hover:text-text-primary bg-card border border-border rounded-xl hover:bg-muted/60 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        >
                            {t('common.cancel', 'إلغاء')}
                        </button>
                        <button
                            type="button"
                            onClick={() => onConfirm(expense.id)}
                            disabled={isDeleting}
                            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-destructive hover:bg-destructive/90 disabled:opacity-50 rounded-xl transition-all shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive focus-visible:ring-offset-2"
                        >
                            {isDeleting ? (
                                <>
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                                    <span>{t('common.deleting', 'جاري الحذف...')}</span>
                                </>
                            ) : (
                                <span>{t('finance.expenses.confirm_delete_btn', 'حذف المصروف نهائياً')}</span>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

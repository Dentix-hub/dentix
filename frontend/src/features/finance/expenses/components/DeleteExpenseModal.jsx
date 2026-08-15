import { useTranslation } from 'react-i18next';
import { AlertTriangle, Loader2 } from 'lucide-react';
import Money from '../../components/Money';

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

    if (!isOpen || !expense) return null;

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity duration-300"
                onClick={onClose}
                aria-hidden="true"
            />

            <div className="flex min-h-full items-center justify-center p-4">
                <div className="relative w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl overflow-hidden space-y-4 p-6">
                    {/* Header */}
                    <div className="flex items-center gap-3">
                        <div className="p-3 rounded-xl bg-destructive/10 text-destructive">
                            <AlertTriangle className="w-6 h-6" />
                        </div>
                        <div>
                            <h3 className="text-base font-bold text-text-primary">
                                {t('finance.expenses.delete_title', 'تأكيد حذف المصروف')}
                            </h3>
                            <p className="text-xs text-text-secondary">
                                {t('finance.expenses.delete_sub', 'إلغاء قيد المصروف من السجلات المالية')}
                            </p>
                        </div>
                    </div>

                    {/* Expense Identity & Financial Impact Warning */}
                    <div className="p-4 rounded-xl border border-destructive/20 bg-destructive/5 space-y-2.5 text-xs">
                        <div className="flex items-center justify-between">
                            <span className="font-bold text-text-primary">{expense.item_name}</span>
                            <Money amount={expense.cost} size="sm" colored />
                        </div>
                        {expense.category && (
                            <div className="text-[11px] text-text-secondary">
                                <span>{t('finance.expenses.category', 'التصنيف')}: </span>
                                <span className="font-semibold text-text-primary">{expense.category}</span>
                            </div>
                        )}
                        <p className="text-[11px] text-text-secondary pt-1 border-t border-destructive/10">
                            {t(
                                'finance.expenses.delete_impact_warning',
                                'سيؤدي حذف هذا المصروف إلى خفض إجمالي المصروفات التشغيلية المسجلة وتعديل صافي الأرباح التشغيلية للفترة.'
                            )}
                        </p>
                    </div>

                    {/* Footer Actions */}
                    <div className="flex items-center justify-end gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-xs font-bold text-text-secondary hover:text-text-primary bg-card border border-border rounded-xl hover:bg-muted/60 transition-colors"
                        >
                            {t('common.cancel', 'إلغاء')}
                        </button>
                        <button
                            type="button"
                            onClick={() => onConfirm(expense.id)}
                            disabled={isDeleting}
                            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-destructive hover:bg-destructive/90 disabled:opacity-50 rounded-xl transition-all shadow-sm"
                        >
                            {isDeleting ? (
                                <>
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
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

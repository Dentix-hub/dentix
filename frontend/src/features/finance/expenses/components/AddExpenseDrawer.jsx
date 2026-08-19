import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
    X,
    Plus,
    Receipt,
    Calendar,
    Tag,
    FileText,
    DollarSign,
    Loader2,
} from 'lucide-react';
import { useFinancePermissions } from '../../useFinancePermissions';

const EXPENSE_CATEGORIES = [
    { value: 'Supplies', label: 'مستلزمات طبية وعيادة (Supplies)' },
    { value: 'Utilities', label: 'فواتير وخدمات (Utilities)' },
    { value: 'Rent', label: 'إيجار المقر (Rent)' },
    { value: 'Maintenance', label: 'صيانة دورية وأجهزة (Maintenance)' },
    { value: 'Laboratory', label: 'معامل وتركيبات خارجية (Laboratory)' },
    { value: 'Salaries', label: 'أجور ورواتب إضافية (Salaries)' },
    { value: 'Other', label: 'مصاريف عامة أخرى (Other)' },
];

/**
 * Slide-over drawer for adding manual clinic expenses.
 */
export default function AddExpenseDrawer({
    isOpen,
    onClose,
    onSubmit,
    isSubmitting = false,
}) {
    const { t } = useTranslation();
    const { canWriteFinance } = useFinancePermissions();

    const [itemName, setItemName] = useState('');
    const [cost, setCost] = useState('');
    const [category, setCategory] = useState('Supplies');
    const [date, setDate] = useState(() => new Date().toISOString().split('T')[0]);
    const [notes, setNotes] = useState('');
    const [formError, setFormError] = useState('');

    if (!isOpen) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setFormError('');

        if (!itemName.trim()) {
            setFormError(t('finance.expenses.item_name_required', 'يرجى إدخال اسم أو بيان المصروف'));
            return;
        }

        const numCost = parseFloat(cost);
        if (isNaN(numCost) || numCost <= 0) {
            setFormError(t('finance.expenses.cost_invalid', 'يرجى إدخال قيمة صحيحة للمصروف أكبر من صفر'));
            return;
        }

        try {
            await onSubmit({
                item_name: itemName.trim(),
                cost: numCost,
                category,
                date,
                notes: notes.trim() || undefined,
            });

            // Reset and close
            setItemName('');
            setCost('');
            setCategory('Supplies');
            setDate(new Date().toISOString().split('T')[0]);
            setNotes('');
            onClose();
        } catch (err) {
            setFormError(err.response?.data?.detail || err.message || t('common.error_occurred', 'حدث خطأ أثناء الحفظ'));
        }
    };

    return (
        <div className="fixed inset-0 z-drawer overflow-hidden" role="dialog" aria-modal="true">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-backdrop backdrop-blur-xs transition-opacity duration-300"
                onClick={onClose}
                aria-hidden="true"
            />

            <div className="fixed inset-y-0 end-0 flex max-w-full pl-10 rtl:pl-0 rtl:pr-10">
                <div className="flex w-screen max-w-md flex-col justify-between overflow-y-auto border-s border-border bg-surface-elevated text-text-primary shadow-high">
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-border p-6">
                        <div className="flex items-center gap-3">
                            <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
                                <Receipt className="h-5 w-5" />
                            </div>
                            <div>
                                <h3 className="text-base font-bold text-text-primary">
                                    {t('finance.expenses.add_drawer_title', 'تسجيل مصروف جديد')}
                                </h3>
                                <p className="text-xs text-text-secondary">
                                    {t('finance.expenses.add_drawer_sub', 'إضافة حركة مصروفات تشغيلية للعيادة')}
                                </p>
                            </div>
                        </div>
                        <button
                            type="button"
                            onClick={onClose}
                            className="rounded-xl p-2 text-text-secondary transition-colors hover:bg-surface-subtle hover:text-text-primary"
                            aria-label={t('common.close', 'إغلاق')}
                        >
                            <X className="h-5 w-5" />
                        </button>
                    </div>

                    {/* Form Body */}
                    <form id="add-expense-form" onSubmit={handleSubmit} className="flex-1 space-y-4 p-6">
                        {formError && (
                            <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-xs font-semibold text-red-600 dark:text-red-400">
                                {formError}
                            </div>
                        )}

                        {/* Item Name */}
                        <div className="space-y-1.5">
                            <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <Receipt className="h-3.5 w-3.5 text-primary" />
                                <span>{t('finance.expenses.item_name', 'بيان المصروف')} *</span>
                            </label>
                            <input
                                type="text"
                                required
                                value={itemName}
                                onChange={(e) => setItemName(e.target.value)}
                                placeholder={t('finance.expenses.item_placeholder', 'مثال: شراء مواد تخدير، صيانة كرسي...')}
                                className="w-full rounded-xl border border-border bg-input px-3 py-2 text-xs text-text-primary transition-all placeholder:text-text-secondary/60 focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                        </div>

                        {/* Cost / Amount */}
                        <div className="space-y-1.5">
                            <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <DollarSign className="h-3.5 w-3.5 text-primary" />
                                <span>{t('finance.expenses.cost', 'المبلغ (جنيه)')} *</span>
                            </label>
                            <input
                                type="number"
                                required
                                min="0.01"
                                step="0.01"
                                value={cost}
                                onChange={(e) => setCost(e.target.value)}
                                placeholder="0.00"
                                className="w-full rounded-xl border border-border bg-input px-3 py-2 font-mono text-xs text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                        </div>

                        {/* Category */}
                        <div className="space-y-1.5">
                            <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <Tag className="h-3.5 w-3.5 text-primary" />
                                <span>{t('finance.expenses.category', 'التصنيف')} *</span>
                            </label>
                            <select
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                                className="w-full rounded-xl border border-border bg-input px-3 py-2 text-xs text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            >
                                {EXPENSE_CATEGORIES.map((cat) => (
                                    <option key={cat.value} value={cat.value}>
                                        {cat.label}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Date */}
                        <div className="space-y-1.5">
                            <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <Calendar className="h-3.5 w-3.5 text-primary" />
                                <span>{t('finance.expenses.date', 'التاريخ')} *</span>
                            </label>
                            <input
                                type="date"
                                required
                                value={date}
                                onChange={(e) => setDate(e.target.value)}
                                className="w-full rounded-xl border border-border bg-input px-3 py-2 font-mono text-xs text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                        </div>

                        {/* Notes */}
                        <div className="space-y-1.5">
                            <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <FileText className="h-3.5 w-3.5 text-primary" />
                                <span>{t('finance.expenses.notes', 'ملاحظات إضافية')}</span>
                            </label>
                            <textarea
                                rows={3}
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                placeholder={t('finance.expenses.notes_placeholder', 'أي تفاصيل عن المورد أو الفاتورة...')}
                                className="w-full rounded-xl border border-border bg-input px-3 py-2 text-xs text-text-primary transition-all placeholder:text-text-secondary/60 focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                        </div>
                    </form>

                    {/* Footer Actions */}
                    <div className="flex items-center gap-3 border-t border-border bg-surface-subtle p-6">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 rounded-xl border border-border bg-surface-elevated px-4 py-2.5 text-xs font-bold text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary"
                        >
                            {t('common.cancel', 'إلغاء')}
                        </button>
                        {canWriteFinance && (
                            <button
                                type="submit"
                                form="add-expense-form"
                                disabled={isSubmitting}
                                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white shadow-low transition-all hover:bg-primary/90 disabled:opacity-50"
                            >
                                {isSubmitting ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        <span>{t('common.saving', 'جاري الحفظ...')}</span>
                                    </>
                                ) : (
                                    <>
                                        <Plus className="h-4 w-4" />
                                        <span>{t('finance.expenses.save_btn', 'حفظ المصروف')}</span>
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
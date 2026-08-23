import { useId, useState } from 'react';
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
import useModalFocusManagement from '../../hooks/useModalFocusManagement';

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
    const titleId = useId();
    const descriptionId = useId();
    const itemNameId = useId();
    const costId = useId();
    const categoryId = useId();
    const dateId = useId();
    const notesId = useId();
    const dialogRef = useModalFocusManagement(isOpen, onClose);

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
        if (Number.isNaN(numCost) || numCost <= 0) {
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
        <div
            className="fixed inset-0 z-50 overflow-hidden"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
        >
            <div
                className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity duration-300"
                onClick={onClose}
                aria-hidden="true"
            />

            <div className="fixed inset-y-0 end-0 flex max-w-full pl-10 rtl:pl-0 rtl:pr-10">
                <div
                    ref={dialogRef}
                    tabIndex={-1}
                    className="flex w-screen max-w-md flex-col justify-between overflow-y-auto border-s border-border bg-surface-elevated text-text-primary shadow-high outline-none"
                >
                    <div className="flex items-center justify-between border-b border-border p-6">
                        <div className="flex items-center gap-3">
                            <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
                                <Receipt className="h-5 w-5" aria-hidden="true" />
                            </div>
                            <div>
                                <h3 id={titleId} className="text-base font-bold text-text-primary">
                                    {t('finance.expenses.add_drawer_title', 'تسجيل مصروف جديد')}
                                </h3>
                                <p id={descriptionId} className="text-xs text-text-secondary">
                                    {t('finance.expenses.add_drawer_sub', 'إضافة حركة مصروفات تشغيلية للعيادة')}
                                </p>
                            </div>
                        </div>
                        <button
                            type="button"
                            onClick={onClose}
                            className="rounded-xl p-2 text-text-secondary transition-colors hover:bg-surface-subtle hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                            aria-label={t('common.close', 'إغلاق')}
                        >
                            <X className="h-5 w-5" aria-hidden="true" />
                        </button>
                    </div>

                    <form id="add-expense-form" onSubmit={handleSubmit} className="flex-1 space-y-4 p-6">
                        {formError && (
                            <div
                                className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-xs font-semibold text-red-600 dark:text-red-400"
                                role="alert"
                            >
                                {formError}
                            </div>
                        )}

                        <div className="space-y-1.5">
                            <label htmlFor={itemNameId} className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <Receipt className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                                <span>{t('finance.expenses.item_name', 'بيان المصروف')} *</span>
                            </label>
                            <input
                                id={itemNameId}
                                type="text"
                                required
                                value={itemName}
                                onChange={(e) => setItemName(e.target.value)}
                                placeholder={t('finance.expenses.item_placeholder', 'مثال: شراء مواد تخدير، صيانة كرسي...')}
                                className="w-full rounded-xl border border-border bg-input px-3 py-2 text-xs text-text-primary transition-all placeholder:text-text-secondary/60 focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label htmlFor={costId} className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <DollarSign className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                                <span>{t('finance.expenses.cost', 'المبلغ (جنيه)')} *</span>
                            </label>
                            <input
                                id={costId}
                                type="number"
                                required
                                min="0.01"
                                step="0.01"
                                inputMode="decimal"
                                dir="ltr"
                                value={cost}
                                onChange={(e) => setCost(e.target.value)}
                                placeholder="0.00"
                                className="w-full rounded-xl border border-border bg-input px-3 py-2 font-mono text-xs text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label htmlFor={categoryId} className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <Tag className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                                <span>{t('finance.expenses.category', 'التصنيف')} *</span>
                            </label>
                            <select
                                id={categoryId}
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

                        <div className="space-y-1.5">
                            <label htmlFor={dateId} className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <Calendar className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                                <span>{t('finance.expenses.date', 'التاريخ')} *</span>
                            </label>
                            <input
                                id={dateId}
                                type="date"
                                required
                                dir="ltr"
                                value={date}
                                onChange={(e) => setDate(e.target.value)}
                                className="w-full rounded-xl border border-border bg-input px-3 py-2 font-mono text-xs text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label htmlFor={notesId} className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <FileText className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                                <span>{t('finance.expenses.notes', 'ملاحظات إضافية')}</span>
                            </label>
                            <textarea
                                id={notesId}
                                rows={3}
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                placeholder={t('finance.expenses.notes_placeholder', 'أي تفاصيل عن المورد أو الفاتورة...')}
                                className="w-full rounded-xl border border-border bg-input px-3 py-2 text-xs text-text-primary transition-all placeholder:text-text-secondary/60 focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                        </div>
                    </form>

                    <div className="flex items-center gap-3 border-t border-border bg-surface-subtle p-6">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 rounded-xl border border-border bg-surface-elevated px-4 py-2.5 text-xs font-bold text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        >
                            {t('common.cancel', 'إلغاء')}
                        </button>
                        {canWriteFinance && (
                            <button
                                type="submit"
                                form="add-expense-form"
                                disabled={isSubmitting}
                                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white shadow-low transition-all hover:bg-primary/90 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                            >
                                {isSubmitting ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                                        <span>{t('common.saving', 'جاري الحفظ...')}</span>
                                    </>
                                ) : (
                                    <>
                                        <Plus className="h-4 w-4" aria-hidden="true" />
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

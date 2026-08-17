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
                    <div className="p-6 border-b border-border flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
                                <Receipt className="w-5 h-5" />
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
                            className="p-2 rounded-xl text-text-secondary hover:text-text-primary hover:bg-muted/60 transition-colors"
                            aria-label={t('common.close', 'إغلاق')}
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Form Body */}
                    <form id="add-expense-form" onSubmit={handleSubmit} className="p-6 space-y-4 flex-1">
                        {formError && (
                            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs font-semibold">
                                {formError}
                            </div>
                        )}

                        {/* Item Name */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <Receipt className="w-3.5 h-3.5 text-primary" />
                                <span>{t('finance.expenses.item_name', 'بيان المصروف')} *</span>
                            </label>
                            <input
                                type="text"
                                required
                                value={itemName}
                                onChange={(e) => setItemName(e.target.value)}
                                placeholder={t('finance.expenses.item_placeholder', 'مثال: شراء مواد تخدير، صيانة كرسي...')}
                                className="w-full px-3 py-2 text-xs sm:text-sm bg-background border border-border rounded-xl text-text-primary placeholder:text-text-secondary/60 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                        </div>

                        {/* Cost / Amount */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <DollarSign className="w-3.5 h-3.5 text-primary" />
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
                                className="w-full px-3 py-2 text-xs sm:text-sm bg-background border border-border rounded-xl text-text-primary font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                        </div>

                        {/* Category */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <Tag className="w-3.5 h-3.5 text-primary" />
                                <span>{t('finance.expenses.category', 'التصنيف')} *</span>
                            </label>
                            <select
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                                className="w-full px-3 py-2 text-xs sm:text-sm bg-background border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
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
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <Calendar className="w-3.5 h-3.5 text-primary" />
                                <span>{t('finance.expenses.date', 'التاريخ')} *</span>
                            </label>
                            <input
                                type="date"
                                required
                                value={date}
                                onChange={(e) => setDate(e.target.value)}
                                className="w-full px-3 py-2 text-xs sm:text-sm bg-background border border-border rounded-xl text-text-primary font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                        </div>

                        {/* Notes */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <FileText className="w-3.5 h-3.5 text-primary" />
                                <span>{t('finance.expenses.notes', 'ملاحظات إضافية')}</span>
                            </label>
                            <textarea
                                rows={3}
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                placeholder={t('finance.expenses.notes_placeholder', 'أي تفاصيل عن المورد أو الفاتورة...')}
                                className="w-full px-3 py-2 text-xs sm:text-sm bg-background border border-border rounded-xl text-text-primary placeholder:text-text-secondary/60 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                        </div>
                    </form>

                    {/* Footer Actions */}
                    <div className="p-6 border-t border-border bg-muted/10 flex items-center gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 py-2.5 px-4 text-xs font-bold text-text-secondary hover:text-text-primary bg-card border border-border rounded-xl hover:bg-muted/60 transition-colors"
                        >
                            {t('common.cancel', 'إلغاء')}
                        </button>
                        {canWriteFinance && (
                            <button
                                type="submit"
                                form="add-expense-form"
                                disabled={isSubmitting}
                                className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 text-xs font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50 rounded-xl transition-all shadow-sm"
                            >
                                {isSubmitting ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span>{t('common.saving', 'جاري الحفظ...')}</span>
                                    </>
                                ) : (
                                    <>
                                        <Plus className="w-4 h-4" />
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

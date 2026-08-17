import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
    X,
    DollarSign,
    CheckCircle2,
    Clock,
    Loader2,
    Calendar,
    FileText,
} from 'lucide-react';
import Money from '../../components/Money';

/**
 * Slide-over drawer for recording full or partial salary payments (§16 MASTER_SPEC, `FIN-PRL-004`).
 */
export default function SalaryPaymentDrawer({
    employee,
    month,
    isOpen,
    onClose,
    onSave,
    isSaving = false,
}) {
    const { t } = useTranslation();

    const [amount, setAmount] = useState('');
    const [isPartial, setIsPartial] = useState(false);
    const [daysWorked, setDaysWorked] = useState('');
    const [notes, setNotes] = useState('');
    const [formError, setFormError] = useState('');

    const payable = Number(employee?.payable_amount !== undefined ? employee.payable_amount : (employee?.prorated_salary || 0));
    const alreadyPaid = Number(employee?.paid_amount !== undefined ? employee.paid_amount : (employee?.payment?.amount || 0));
    const remaining = Number(employee?.remaining_amount !== undefined ? employee.remaining_amount : Math.max(0, payable - alreadyPaid));

    useEffect(() => {
        if (employee) {
            const initialAmount = remaining > 0 ? remaining : payable;
            setAmount(String(initialAmount));
            setIsPartial(false);
            setDaysWorked(String(employee.days_worked || employee.days_in_month || 30));
            setNotes('');
            setFormError('');
        }
    }, [employee, remaining, payable]);

    if (!isOpen || !employee) return null;

    const handlePayRemaining = () => {
        setAmount(String(remaining));
        setIsPartial(false);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setFormError('');

        const numericAmount = parseFloat(amount);
        if (isNaN(numericAmount) || numericAmount <= 0) {
            setFormError(t('finance.payroll.invalid_amount', 'يرجى إدخال مبلغ صحيح أكبر من صفر'));
            return;
        }

        const days = parseInt(daysWorked, 10);

        try {
            await onSave({
                userId: employee.id,
                amount: numericAmount,
                isPartial,
                daysWorked: !isNaN(days) ? days : undefined,
                notes: notes.trim() || undefined,
            });
            onClose();
        } catch (err) {
            setFormError(
                err.response?.data?.detail ||
                err.message ||
                t('common.error_occurred', 'حدث خطأ أثناء تسجيل الدفع')
            );
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
                                <DollarSign className="w-5 h-5" />
                            </div>
                            <div>
                                <h3 className="text-base font-bold text-text-primary">
                                    {t('finance.payroll.record_payment_title', 'صرف راتب الموظف')}
                                </h3>
                                <p className="text-xs text-text-secondary">
                                    {employee.username} ({employee.role}) • {month}
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

                    {/* Body */}
                    <form id="salary-payment-form" onSubmit={handleSubmit} className="p-6 space-y-5 flex-1">
                        {formError && (
                            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs font-semibold">
                                {formError}
                            </div>
                        )}

                        {/* Salary Summary Pill */}
                        <div className="p-4 rounded-xl border border-border bg-muted/20 space-y-3">
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-text-secondary">{t('finance.payroll.payable', 'الراتب المستحق')}:</span>
                                <Money amount={payable} size="sm" />
                            </div>
                            {alreadyPaid > 0 && (
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-text-secondary">{t('finance.payroll.already_paid', 'المسدد سابقاً')}:</span>
                                    <Money amount={alreadyPaid} size="sm" colored />
                                </div>
                            )}
                            <div className="pt-2 border-t border-border/50 flex items-center justify-between font-bold text-xs">
                                <span className="text-text-primary">{t('finance.payroll.remaining', 'المتبقي للصرف')}:</span>
                                <Money amount={remaining} size="md" colored />
                            </div>
                        </div>

                        {/* Payment Amount Input */}
                        <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                                <label className="text-xs font-bold text-text-primary">
                                    {t('finance.payroll.payment_amount', 'مبلغ الصرف')} *
                                </label>
                                {remaining > 0 && remaining !== Number(amount) && (
                                    <button
                                        type="button"
                                        onClick={handlePayRemaining}
                                        className="text-[11px] font-bold text-primary hover:underline"
                                    >
                                        {t('finance.payroll.pay_remaining_quick', 'صرف كامل المتبقي')}
                                    </button>
                                )}
                            </div>
                            <input
                                type="number"
                                required
                                min="1"
                                step="0.5"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                placeholder="0.00"
                                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-xl text-text-primary font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                        </div>

                        {/* Partial Checkbox */}
                        <label className="flex items-center gap-2.5 cursor-pointer select-none">
                            <input
                                type="checkbox"
                                checked={isPartial}
                                onChange={(e) => setIsPartial(e.target.checked)}
                                className="rounded border-border text-primary focus:ring-primary/20 w-4 h-4"
                            />
                            <div className="text-xs">
                                <span className="font-bold text-text-primary block">
                                    {t('finance.payroll.is_partial_label', 'دفعة جزئية (سلفة / جزء من الراتب)')}
                                </span>
                                <span className="text-text-secondary text-[11px]">
                                    {t('finance.payroll.is_partial_hint', 'حدد هذا الخيار إذا كان المبلغ لا يغلق مستحقات الشهر بالكامل')}
                                </span>
                            </div>
                        </label>

                        {/* Days Worked (Prorated) */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <Calendar className="w-3.5 h-3.5 text-text-secondary" />
                                <span>{t('finance.payroll.days_worked', 'عدد الأيام المحتسبة')}</span>
                            </label>
                            <input
                                type="number"
                                min="1"
                                max="31"
                                value={daysWorked}
                                onChange={(e) => setDaysWorked(e.target.value)}
                                className="w-full px-3 py-2 text-xs bg-background border border-border rounded-xl text-text-primary font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                        </div>

                        {/* Notes */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <FileText className="w-3.5 h-3.5 text-text-secondary" />
                                <span>{t('common.notes', 'ملاحظات الصرف')}</span>
                            </label>
                            <textarea
                                rows={2}
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                placeholder={t('finance.payroll.notes_placeholder', 'سلفة، مكافأة، خصم غياب...')}
                                className="w-full px-3 py-2 text-xs bg-background border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all resize-none"
                            />
                        </div>
                    </form>

                    {/* Footer */}
                    <div className="p-6 border-t border-border bg-muted/10 flex items-center gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 py-2.5 px-4 text-xs font-bold text-text-secondary hover:text-text-primary bg-card border border-border rounded-xl hover:bg-muted/60 transition-colors"
                        >
                            {t('common.cancel', 'إلغاء')}
                        </button>
                        <button
                            type="submit"
                            form="salary-payment-form"
                            disabled={isSaving}
                            className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 text-xs font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50 rounded-xl transition-all shadow-sm"
                        >
                            {isSaving ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <span>{t('common.saving', 'جاري التسجيل...')}</span>
                                </>
                            ) : (
                                <>
                                    <CheckCircle2 className="w-4 h-4" />
                                    <span>{t('finance.payroll.confirm_payment', 'تأكيد تسجيل الصرف')}</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

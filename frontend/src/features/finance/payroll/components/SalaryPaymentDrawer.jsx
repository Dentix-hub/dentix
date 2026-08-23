import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
    DollarSign,
    CheckCircle2,
    Loader2,
    Calendar,
    FileText,
} from 'lucide-react';
import DentixDrawer from '@/shared/ui/DentixDrawer';
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

    const handlePayRemaining = () => {
        setAmount(String(remaining));
        setIsPartial(false);
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setFormError('');

        const numericAmount = parseFloat(amount);
        if (Number.isNaN(numericAmount) || numericAmount <= 0) {
            setFormError(t('finance.payroll.invalid_amount', 'يرجى إدخال مبلغ صحيح أكبر من صفر'));
            return;
        }

        const days = parseInt(daysWorked, 10);

        try {
            await onSave({
                userId: employee.id,
                amount: numericAmount,
                isPartial,
                daysWorked: !Number.isNaN(days) ? days : undefined,
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
        <DentixDrawer
            open={Boolean(isOpen && employee)}
            onOpenChange={(open) => {
                if (!open) onClose?.();
            }}
            title={t('finance.payroll.record_payment_title', 'صرف راتب الموظف')}
            size="md"
            closeLabel={t('common.close', 'إغلاق')}
            closeOnOutside={!isSaving}
        >
            {employee && (
                <div className="space-y-5">
                    <div className="flex items-center gap-3 rounded-xl bg-primary/5 p-3">
                        <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
                            <DollarSign className="h-5 w-5" aria-hidden="true" />
                        </div>
                        <p className="min-w-0 break-words text-xs font-semibold text-text-secondary" dir="auto">
                            {employee.username} ({employee.role}) • <bdi>{month}</bdi>
                        </p>
                    </div>

                    <form id="salary-payment-form" onSubmit={handleSubmit} className="space-y-5">
                        {formError && (
                            <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-xs font-semibold text-destructive" role="alert">
                                {formError}
                            </div>
                        )}

                        <div className="space-y-3 rounded-xl border border-border bg-muted/20 p-4">
                            <div className="flex items-center justify-between gap-3 text-xs">
                                <span className="text-text-secondary">{t('finance.payroll.payable', 'الراتب المستحق')}:</span>
                                <Money amount={payable} size="sm" />
                            </div>
                            {alreadyPaid > 0 && (
                                <div className="flex items-center justify-between gap-3 text-xs">
                                    <span className="text-text-secondary">{t('finance.payroll.already_paid', 'المسدد سابقاً')}:</span>
                                    <Money amount={alreadyPaid} size="sm" colored />
                                </div>
                            )}
                            <div className="flex items-center justify-between gap-3 border-t border-border/50 pt-2 text-xs font-bold">
                                <span className="text-text-primary">{t('finance.payroll.remaining', 'المتبقي للصرف')}:</span>
                                <Money amount={remaining} size="md" colored />
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <div className="flex items-center justify-between gap-3">
                                <label htmlFor="salary-payment-amount" className="text-xs font-bold text-text-primary">
                                    {t('finance.payroll.payment_amount', 'مبلغ الصرف')} *
                                </label>
                                {remaining > 0 && remaining !== Number(amount) && (
                                    <button
                                        type="button"
                                        onClick={handlePayRemaining}
                                        className="text-[11px] font-bold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                                    >
                                        {t('finance.payroll.pay_remaining_quick', 'صرف كامل المتبقي')}
                                    </button>
                                )}
                            </div>
                            <input
                                id="salary-payment-amount"
                                type="number"
                                required
                                min="1"
                                step="0.5"
                                inputMode="decimal"
                                dir="ltr"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                placeholder="0.00"
                                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm font-mono text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20"
                            />
                        </div>

                        <label className="flex cursor-pointer select-none items-center gap-2.5">
                            <input
                                type="checkbox"
                                checked={isPartial}
                                onChange={(e) => setIsPartial(e.target.checked)}
                                className="h-4 w-4 rounded border-border text-primary focus:ring-primary/20"
                            />
                            <span className="text-xs">
                                <span className="block font-bold text-text-primary">
                                    {t('finance.payroll.is_partial_label', 'دفعة جزئية (سلفة / جزء من الراتب)')}
                                </span>
                                <span className="text-[11px] text-text-secondary">
                                    {t('finance.payroll.is_partial_hint', 'حدد هذا الخيار إذا كان المبلغ لا يغلق مستحقات الشهر بالكامل')}
                                </span>
                            </span>
                        </label>

                        <div className="space-y-1.5">
                            <label htmlFor="salary-days-worked" className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <Calendar className="h-3.5 w-3.5 text-text-secondary" aria-hidden="true" />
                                <span>{t('finance.payroll.days_worked', 'عدد الأيام المحتسبة')}</span>
                            </label>
                            <input
                                id="salary-days-worked"
                                type="number"
                                min="1"
                                max="31"
                                inputMode="numeric"
                                dir="ltr"
                                value={daysWorked}
                                onChange={(e) => setDaysWorked(e.target.value)}
                                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs font-mono text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label htmlFor="salary-payment-notes" className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <FileText className="h-3.5 w-3.5 text-text-secondary" aria-hidden="true" />
                                <span>{t('common.notes', 'ملاحظات الصرف')}</span>
                            </label>
                            <textarea
                                id="salary-payment-notes"
                                rows={2}
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                placeholder={t('finance.payroll.notes_placeholder', 'سلفة، مكافأة، خصم غياب...')}
                                className="w-full resize-none rounded-xl border border-border bg-background px-3 py-2 text-xs text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20"
                            />
                        </div>
                    </form>

                    <div className="flex items-center gap-3 border-t border-border pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            disabled={isSaving}
                            className="flex-1 rounded-xl border border-border bg-card px-4 py-2.5 text-xs font-bold text-text-secondary transition-colors hover:bg-muted/60 hover:text-text-primary disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        >
                            {t('common.cancel', 'إلغاء')}
                        </button>
                        <button
                            type="submit"
                            form="salary-payment-form"
                            disabled={isSaving}
                            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white shadow-sm transition-all hover:bg-primary/90 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                        >
                            {isSaving ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                                    <span>{t('common.saving', 'جاري التسجيل...')}</span>
                                </>
                            ) : (
                                <>
                                    <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                                    <span>{t('finance.payroll.confirm_payment', 'تأكيد تسجيل الصرف')}</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            )}
        </DentixDrawer>
    );
}

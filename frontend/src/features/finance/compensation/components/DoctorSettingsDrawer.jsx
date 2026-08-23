import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
    Settings,
    Percent,
    DollarSign,
    Loader2,
    Save,
    ShieldAlert,
} from 'lucide-react';
import DentixDrawer from '@/shared/ui/DentixDrawer';
import { useFinancePermissions } from '../../useFinancePermissions';

/**
 * Slide-over drawer for configuring a doctor's compensation rules.
 * Strictly gated by SYSTEM_CONFIG permission (§23 MASTER_SPEC).
 */
export default function DoctorSettingsDrawer({
    doctor,
    isOpen,
    onClose,
    onSave,
    isSaving = false,
}) {
    const { t } = useTranslation();
    const { canConfigFinance } = useFinancePermissions();

    const [commissionPercent, setCommissionPercent] = useState('');
    const [fixedSalary, setFixedSalary] = useState('');
    const [formError, setFormError] = useState('');

    useEffect(() => {
        if (doctor) {
            setCommissionPercent(String(doctor.commission_percent || 0));
            setFixedSalary(String(doctor.fixed_salary || 0));
            setFormError('');
        }
    }, [doctor]);

    const handleSubmit = async (event) => {
        event.preventDefault();
        setFormError('');

        const commission = parseFloat(commissionPercent);
        if (Number.isNaN(commission) || commission < 0 || commission > 100) {
            setFormError(t('finance.compensation.commission_invalid', 'نسبة العمولة يجب أن تكون بين 0% و 100%'));
            return;
        }

        const salary = parseFloat(fixedSalary);
        if (Number.isNaN(salary) || salary < 0) {
            setFormError(t('finance.compensation.salary_invalid', 'قيمة الراتب الثابت يجب أن تكون أكبر من أو تساوي صفر'));
            return;
        }

        try {
            await onSave({
                commission_percent: commission,
                fixed_salary: salary,
                per_appointment_fee: 0,
            });
            onClose();
        } catch (err) {
            setFormError(err.response?.data?.detail || err.message || t('common.error_occurred', 'حدث خطأ أثناء حفظ الإعدادات'));
        }
    };

    const open = Boolean(isOpen && doctor);

    if (!canConfigFinance) {
        return (
            <DentixDrawer
                open={open}
                onOpenChange={(nextOpen) => {
                    if (!nextOpen) onClose?.();
                }}
                title={t('common.access_denied', 'غير مصرح بالوصول')}
                size="sm"
                closeLabel={t('common.close', 'إغلاق')}
            >
                <div className="space-y-4 text-center">
                    <ShieldAlert className="mx-auto h-10 w-10 text-destructive" aria-hidden="true" />
                    <p className="text-xs text-text-secondary">
                        {t('finance.compensation.config_permission_required', 'تعديل قواعد أتعاب الأطباء يتطلب صلاحيات إدارة النظام.')}
                    </p>
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-xl bg-muted px-4 py-2 text-xs font-bold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                    >
                        {t('common.close', 'إغلاق')}
                    </button>
                </div>
            </DentixDrawer>
        );
    }

    return (
        <DentixDrawer
            open={open}
            onOpenChange={(nextOpen) => {
                if (!nextOpen) onClose?.();
            }}
            title={t('finance.compensation.settings_title', 'إعدادات أتعاب الطبيب')}
            size="md"
            closeLabel={t('common.close', 'إغلاق')}
            closeOnOutside={!isSaving}
        >
            {doctor && (
                <div className="space-y-5">
                    <div className="flex items-center gap-3 rounded-xl bg-primary/5 p-3">
                        <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
                            <Settings className="h-5 w-5" aria-hidden="true" />
                        </div>
                        <p className="min-w-0 break-words text-xs font-semibold text-text-secondary" dir="auto">
                            {doctor.doctor_name || doctor.username}
                        </p>
                    </div>

                    <form id="doctor-settings-form" onSubmit={handleSubmit} className="space-y-4">
                        {formError && (
                            <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-xs font-semibold text-destructive" role="alert">
                                {formError}
                            </div>
                        )}

                        <div className="space-y-1.5">
                            <label htmlFor="doctor-commission-percent" className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <Percent className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                                <span>{t('finance.compensation.commission_rate', 'نسبة العمولة من الصافي (%)')} *</span>
                            </label>
                            <input
                                id="doctor-commission-percent"
                                type="number"
                                required
                                min="0"
                                max="100"
                                step="0.1"
                                inputMode="decimal"
                                dir="ltr"
                                value={commissionPercent}
                                onChange={(e) => setCommissionPercent(e.target.value)}
                                placeholder="0.0"
                                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs font-mono text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                            <p className="text-[11px] text-text-secondary">
                                {t('finance.compensation.commission_desc', 'تحتسب من إجمالي المحصل منسوباً للطبيب بعد خصم تكاليف المعمل')}
                            </p>
                        </div>

                        <div className="space-y-1.5">
                            <label htmlFor="doctor-fixed-salary" className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <DollarSign className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                                <span>{t('finance.compensation.fixed_salary', 'الراتب الأساسي الثابت (جنيه)')} *</span>
                            </label>
                            <input
                                id="doctor-fixed-salary"
                                type="number"
                                required
                                min="0"
                                step="1"
                                inputMode="decimal"
                                dir="ltr"
                                value={fixedSalary}
                                onChange={(e) => setFixedSalary(e.target.value)}
                                placeholder="0.00"
                                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs font-mono text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                            <p className="text-[11px] text-text-secondary">
                                {t('finance.compensation.salary_desc', 'مبلغ ثابت يضاف لمستحقات الطبيب شهرياً')}
                            </p>
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
                            form="doctor-settings-form"
                            disabled={isSaving}
                            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white shadow-sm transition-all hover:bg-primary/90 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                        >
                            {isSaving ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                                    <span>{t('common.saving', 'جاري الحفظ...')}</span>
                                </>
                            ) : (
                                <>
                                    <Save className="h-4 w-4" aria-hidden="true" />
                                    <span>{t('common.save', 'حفظ التعديلات')}</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            )}
        </DentixDrawer>
    );
}

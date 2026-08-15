import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
    X,
    Settings,
    Percent,
    DollarSign,
    Loader2,
    Save,
    ShieldAlert,
} from 'lucide-react';
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

    if (!isOpen || !doctor) return null;

    if (!canConfigFinance) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
                <div className="p-6 bg-card border border-border rounded-2xl max-w-sm text-center space-y-3">
                    <ShieldAlert className="w-10 h-10 text-destructive mx-auto" />
                    <h3 className="text-sm font-bold text-text-primary">
                        {t('common.access_denied', 'غير مصرح بالوصول')}
                    </h3>
                    <p className="text-xs text-text-secondary">
                        {t('finance.compensation.config_permission_required', 'تعديل قواعد أتعاب الأطباء يتطلب صلاحيات إدارة النظام.')}
                    </p>
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 text-xs font-bold bg-muted rounded-xl"
                    >
                        {t('common.close', 'إغلاق')}
                    </button>
                </div>
            </div>
        );
    }

    const handleSubmit = async (e) => {
        e.preventDefault();
        setFormError('');

        const comm = parseFloat(commissionPercent);
        if (isNaN(comm) || comm < 0 || comm > 100) {
            setFormError(t('finance.compensation.commission_invalid', 'نسبة العمولة يجب أن تكون بين 0% و 100%'));
            return;
        }

        const salary = parseFloat(fixedSalary);
        if (isNaN(salary) || salary < 0) {
            setFormError(t('finance.compensation.salary_invalid', 'قيمة الراتب الثابت يجب أن تكون أكبر من أو تساوي صفر'));
            return;
        }

        try {
            await onSave({
                commission_percent: comm,
                fixed_salary: salary,
                per_appointment_fee: 0,
            });
            onClose();
        } catch (err) {
            setFormError(err.response?.data?.detail || err.message || t('common.error_occurred', 'حدث خطأ أثناء حفظ الإعدادات'));
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
                                <Settings className="w-5 h-5" />
                            </div>
                            <div>
                                <h3 className="text-base font-bold text-text-primary">
                                    {t('finance.compensation.settings_title', 'إعدادات أتعاب الطبيب')}
                                </h3>
                                <p className="text-xs text-text-secondary">
                                    {doctor.doctor_name || doctor.username}
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
                    <form id="doctor-settings-form" onSubmit={handleSubmit} className="p-6 space-y-4 flex-1">
                        {formError && (
                            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs font-semibold">
                                {formError}
                            </div>
                        )}

                        {/* Commission % */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <Percent className="w-3.5 h-3.5 text-primary" />
                                <span>{t('finance.compensation.commission_rate', 'نسبة العمولة من الصافي (%)')} *</span>
                            </label>
                            <input
                                type="number"
                                required
                                min="0"
                                max="100"
                                step="0.1"
                                value={commissionPercent}
                                onChange={(e) => setCommissionPercent(e.target.value)}
                                placeholder="0.0"
                                className="w-full px-3 py-2 text-xs sm:text-sm bg-background border border-border rounded-xl text-text-primary font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                            <p className="text-[11px] text-text-secondary">
                                {t('finance.compensation.commission_desc', 'تحتسب من إجمالي المحصل منسوباً للطبيب بعد خصم تكاليف المعمل')}
                            </p>
                        </div>

                        {/* Fixed Salary */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <DollarSign className="w-3.5 h-3.5 text-primary" />
                                <span>{t('finance.compensation.fixed_salary', 'الراتب الأساسي الثابت (جنيه)')} *</span>
                            </label>
                            <input
                                type="number"
                                required
                                min="0"
                                step="1"
                                value={fixedSalary}
                                onChange={(e) => setFixedSalary(e.target.value)}
                                placeholder="0.00"
                                className="w-full px-3 py-2 text-xs sm:text-sm bg-background border border-border rounded-xl text-text-primary font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                            <p className="text-[11px] text-text-secondary">
                                {t('finance.compensation.salary_desc', 'مبلغ ثابت يضاف لمستحقات الطبيب شهرياً')}
                            </p>
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
                        <button
                            type="submit"
                            form="doctor-settings-form"
                            disabled={isSaving}
                            className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 text-xs font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50 rounded-xl transition-all shadow-sm"
                        >
                            {isSaving ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <span>{t('common.saving', 'جاري الحفظ...')}</span>
                                </>
                            ) : (
                                <>
                                    <Save className="w-4 h-4" />
                                    <span>{t('common.save', 'حفظ التعديلات')}</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

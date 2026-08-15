import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
    X,
    Settings,
    DollarSign,
    Calendar,
    Loader2,
    Save,
    ShieldAlert,
} from 'lucide-react';
import { useFinancePermissions } from '../../useFinancePermissions';

/**
 * Drawer for managing employee base compensation rules and hire date (§16 MASTER_SPEC, `FIN-PRL-005`).
 */
export default function StaffSettingsDrawer({
    employee,
    isOpen,
    onClose,
    onSave,
    isSaving = false,
}) {
    const { t } = useTranslation();
    const { canConfigFinance } = useFinancePermissions();

    const [salary, setSalary] = useState('');
    const [hireDate, setHireDate] = useState('');
    const [formError, setFormError] = useState('');

    useEffect(() => {
        if (employee) {
            setSalary(String(employee.base_salary || 0));
            setHireDate(employee.hire_date ? employee.hire_date.substring(0, 10) : '');
            setFormError('');
        }
    }, [employee]);

    if (!isOpen || !employee) return null;

    if (!canConfigFinance) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
                <div className="p-6 bg-card border border-border rounded-2xl max-w-sm text-center space-y-3">
                    <ShieldAlert className="w-10 h-10 text-destructive mx-auto" />
                    <h3 className="text-sm font-bold text-text-primary">
                        {t('common.access_denied', 'غير مصرح بالوصول')}
                    </h3>
                    <p className="text-xs text-text-secondary">
                        {t('finance.payroll.config_permission_required', 'تعديل رواتب الموظفين يتطلب صلاحيات إدارة النظام.')}
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

        const numericSalary = parseFloat(salary);
        if (isNaN(numericSalary) || numericSalary < 0) {
            setFormError(t('finance.payroll.invalid_salary', 'يرجى إدخال راتب أساسي صحيح'));
            return;
        }

        try {
            await onSave({
                userId: employee.id,
                salary: numericSalary,
                hireDate: hireDate.trim() || null,
            });
            onClose();
        } catch (err) {
            setFormError(
                err.response?.data?.detail ||
                err.message ||
                t('common.error_occurred', 'حدث خطأ أثناء حفظ التعديلات')
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
                                <Settings className="w-5 h-5" />
                            </div>
                            <div>
                                <h3 className="text-base font-bold text-text-primary">
                                    {t('finance.payroll.staff_settings_title', 'قواعد راتب الموظف')}
                                </h3>
                                <p className="text-xs text-text-secondary">
                                    {employee.username} ({employee.role})
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

                    {/* Form */}
                    <form id="staff-settings-form" onSubmit={handleSubmit} className="p-6 space-y-4 flex-1">
                        {formError && (
                            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs font-semibold">
                                {formError}
                            </div>
                        )}

                        {/* Base Salary */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <DollarSign className="w-3.5 h-3.5 text-primary" />
                                <span>{t('finance.payroll.base_salary_label', 'الراتب الأساسي الشهري (جنيه)')} *</span>
                            </label>
                            <input
                                type="number"
                                required
                                min="0"
                                step="1"
                                value={salary}
                                onChange={(e) => setSalary(e.target.value)}
                                placeholder="0.00"
                                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-xl text-text-primary font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                        </div>

                        {/* Hire Date */}
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                                <Calendar className="w-3.5 h-3.5 text-primary" />
                                <span>{t('finance.payroll.hire_date_label', 'تاريخ بداية العمل / التعيين')}</span>
                            </label>
                            <input
                                type="date"
                                value={hireDate}
                                onChange={(e) => setHireDate(e.target.value)}
                                className="w-full px-3 py-2 text-xs bg-background border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                            <p className="text-[11px] text-text-secondary">
                                {t('finance.payroll.hire_date_hint', 'يستخدم لاحتساب نسبة الأيام الفعلية للموظف في شهر التعيين')}
                            </p>
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
                            form="staff-settings-form"
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

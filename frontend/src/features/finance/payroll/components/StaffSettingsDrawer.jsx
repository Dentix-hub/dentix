import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
    Settings,
    DollarSign,
    Calendar,
    Loader2,
    Save,
    ShieldAlert,
} from 'lucide-react';
import DentixDrawer from '@/shared/ui/DentixDrawer';
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

    const handleSubmit = async (event) => {
        event.preventDefault();
        setFormError('');

        const numericSalary = parseFloat(salary);
        if (Number.isNaN(numericSalary) || numericSalary < 0) {
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

    const open = Boolean(isOpen && employee);

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
                        {t('finance.payroll.config_permission_required', 'تعديل رواتب الموظفين يتطلب صلاحيات إدارة النظام.')}
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
            title={t('finance.payroll.staff_settings_title', 'قواعد راتب الموظف')}
            size="md"
            closeLabel={t('common.close', 'إغلاق')}
            closeOnOutside={!isSaving}
        >
            {employee && (
                <div className="space-y-5">
                    <div className="flex items-center gap-3 rounded-xl bg-primary/5 p-3">
                        <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
                            <Settings className="h-5 w-5" aria-hidden="true" />
                        </div>
                        <p className="min-w-0 break-words text-xs font-semibold text-text-secondary" dir="auto">
                            {employee.username} ({employee.role})
                        </p>
                    </div>

                    <form id="staff-settings-form" onSubmit={handleSubmit} className="space-y-4">
                        {formError && (
                            <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-xs font-semibold text-destructive" role="alert">
                                {formError}
                            </div>
                        )}

                        <div className="space-y-1.5">
                            <label htmlFor="staff-base-salary" className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <DollarSign className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                                <span>{t('finance.payroll.base_salary_label', 'الراتب الأساسي الشهري (جنيه)')} *</span>
                            </label>
                            <input
                                id="staff-base-salary"
                                type="number"
                                required
                                min="0"
                                step="1"
                                inputMode="decimal"
                                dir="ltr"
                                value={salary}
                                onChange={(e) => setSalary(e.target.value)}
                                placeholder="0.00"
                                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm font-mono text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label htmlFor="staff-hire-date" className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <Calendar className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                                <span>{t('finance.payroll.hire_date_label', 'تاريخ بداية العمل / التعيين')}</span>
                            </label>
                            <input
                                id="staff-hire-date"
                                type="date"
                                dir="ltr"
                                value={hireDate}
                                onChange={(e) => setHireDate(e.target.value)}
                                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary/20"
                            />
                            <p className="text-[11px] text-text-secondary">
                                {t('finance.payroll.hire_date_hint', 'يستخدم لاحتساب نسبة الأيام الفعلية للموظف في شهر التعيين')}
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
                            form="staff-settings-form"
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

import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
    X,
    Phone,
    FileSpreadsheet,
    CreditCard,
    Plus,
    ExternalLink,
    AlertTriangle,
} from 'lucide-react';
import Money from '../../components/Money';
import ScopeBadge from '../../components/ScopeBadge';
import { useFinancePermissions } from '../../useFinancePermissions';

/**
 * Patient Financial Statement Drawer.
 * Displays patient account breakdown and provides contextual "Record Payment" action.
 */
export default function PatientStatementDrawer({
    patient,
    isOpen,
    onClose,
    onRecordPayment,
}) {
    const { t } = useTranslation();
    const { canWriteFinance } = useFinancePermissions();

    if (!isOpen || !patient) return null;

    const allTimeDebt = Number(patient.all_time_outstanding) || 0;
    const totalInvoiced = Number(patient.total_invoiced) || 0;
    const totalPaid = Number(patient.total_paid) || 0;

    return (
        <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity duration-300"
                onClick={onClose}
                aria-hidden="true"
            />

            <div className="fixed inset-y-0 end-0 max-w-full flex pl-10 rtl:pl-0 rtl:pr-10">
                <div
                    data-testid="patient-statement-panel"
                    className="w-screen max-w-md bg-white dark:bg-slate-950 border-s border-border shadow-2xl flex flex-col justify-between overflow-y-auto"
                >
                    {/* Header */}
                    <div className="p-6 border-b border-border space-y-3">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-mono font-bold text-text-secondary">
                                #{patient.file_number || patient.patient_id}
                            </span>
                            <button
                                type="button"
                                onClick={onClose}
                                className="p-2 rounded-xl text-text-secondary hover:text-text-primary hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                                aria-label={t('common.close', 'إغلاق')}
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-1">
                            <h3 className="text-base font-bold text-text-primary">
                                {patient.patient_name}
                            </h3>
                            <div className="flex items-center gap-2 text-xs text-text-secondary">
                                {patient.patient_phone && (
                                    <span className="flex items-center gap-1 font-mono" dir="ltr">
                                        <Phone className="w-3 h-3 text-primary" />
                                        {patient.patient_phone}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Body */}
                    <div className="p-6 space-y-6 flex-1">
                        {/* Outstanding Debt Card */}
                        <div className="p-4 rounded-2xl border border-amber-200 dark:border-amber-900/50 bg-amber-50 dark:bg-amber-950/30 space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
                                    <AlertTriangle className="w-4 h-4" />
                                    <span>{t('finance.receivables.total_debt', 'المديونية التراكمية (الذمة القائمة)')}</span>
                                </span>
                                <ScopeBadge scope="all_time" />
                            </div>
                            <div className="pt-1">
                                <Money
                                    amount={allTimeDebt}
                                    size="2xl"
                                    colored
                                />
                            </div>
                            <p className="text-[11px] text-text-secondary">
                                {t('finance.receivables.debt_desc', 'إجمالي المبالغ غير المسددة عبر جميع الفترات العلاجية')}
                            </p>
                        </div>

                        {/* Breakdown */}
                        <div className="space-y-3">
                            <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                                {t('finance.receivables.breakdown_title', 'ملخص الحركات')}
                            </h4>

                            <div className="space-y-2">
                                <div className="p-3.5 rounded-xl border border-border bg-slate-50 dark:bg-slate-900 flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <FileSpreadsheet className="w-4 h-4 text-primary" />
                                        <span className="text-xs text-text-secondary">{t('finance.metrics.invoiced', 'إجمالي الخدمات المحتسبة')}</span>
                                    </div>
                                    <Money amount={totalInvoiced} size="sm" />
                                </div>

                                <div className="p-3.5 rounded-xl border border-border bg-slate-50 dark:bg-slate-900 flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <CreditCard className="w-4 h-4 text-emerald-500" />
                                        <span className="text-xs text-text-secondary">{t('finance.metrics.collected', 'إجمالي الدفعات المسددة')}</span>
                                    </div>
                                    <Money amount={totalPaid} size="sm" colored />
                                </div>
                            </div>
                        </div>

                        {/* Profile Link */}
                        <div className="p-4 rounded-xl border border-border bg-slate-50 dark:bg-slate-900 flex items-center justify-between">
                            <div className="space-y-0.5">
                                <p className="text-xs font-bold text-text-primary">{t('patients.full_record', 'الملف الطبي والمالي الكامل')}</p>
                                <p className="text-[11px] text-text-secondary">{t('patients.view_timeline', 'عرض سجل الجلسات والفواتير التفصيلية')}</p>
                            </div>
                            <Link
                                to={`/patients/${patient.patient_id}`}
                                className="inline-flex items-center gap-1 px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary text-xs font-bold rounded-lg transition-colors"
                            >
                                <span>{t('common.view', 'عرض')}</span>
                                <ExternalLink className="w-3.5 h-3.5" />
                            </Link>
                        </div>
                    </div>

                    {/* Footer Action */}
                    <div className="p-6 border-t border-border bg-slate-50 dark:bg-slate-900 space-y-3">
                        {canWriteFinance && (
                            <button
                                type="button"
                                onClick={() => {
                                    onClose();
                                    if (onRecordPayment) onRecordPayment(patient);
                                }}
                                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 text-xs font-bold text-white bg-primary hover:bg-primary/90 rounded-xl transition-all shadow-sm"
                            >
                                <Plus className="w-4 h-4" />
                                <span>{t('finance.payments.record_btn', 'تسجيل دفعة لهذا المريض')}</span>
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
    X,
    CreditCard,
    User,
    DollarSign,
    FileText,
    AlertCircle,
    Check,
} from 'lucide-react';
import { getPatients } from '@/api/patients';

/**
 * Record Payment Modal.
 * Allows receptionists/admins with FINANCIAL_WRITE to record patient cash collections.
 */
export default function RecordPaymentModal({
    isOpen,
    onClose,
    onSubmit,
    isSubmitting = false,
}) {
    const { t } = useTranslation();

    const [patientId, setPatientId] = useState('');
    const [amount, setAmount] = useState('');
    const [notes, setNotes] = useState('');
    const [error, setError] = useState(null);

    // Fetch patient options for dropdown
    const { data: patients = [], isLoading: isLoadingPatients } = useQuery({
        queryKey: ['patients', 'options'],
        queryFn: async () => {
            const res = await getPatients();
            const list = Array.isArray(res.data?.data) ? res.data.data : Array.isArray(res.data) ? res.data : [];
            return list;
        },
        enabled: isOpen,
        staleTime: 5 * 60 * 1000,
    });

    useEffect(() => {
        if (isOpen) {
            setPatientId('');
            setAmount('');
            setNotes('');
            setError(null);
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        const numAmount = parseFloat(amount);
        if (!patientId) {
            setError(t('finance.payments.error_select_patient', 'يرجى اختيار المريض'));
            return;
        }
        if (isNaN(numAmount) || numAmount <= 0) {
            setError(t('finance.payments.error_invalid_amount', 'يرجى إدخال مبلغ صحيح أكبر من الصفر'));
            return;
        }

        try {
            await onSubmit({
                patient_id: parseInt(patientId, 10),
                amount: numAmount,
                notes: notes.trim() || undefined,
            });
            onClose();
        } catch (err) {
            setError(err.response?.data?.detail || err.message || t('common.error_occurred', 'حدث خطأ أثناء حفظ الدفعة'));
        }
    };

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto flex items-center justify-center p-4" role="dialog" aria-modal="true">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity"
                onClick={onClose}
                aria-hidden="true"
            />

            <div className="relative bg-card border border-border rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 z-10">
                {/* Header */}
                <div className="flex items-center justify-between border-b border-border pb-4">
                    <div className="flex items-center gap-2.5">
                        <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                            <CreditCard className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 className="text-base font-bold text-text-primary">
                                {t('finance.payments.record_title', 'تسجيل دفعة مريض')}
                            </h3>
                            <p className="text-xs text-text-secondary">
                                {t('finance.payments.record_subtitle', 'سند قبض نقدي جديد يتم ترحيله للحسابات')}
                            </p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-muted/60 transition-colors"
                        aria-label={t('common.close', 'إغلاق')}
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {error && (
                    <div className="p-3 rounded-xl border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/20 flex items-center gap-2 text-xs font-semibold text-rose-600 dark:text-rose-400">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        <span>{error}</span>
                    </div>
                )}

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Patient Select */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-text-secondary flex items-center gap-1">
                            <User className="w-3.5 h-3.5 text-primary" />
                            <span>{t('finance.payments.select_patient', 'المريض')} *</span>
                        </label>
                        <select
                            value={patientId}
                            onChange={(e) => setPatientId(e.target.value)}
                            disabled={isLoadingPatients || isSubmitting}
                            className="w-full px-3.5 py-2.5 bg-background border border-border rounded-xl text-xs sm:text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                            required
                        >
                            <option value="">
                                {isLoadingPatients
                                    ? t('common.loading', 'جاري تحميل قائمة المرضى...')
                                    : t('finance.payments.choose_patient', 'اختر المريض من القائمة...')}
                            </option>
                            {patients.map((p) => (
                                <option key={p.id} value={p.id}>
                                    {p.name} {p.file_number ? `(#${p.file_number})` : `(#${p.id})`}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Amount Input */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-text-secondary flex items-center gap-1">
                            <DollarSign className="w-3.5 h-3.5 text-primary" />
                            <span>{t('finance.payments.amount', 'المبلغ (جنيه مصري)')} *</span>
                        </label>
                        <input
                            type="number"
                            min="1"
                            step="any"
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                            placeholder="0.00"
                            disabled={isSubmitting}
                            className="w-full px-3.5 py-2.5 bg-background border border-border rounded-xl text-xs sm:text-sm font-mono text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                            required
                        />
                    </div>

                    {/* Notes */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-text-secondary flex items-center gap-1">
                            <FileText className="w-3.5 h-3.5 text-primary" />
                            <span>{t('finance.payments.notes_label', 'ملاحظات وسند التحصيل (اختياري)')}</span>
                        </label>
                        <textarea
                            rows={3}
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder={t('finance.payments.notes_placeholder', 'مثال: دفعة تحت حساب تقويم الأسنان / جلسة حشو...')}
                            disabled={isSubmitting}
                            className="w-full px-3.5 py-2 bg-background border border-border rounded-xl text-xs sm:text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all resize-none"
                        />
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border">
                        <button
                            type="button"
                            onClick={onClose}
                            disabled={isSubmitting}
                            className="px-4 py-2 text-xs font-bold text-text-secondary hover:text-text-primary bg-muted/60 hover:bg-muted rounded-xl transition-colors"
                        >
                            {t('common.cancel', 'إلغاء')}
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-primary hover:bg-primary/90 rounded-xl transition-colors disabled:opacity-50 shadow-sm"
                        >
                            <Check className="w-4 h-4" />
                            <span>{isSubmitting ? t('common.saving', 'جاري الحفظ...') : t('finance.payments.save_payment', 'تسجيل السند')}</span>
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

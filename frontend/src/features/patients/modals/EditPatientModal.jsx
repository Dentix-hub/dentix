import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getDoctors } from '@/api';
import { toast } from '@/shared/ui';
import PriceListSelector from '@/shared/ui/PriceListSelector';

const MEDICAL_CONDITION_KEYS = [
    'none',
    'diabetes',
    'hypertension',
    'heart_disease',
    'allergy',
    'blood_thinners',
    'hepatitis_c',
    'thyroid',
    'pregnancy',
    'smoking',
];

export default function EditPatientModal({ isOpen, onClose, onSave, initialData }) {
    const { t } = useTranslation();
    const [formData, setFormData] = useState({});
    const [hasExactDob, setHasExactDob] = useState(false);
    const todayIso = new Date().toISOString().split('T')[0];

    const doctorsQuery = useQuery({
        queryKey: ['doctors', 'patient-edit-form'],
        queryFn: async () => {
            const res = await getDoctors();
            return res.data || [];
        },
        enabled: isOpen,
        staleTime: 5 * 60 * 1000,
    });

    useEffect(() => {
        if (isOpen && initialData) {
            const exactDobKnown = Boolean(
                initialData.date_of_birth
                && initialData.date_of_birth_precision === 'exact',
            );
            setHasExactDob(exactDobKnown);
            setFormData({
                name: initialData.name || '',
                age: initialData.age ?? '',
                phone: initialData.phone || '',
                address: initialData.address || '',
                medical_history: initialData.medical_history || '',
                date_of_birth: exactDobKnown ? initialData.date_of_birth : '',
                default_price_list_id: initialData.default_price_list_id ?? '',
                assigned_doctor_id: initialData.assigned_doctor_id ?? '',
            });
        }
    }, [isOpen, initialData]);

    const toggleMedicalCondition = (conditionKey) => {
        const condition = t(`patients.medical_conditions.${conditionKey}`);
        const none = t('patients.medical_conditions.none');
        const separator = t('common.separator', '، ');

        if (conditionKey === 'none') {
            setFormData((prev) => ({ ...prev, medical_history: none }));
            return;
        }

        let current = formData.medical_history
            ? String(formData.medical_history).split(separator).map((item) => item.trim()).filter(Boolean)
            : [];
        current = current.filter((item) => item !== none);
        current = current.includes(condition)
            ? current.filter((item) => item !== condition)
            : [...current, condition];
        setFormData((prev) => ({ ...prev, medical_history: current.join(separator) }));
    };

    const parseOptionalInt = (val) => {
        if (val === '' || val === null || val === undefined) return null;
        const parsed = Number.parseInt(val, 10);
        return Number.isNaN(parsed) ? null : parsed;
    };

    const handleSubmit = (event) => {
        event.preventDefault();
        const trimmedName = formData.name?.trim() || '';
        if (!trimmedName) {
            toast.error(t('patients.form.name_required', 'Patient name is required'));
            return;
        }
        if (hasExactDob && formData.date_of_birth && formData.date_of_birth > todayIso) {
            toast.error(t('patients.form.future_dob_error', 'تاريخ الميلاد لا يمكن أن يكون في المستقبل'));
            return;
        }
        const payload = {
            ...formData,
            name: trimmedName,
            phone: formData.phone?.trim() || '',
            address: formData.address?.trim() || '',
            medical_history: formData.medical_history?.trim() || '',
            age: parseOptionalInt(formData.age),
            assigned_doctor_id: parseOptionalInt(formData.assigned_doctor_id),
            default_price_list_id: parseOptionalInt(formData.default_price_list_id),
        };

        if (hasExactDob) {
            payload.date_of_birth = formData.date_of_birth?.trim() || null;
        } else if (initialData?.date_of_birth_precision === 'exact') {
            // Clearing an existing exact DOB is explicit: the user switched back to age-only mode.
            payload.date_of_birth = null;
        } else {
            delete payload.date_of_birth;
        }

        onSave(payload);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="edit-patient-title">
            <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-900">
                <h3 id="edit-patient-title" className="mb-4 text-xl font-bold text-text-primary">
                    {t('patient_details.edit_modal.title')}
                </h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <label className="block space-y-1.5 text-sm font-bold text-text-secondary">
                        <span>{t('patients.form.name_label')}</span>
                        <input
                            value={formData.name || ''}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="w-full rounded-xl border border-border bg-input p-3 text-text-primary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                            required
                            dir="auto"
                        />
                    </label>

                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <label className="block space-y-1.5 text-sm font-bold text-text-secondary">
                            <span>{t('patients.form.age_label')}</span>
                            <input
                                type="number"
                                inputMode="numeric"
                                min="0"
                                max="120"
                                value={formData.age ?? ''}
                                onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                                disabled={hasExactDob}
                                className="w-full rounded-xl border border-border bg-input p-3 text-text-primary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50"
                            />
                        </label>
                        <label className="block space-y-1.5 text-sm font-bold text-text-secondary">
                            <span>{t('patients.form.phone_label')}</span>
                            <input
                                type="tel"
                                inputMode="tel"
                                value={formData.phone || ''}
                                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                                className="w-full rounded-xl border border-border bg-input p-3 text-text-primary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                                dir="ltr"
                            />
                        </label>
                    </div>

                    <div className="rounded-xl border border-border bg-surface-hover/40 p-3">
                        <label className="flex cursor-pointer items-center gap-3 text-sm font-bold text-text-secondary">
                            <input
                                type="checkbox"
                                checked={hasExactDob}
                                onChange={(e) => setHasExactDob(e.target.checked)}
                                className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                            />
                            {t('patients.exact_dob_known')}
                        </label>
                        {hasExactDob && (
                            <label className="mt-3 block space-y-1.5 text-sm font-bold text-text-secondary">
                                <span>{t('patients.date_of_birth')}</span>
                                <input
                                    type="date"
                                    max={todayIso}
                                    value={formData.date_of_birth || ''}
                                    onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                                    className="w-full rounded-xl border border-border bg-input p-3 text-text-primary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                                    required
                                />
                            </label>
                        )}
                        <p className="mt-2 text-xs text-text-muted">{t('patients.dob_hint')}</p>
                    </div>

                    <label className="block space-y-1.5 text-sm font-bold text-text-secondary">
                        <span>{t('patients.form.address_label')}</span>
                        <input
                            value={formData.address || ''}
                            onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                            className="w-full rounded-xl border border-border bg-input p-3 text-text-primary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                            dir="auto"
                        />
                    </label>

                    <div className="space-y-2 rounded-xl border border-border bg-surface-hover/40 p-3">
                        <label className="block text-sm font-bold text-text-secondary" htmlFor="edit-patient-medical-history">
                            {t('patients.form.medical_history')}
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {MEDICAL_CONDITION_KEYS.map((conditionKey) => {
                                const condition = t(`patients.medical_conditions.${conditionKey}`);
                                const currentHistory = String(formData.medical_history || '');
                                const isSelected = conditionKey === 'none'
                                    ? currentHistory === condition
                                    : currentHistory.includes(condition);
                                return (
                                    <button
                                        key={conditionKey}
                                        type="button"
                                        onClick={() => toggleMedicalCondition(conditionKey)}
                                        aria-pressed={isSelected}
                                        className={`rounded-xl border px-3 py-1.5 text-xs font-bold transition ${isSelected ? 'border-rose-500 bg-rose-500 text-white' : 'border-border bg-surface text-text-secondary hover:border-rose-300'}`}
                                    >
                                        {condition}
                                    </button>
                                );
                            })}
                        </div>
                        <textarea
                            id="edit-patient-medical-history"
                            value={formData.medical_history || ''}
                            onChange={(e) => setFormData({ ...formData, medical_history: e.target.value })}
                            placeholder={t('patients.form.other_notes')}
                            className="min-h-20 w-full resize-y rounded-xl border border-border bg-input p-3 text-sm text-text-primary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                            dir="auto"
                        />
                    </div>

                    <div className="rounded-xl border border-border bg-surface-hover/40 p-3">
                        <label className="mb-2 block text-sm font-bold text-text-secondary">
                            {t('patient_details.edit_modal.price_list_label')}
                        </label>
                        <PriceListSelector
                            value={formData.default_price_list_id ?? ''}
                            onChange={(val) => setFormData((prev) => ({ ...prev, default_price_list_id: val }))}
                        />
                        <p className="mt-1 text-xs text-text-muted">{t('patient_details.edit_modal.price_list_hint')}</p>
                    </div>

                    <div className="rounded-xl border border-border bg-surface-hover/40 p-3">
                        <label className="mb-2 block text-sm font-bold text-text-secondary" htmlFor="edit-patient-doctor">
                            {t('patient_details.edit_modal.doctor_label')}
                        </label>
                        <select
                            id="edit-patient-doctor"
                            value={formData.assigned_doctor_id || ''}
                            onChange={(e) => setFormData({ ...formData, assigned_doctor_id: e.target.value })}
                            className="w-full rounded-xl border border-border bg-input p-3 text-text-primary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                        >
                            <option value="">{t('patient_details.edit_modal.doctor_select')}</option>
                            {(doctorsQuery.data || []).map((doctor) => (
                                <option key={doctor.id} value={doctor.id}>
                                    {t('common.doctor_prefix', 'د.')} {doctor.full_name || doctor.username}
                                </option>
                            ))}
                        </select>
                        <p className="mt-1 text-xs text-text-muted">{t('patient_details.edit_modal.doctor_hint')}</p>
                    </div>

                    <div className="flex justify-end gap-3 pt-2">
                        <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 font-bold text-text-secondary hover:bg-surface-hover focus:outline-none focus:ring-2 focus:ring-primary/30">
                            {t('common.cancel')}
                        </button>
                        <button type="submit" className="rounded-lg bg-primary px-6 py-2 font-bold text-white hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary/40 focus:ring-offset-2">
                            {t('common.save')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

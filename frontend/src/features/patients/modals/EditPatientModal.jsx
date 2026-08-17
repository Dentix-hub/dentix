import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getDoctors } from '@/api';
import PriceListSelector from '@/shared/ui/PriceListSelector';

export default function EditPatientModal({ isOpen, onClose, onSave, initialData }) {
    const { t } = useTranslation();
    const [formData, setFormData] = useState({});
    const [hasExactDob, setHasExactDob] = useState(false);

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
                date_of_birth: exactDobKnown ? initialData.date_of_birth : '',
                default_price_list_id: initialData.default_price_list_id ?? '',
                assigned_doctor_id: initialData.assigned_doctor_id ?? '',
            });
        }
    }, [isOpen, initialData]);

    const handleSubmit = (event) => {
        event.preventDefault();
        const payload = {
            ...formData,
            name: formData.name?.trim() || '',
            phone: formData.phone?.trim() || '',
            address: formData.address?.trim() || '',
            age: formData.age === '' ? null : Number.parseInt(formData.age, 10),
            assigned_doctor_id: formData.assigned_doctor_id === ''
                ? null
                : Number.parseInt(formData.assigned_doctor_id, 10),
        };

        if (hasExactDob) {
            payload.date_of_birth = formData.date_of_birth || null;
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

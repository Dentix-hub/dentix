import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getDoctors } from '@/api';
import { useAuth } from '@/auth/useAuth';
import { useCreatePatient } from '@/hooks/usePatients';
import { Modal, Button, Input, toast } from '@/shared/ui';

const EMPTY_FORM = {
    name: '',
    age: '',
    phone: '',
    address: '',
    medical_history: '',
    assigned_doctor_id: '',
    date_of_birth: '',
};

export default function PatientModal({ isOpen, onClose, onSuccess }) {
    const { t } = useTranslation();
    const { user } = useAuth();
    const createPatientMutation = useCreatePatient();
    const [hasExactDob, setHasExactDob] = useState(false);
    const [formData, setFormData] = useState(EMPTY_FORM);

    const doctorsQuery = useQuery({
        queryKey: ['doctors', 'patient-form'],
        queryFn: async () => {
            const res = await getDoctors();
            return res.data || [];
        },
        enabled: isOpen,
        staleTime: 5 * 60 * 1000,
    });

    useEffect(() => {
        if (!isOpen) {
            setFormData(EMPTY_FORM);
            setHasExactDob(false);
            return;
        }
        if (user?.role === 'doctor') {
            setFormData((prev) => ({ ...prev, assigned_doctor_id: user.id }));
        }
    }, [isOpen, user]);

    const handleInputChange = (field, value) => {
        setFormData((prev) => ({ ...prev, [field]: value }));
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (createPatientMutation.isPending) return;
        if (!formData.name.trim()) {
            toast.error(t('patients.form.name_required'));
            return;
        }

        const payload = {
            name: formData.name.trim(),
            age: formData.age === '' ? null : Number.parseInt(formData.age, 10),
            phone: formData.phone.trim(),
            address: formData.address.trim() || null,
            medical_history: formData.medical_history.trim(),
            assigned_doctor_id: formData.assigned_doctor_id === '' ? null : Number.parseInt(formData.assigned_doctor_id, 10),
        };
        if (hasExactDob && formData.date_of_birth) payload.date_of_birth = formData.date_of_birth;

        try {
            const response = await createPatientMutation.mutateAsync(payload);
            toast.success(t('patients.form.success_msg'));
            onSuccess?.(response?.data);
            onClose();
        } catch (err) {
            toast.error(err.response?.data?.detail || t('patients.form.error_msg'));
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={t('patients.form.add_new')} size="md">
            <form onSubmit={handleSubmit} className="space-y-5">
                <div className="rounded-2xl border border-border bg-surface-hover/40 p-4">
                    <p className="mb-4 text-xs font-bold uppercase tracking-wide text-text-muted">
                        {t('patients.fast_registration', 'Quick registration')}
                    </p>
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <Input
                            label={t('patients.form.name_label')}
                            placeholder={t('patients.form.name_placeholder')}
                            value={formData.name}
                            onChange={(e) => handleInputChange('name', e.target.value)}
                            containerClassName="md:col-span-2"
                            required
                            autoFocus
                            dir="auto"
                        />
                        <Input
                            label={t('patients.form.phone_label')}
                            type="tel"
                            inputMode="tel"
                            placeholder="01xxxxxxxxx"
                            value={formData.phone}
                            onChange={(e) => handleInputChange('phone', e.target.value)}
                            dir="ltr"
                        />
                        <Input
                            label={t('patients.form.age_label')}
                            type="number"
                            inputMode="numeric"
                            min="0"
                            max="120"
                            placeholder="30"
                            value={formData.age}
                            onChange={(e) => handleInputChange('age', e.target.value)}
                        />
                    </div>

                    <label className="mt-4 flex cursor-pointer items-center gap-3 rounded-xl border border-border bg-surface px-3 py-2.5 text-sm font-semibold text-text-secondary">
                        <input
                            type="checkbox"
                            checked={hasExactDob}
                            onChange={(e) => setHasExactDob(e.target.checked)}
                            className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                        />
                        {t('patients.exact_dob_known', 'Exact date of birth is known')}
                    </label>
                    {hasExactDob && (
                        <div className="mt-3">
                            <Input
                                label={t('patients.date_of_birth', 'Date of birth')}
                                type="date"
                                value={formData.date_of_birth}
                                onChange={(e) => handleInputChange('date_of_birth', e.target.value)}
                            />
                            <p className="mt-1 text-xs text-text-muted">
                                {t('patients.dob_hint', 'If only the age is known, leave this off. DENTIX will not invent an exact birthday.')}
                            </p>
                        </div>
                    )}
                </div>

                <details className="rounded-2xl border border-border bg-surface">
                    <summary className="cursor-pointer px-4 py-3 text-sm font-bold text-text-primary">
                        {t('patients.additional_information', 'Additional information')}
                    </summary>
                    <div className="grid grid-cols-1 gap-4 border-t border-border p-4">
                        <div className="space-y-1.5">
                            <label className="block text-sm font-bold text-text-secondary">{t('patients.form.doctor_label')}</label>
                            <select
                                value={formData.assigned_doctor_id || ''}
                                onChange={(e) => handleInputChange('assigned_doctor_id', e.target.value)}
                                className="w-full rounded-xl border border-border bg-input p-2.5 text-text-primary outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                            >
                                <option value="">{t('patients.form.doctor_select')}</option>
                                {(doctorsQuery.data || []).map((doctor) => (
                                    <option key={doctor.id} value={doctor.id}>
                                        {t('common.doctor_prefix', 'د.')} {doctor.full_name || doctor.username}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <Input
                            label={t('patients.form.address_label')}
                            placeholder={t('patients.form.address_placeholder')}
                            value={formData.address}
                            onChange={(e) => handleInputChange('address', e.target.value)}
                            dir="auto"
                        />
                        <div className="space-y-1.5">
                            <label className="block text-sm font-bold text-text-secondary">{t('patients.form.medical_history')}</label>
                            <textarea
                                value={formData.medical_history}
                                onChange={(e) => handleInputChange('medical_history', e.target.value)}
                                placeholder={t('patients.form.other_notes')}
                                className="min-h-24 w-full resize-y rounded-xl border border-border bg-input p-3 text-sm text-text-primary outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                                dir="auto"
                            />
                        </div>
                    </div>
                </details>

                <div className="flex gap-3 pt-1">
                    <Button variant="ghost" type="button" onClick={onClose} className="flex-1" disabled={createPatientMutation.isPending}>
                        {t('patients.form.cancel_btn')}
                    </Button>
                    <Button type="submit" isLoading={createPatientMutation.isPending} className="flex-[2]">
                        {t('patients.form.submit_btn')}
                    </Button>
                </div>
            </form>
        </Modal>
    );
}

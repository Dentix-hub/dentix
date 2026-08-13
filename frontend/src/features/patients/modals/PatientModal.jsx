import React, { useState, useEffect } from 'react';
import logger from '@/utils/logger';
import { useTranslation } from 'react-i18next';
import { getDoctors, createPatient, checkDuplicatePatient, getFieldSuggestions } from '@/api';
import { useAuth } from '@/auth/useAuth';
import { Modal, Button, Input, toast } from '@/shared/ui';
import { AlertTriangle, UserCheck } from 'lucide-react';

export default function PatientModal({ isOpen, onClose, onSuccess }) {
    const { t } = useTranslation();
    const { user } = useAuth();
    
    const [doctors, setDoctors] = useState([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [addressSuggestions, setAddressSuggestions] = useState([]);
    const [dupInfo, setDupInfo] = useState({ exact_match: null, similar_patients: [] });
    const [formData, setFormData] = useState({
        name: '',
        age: '',
        phone: '',
        address: '',
        medical_history: '',
        assigned_doctor_id: ''
    });

    useEffect(() => {
        if (isOpen) {
            getDoctors()
                .then(res => setDoctors(res.data))
                .catch(err => logger.error("Failed to fetch doctors", err));

            getFieldSuggestions('address')
                .then(res => setAddressSuggestions(res.data || []))
                .catch(err => logger.error("Failed to fetch address suggestions", err));
            
            if (user?.role === 'doctor') {
                setFormData(prev => ({ ...prev, assigned_doctor_id: user.id }));
            }
        } else {
            // Reset form on close
            setFormData({
                name: '',
                age: '',
                phone: '',
                address: '',
                medical_history: '',
                assigned_doctor_id: user?.role === 'doctor' ? user.id : ''
            });
            setDupInfo({ exact_match: null, similar_patients: [] });
        }
    }, [isOpen, user]);

    // Check duplicates when name or phone changes
    useEffect(() => {
        if (!formData.name || formData.name.trim().length < 2) {
            setDupInfo({ exact_match: null, similar_patients: [] });
            return;
        }

        const timer = setTimeout(() => {
            checkDuplicatePatient(formData.name.trim(), formData.phone.trim())
                .then(res => {
                    if (res.data) {
                        setDupInfo(res.data);
                    }
                })
                .catch(() => {});
        }, 300);

        return () => clearTimeout(timer);
    }, [formData.name, formData.phone]);

    const handleInputChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!formData.name) return toast.error(t('patients.form.name_required'));
        if (dupInfo.exact_match) {
            return toast.error(t('patients.form.duplicate_error', 'هذا المريض موجود بالفعل برقم ملف #' + dupInfo.exact_match.file_number));
        }

        setIsSubmitting(true);
        
        const cleanedData = {
            ...formData,
            age: formData.age === '' ? null : parseInt(formData.age),
            assigned_doctor_id: formData.assigned_doctor_id === '' ? null : parseInt(formData.assigned_doctor_id)
        };

        try {
            await createPatient(cleanedData);
            toast.success(t('patients.form.success_msg'));
            if (onSuccess) onSuccess();
            onClose();
        } catch (err) {
            toast.error(err.response?.data?.detail || t('patients.form.error_msg'));
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={t('patients.form.add_new')}
            size="md"
        >
            <form onSubmit={handleSubmit} className="space-y-4">
                {/* Duplicate Warning Banners */}
                {dupInfo.exact_match && (
                    <div className="p-3.5 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-start gap-3 text-red-600 dark:text-red-400 text-xs font-bold animate-in fade-in">
                        <AlertTriangle size={18} className="shrink-0 mt-0.5" />
                        <div>
                            <p className="font-black text-sm">مريض مكرر!</p>
                            <p>يوجد مريض آخر بنفس الاسم أو رقم الهاتف: <strong>{dupInfo.exact_match.name}</strong> (رقم الملف #{dupInfo.exact_match.file_number})</p>
                        </div>
                    </div>
                )}

                {!dupInfo.exact_match && dupInfo.similar_patients.length > 0 && (
                    <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex items-start gap-3 text-amber-700 dark:text-amber-400 text-xs font-bold animate-in fade-in">
                        <UserCheck size={18} className="shrink-0 mt-0.5" />
                        <div>
                            <p className="font-bold">مرضى بأسماء مشابهة:</p>
                            <ul className="mt-1 space-y-0.5">
                                {dupInfo.similar_patients.map(p => (
                                    <li key={p.id}>• {p.name} (رقم الملف #{p.file_number})</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                        label={t('patients.form.name_label')}
                        placeholder={t('patients.form.name_placeholder')}
                        value={formData.name}
                        onChange={(e) => handleInputChange('name', e.target.value)}
                        containerClassName="md:col-span-2"
                        required
                    />
                    <Input
                        label={t('patients.form.age_label')}
                        type="number"
                        placeholder="25"
                        value={formData.age}
                        onChange={(e) => handleInputChange('age', e.target.value)}
                    />
                    <Input
                        label={t('patients.form.phone_label')}
                        type="tel"
                        placeholder="01xxxxxxxxx"
                        value={formData.phone}
                        onChange={(e) => handleInputChange('phone', e.target.value)}
                        dir="ltr"
                    />
                    <Input
                        label={t('patients.form.address_label')}
                        placeholder={t('patients.form.address_placeholder')}
                        value={formData.address}
                        onChange={(e) => handleInputChange('address', e.target.value)}
                        suggestions={addressSuggestions}
                        containerClassName="md:col-span-2"
                    />
                    
                    <div className="md:col-span-2 space-y-1.5">
                        <label className="block text-sm font-bold text-text-secondary">
                            {t('patients.form.doctor_label')}
                        </label>
                        <select
                            value={formData.assigned_doctor_id || ''}
                            onChange={(e) => handleInputChange('assigned_doctor_id', e.target.value)}
                            className="w-full rounded-xl border border-border bg-input text-text-primary p-2.5 outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                        >
                            <option value="">{t('patients.form.doctor_select')}</option>
                            {doctors.map(doc => (
                                <option key={doc.id} value={doc.id}>
                                    {t('common.doctor_prefix', 'د.')} {doc.full_name || doc.username}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="md:col-span-2 space-y-3 pt-2">
                        <label className="text-sm font-bold text-text-secondary flex items-center gap-2">
                            {t('patients.form.medical_history')}
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {['none', 'diabetes', 'hypertension', 'heart_disease', 'allergy', 'blood_thinners', 'hepatitis_c', 'thyroid', 'pregnancy', 'smoking'].map(conditionKey => {
                                const condition = t(`patients.medical_conditions.${conditionKey}`);
                                const isSelected = conditionKey === 'none' 
                                    ? formData.medical_history === condition
                                    : (formData.medical_history || '').includes(condition);

                                return (
                                    <button
                                        key={conditionKey}
                                        type="button"
                                        onClick={() => {
                                            let current = formData.medical_history ? formData.medical_history.split(t('common.separator', '، ')) : [];
                                            current = current.map(c => c.trim()).filter(c => c && c !== t('patients.medical_conditions.none'));
                                            
                                            if (conditionKey === 'none') {
                                                setFormData(prev => ({ ...prev, medical_history: t('patients.medical_conditions.none') }));
                                                return;
                                            }
                                            
                                            if (current.includes(condition)) {
                                                current = current.filter(c => c !== condition);
                                            } else {
                                                current.push(condition);
                                            }
                                            const separator = t('common.separator', '، ');
                                            setFormData(prev => ({ ...prev, medical_history: current.length ? current.join(separator) : '' }));
                                        }}
                                        className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${isSelected
                                            ? 'bg-rose-500 text-white border-rose-500'
                                            : 'bg-surface text-text-secondary border-border hover:border-rose-300'
                                            }`}
                                    >
                                        {condition}
                                    </button>
                                );
                            })}
                        </div>
                        <Input
                            placeholder={t('patients.form.other_notes')}
                            value={formData.medical_history}
                            onChange={(e) => handleInputChange('medical_history', e.target.value)}
                        />
                    </div>
                </div>

                <div className="flex gap-4 pt-4">
                    <Button
                        variant="ghost"
                        type="button"
                        onClick={onClose}
                        className="flex-1"
                    >
                        {t('patients.form.cancel_btn')}
                    </Button>
                    <Button
                        type="submit"
                        isLoading={isSubmitting}
                        className="flex-[2]"
                    >
                        {t('patients.form.submit_btn')}
                    </Button>
                </div>
            </form>
        </Modal>
    );
}

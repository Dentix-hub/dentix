import React, { useState, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { createPatient, deletePatient, searchPatients, getDoctors } from '@/api';
import { usePatients } from '@/hooks/usePatients';
import { useAuth } from '@/auth/useAuth';
import PatientScanner from '@/features/patients/PatientScanner';
import PatientTable from '@/features/patients/PatientTable';
import PatientFilters from '@/features/patients/PatientFilters';
import PatientQuickActions from '@/features/patients/PatientQuickActions';
import { Modal, Button, Input, toast } from '@/shared/ui';

export default function Patients() {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const { data: patients = [], isLoading: loading, refetch } = usePatients();
    const { user } = useAuth();

    // State
    const [search, setSearch] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isScannerOpen, setIsScannerOpen] = useState(false);
    const [doctors, setDoctors] = useState([]);
    const [newPatient, setNewPatient] = useState({
        name: '',
        age: '',
        phone: '',
        address: '',
        medical_history: '',
        assigned_doctor_id: ''
    });
    const [suggestions, setSuggestions] = useState([]);
    const [searchTimeoutState, setSearchTimeoutState] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Fetch Doctors when modal opens
    React.useEffect(() => {
        const fetchDoctors = async () => {
            try {
                const res = await getDoctors();
                setDoctors(res.data);
                if (user?.role === 'doctor') {
                    setNewPatient(prev => ({ ...prev, assigned_doctor_id: user.id }));
                }
            } catch (err) {
                console.error("Failed to fetch doctors", err);
            }
        };
        if (isModalOpen) fetchDoctors();
    }, [isModalOpen, user]);

    // Derived Stats
    const stats = useMemo(() => {
        const total = patients.length;
        const newThisMonth = patients.filter(p => {
            if (!p.created_at) return false;
            const date = new Date(p.created_at);
            const now = new Date();
            return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
        }).length;
        const active = Math.floor(total * 0.7);
        return { total, newThisMonth, active };
    }, [patients]);

    // Handlers
    const handleDeletePatient = useCallback(async (id, name) => {
        if (!window.confirm(t('patients.delete_confirm', { name }))) return;
        const toastId = toast.loading(t('common.loading'));
        try {
            await deletePatient(id);
            toast.success(t('patients.delete_success'), { id: toastId });
            refetch();
        } catch (err) {
            toast.error(t('patients.delete_error'), { id: toastId });
        }
    }, [refetch, t]);

    const handleCreatePatient = async (e) => {
        e.preventDefault();
        if (!newPatient.name || !newPatient.phone) {
            toast.error(t('patients.form.name_placeholder') + ' ' + t('common.and') + ' ' + t('patients.form.phone_label'));
            return;
        }
        setIsSubmitting(true);
        const toastId = toast.loading(t('common.loading'));

        try {
            const res = await searchPatients(newPatient.phone);
            const duplicates = res.data;
            const exactMatch = duplicates.find(p => p.phone === newPatient.phone && p.name === newPatient.name);
            if (exactMatch) {
                toast.error(t('patients.form.duplicate_error'), { id: toastId });
                setIsSubmitting(false);
                return;
            }
        } catch (err) {
            console.error("Error checking duplicates", err);
        }

        try {
            await createPatient({
                name: newPatient.name,
                age: parseInt(newPatient.age) || 0,
                phone: newPatient.phone,
                address: newPatient.address || '',
                medical_history: newPatient.medical_history || '',
                assigned_doctor_id: newPatient.assigned_doctor_id || null,
                notes: ''
            });
            toast.success(t('patients.form.submit_btn'), { id: toastId });
            setIsModalOpen(false);
            setNewPatient({
                name: '',
                age: '',
                phone: '',
                address: '',
                medical_history: '',
                assigned_doctor_id: user?.role === 'doctor' ? user.id : ''
            });
            setSuggestions([]);
            setSearch('');
            refetch();
        } catch (err) {
            console.error(err);
            const msg = err.response?.data?.detail || t('patients.delete_error');
            toast.error(msg, { id: toastId });
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleInputChange = (field, value) => {
        setNewPatient(prev => ({ ...prev, [field]: value }));
        if (['name', 'phone'].includes(field)) {
            if (searchTimeoutState) clearTimeout(searchTimeoutState);
            if (!value || value.length < 2) {
                setSuggestions([]);
                return;
            }
            const timeoutId = setTimeout(async () => {
                try {
                    const res = await searchPatients(value);
                    setSuggestions(res.data);
                } catch (err) {
                    console.error(err);
                }
            }, 300);
            setSearchTimeoutState(timeoutId);
        }
    };

    const handleScanComplete = (data) => {
        setNewPatient(prev => ({
            ...prev,
            name: data.name || prev.name,
            age: data.age || prev.age,
            phone: data.phone || prev.phone,
            address: data.address || prev.address
        }));
        toast.success(t('patients.form.scan_success'));
    };

    const filteredPatients = patients.filter(p =>
        p.name.includes(search) || p.phone.includes(search)
    );

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 min-h-screen pb-20">
            {/* Quick Actions (Header + Stats) */}
            <PatientQuickActions
                stats={stats}
                isLoading={loading}
                onAddClick={() => setIsModalOpen(true)}
            />

            {/* Search Filter */}
            <PatientFilters
                search={search}
                onSearchChange={setSearch}
            />

            {/* Patients Table */}
            <PatientTable
                patients={filteredPatients}
                isLoading={loading}
                onDelete={handleDeletePatient}
            />

            {/* Add Patient Modal */}
            <Modal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title={t('patients.add_new')}
                size="lg"
            >
                <form onSubmit={handleCreatePatient} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <Input
                            label={t('patients.form.name_label')}
                            placeholder={t('patients.form.name_placeholder')}
                            value={newPatient.name}
                            onChange={(e) => handleInputChange('name', e.target.value)}
                            containerClassName="md:col-span-2"
                        />
                        <Input
                            label={t('patients.form.age_label')}
                            type="number"
                            placeholder="مثال: 25"
                            value={newPatient.age}
                            onChange={(e) => handleInputChange('age', e.target.value)}
                        />
                        <Input
                            label={t('patients.form.phone_label')}
                            type="tel"
                            placeholder="01xxxxxxxxx"
                            value={newPatient.phone}
                            onChange={(e) => handleInputChange('phone', e.target.value)}
                            dir="ltr"
                            className="text-right"
                        />
                        <Input
                            label={t('patients.form.address_label')}
                            placeholder={t('patients.form.address_placeholder')}
                            value={newPatient.address}
                            onChange={(e) => handleInputChange('address', e.target.value)}
                            containerClassName="md:col-span-2"
                        />
                        {/* Doctor Assignment Dropdown */}
                        <div className="md:col-span-2 space-y-1.5">
                            <label className="block text-sm font-bold text-text-secondary">
                                {t('patients.form.doctor_label')}
                            </label>
                            <select
                                value={newPatient.assigned_doctor_id || ''}
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
                        {/* Medical History */}
                        <div className="md:col-span-2 space-y-3 pt-2 border-t border-border">
                            <label className="text-sm font-black text-text-secondary flex items-center gap-2">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
                                {t('patients.form.medical_history')}
                            </label>
                             <div className="flex flex-wrap gap-2">
                                 {['none', 'diabetes', 'hypertension', 'heart_disease', 'allergy', 'blood_thinners', 'hepatitis_c', 'thyroid', 'pregnancy', 'smoking'].map(conditionKey => {
                                     const condition = t(`patients.medical_conditions.${conditionKey}`);
                                     const isSelected = conditionKey === 'none' 
                                         ? newPatient.medical_history === condition
                                         : (newPatient.medical_history || '').includes(condition);

                                     return (
                                         <button
                                             key={conditionKey}
                                             type="button"
                                             onClick={() => {
                                                 let current = newPatient.medical_history ? newPatient.medical_history.split(t('common.separator', '، ')) : [];
                                                 current = current.map(c => c.trim()).filter(c => c && c !== t('patients.medical_conditions.none'));
                                                 
                                                 if (conditionKey === 'none') {
                                                     setNewPatient(prev => ({ ...prev, medical_history: t('patients.medical_conditions.none') }));
                                                     return;
                                                 }
                                                 
                                                 if (current.includes(condition)) {
                                                     current = current.filter(c => c !== condition);
                                                 } else {
                                                     current.push(condition);
                                                 }
                                                 const separator = t('common.separator', '، ');
                                                 setNewPatient(prev => ({ ...prev, medical_history: current.length ? current.join(separator) : '' }));
                                             }}
                                             className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${isSelected
                                                 ? 'bg-rose-500 text-white border-rose-500 shadow-sm'
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
                                value={newPatient.medical_history}
                                onChange={(e) => handleInputChange('medical_history', e.target.value)}
                            />
                        </div>
                        {/* Duplicate Warning */}
                        {suggestions.length > 0 && (
                            <div className="md:col-span-2 bg-amber-50 dark:bg-amber-900/20 p-4 rounded-2xl border border-amber-200 dark:border-amber-700/50">
                                <h4 className="text-amber-800 dark:text-amber-400 font-bold mb-3 text-sm">
                                    {t('patients.form.duplicate_warning')}
                                </h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-32 overflow-y-auto custom-scrollbar">
                                    {suggestions.map(s => (
                                        <div key={s.id} className="flex justify-between text-sm bg-surface p-2 rounded-lg border border-border">
                                            <span className="font-bold text-text-primary">{s.name}</span>
                                            <span className="text-text-secondary" dir="ltr">{s.phone}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                    <div className="flex gap-4 pt-4">
                        <Button
                            variant="ghost"
                            type="button"
                            onClick={() => setIsModalOpen(false)}
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

            {/* Patient Scanner */}
            {isScannerOpen && (
                <PatientScanner
                    onScanComplete={handleScanComplete}
                    onClose={() => setIsScannerOpen(false)}
                />
            )}
        </div>
    );
}


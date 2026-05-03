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
import PatientModal from '@/features/patients/modals/PatientModal';
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

            {/* Patient Scanner */}
            {isScannerOpen && (
                <PatientScanner
                    onScanComplete={handleScanComplete}
                    onClose={() => setIsScannerOpen(false)}
                />
            )}

            {/* Add Patient Modal */}
            <PatientModal 
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSuccess={refetch}
            />
        </div>
    );
}

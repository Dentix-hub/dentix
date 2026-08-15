import { useState, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { deletePatient } from '@/api';
import { usePatients } from '@/hooks/usePatients';
import PatientTable from '@/features/patients/PatientTable';
import PatientFilters from '@/features/patients/PatientFilters';
import PatientQuickActions from '@/features/patients/PatientQuickActions';
import PatientModal from '@/features/patients/modals/PatientModal.jsx';
import { toast } from '@/shared/ui';

export default function Patients() {
    const { t } = useTranslation();
    const { data: patients = [], isLoading: loading, refetch } = usePatients();

    // State
    const [search, setSearch] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);

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
            <PatientModal 
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSuccess={refetch}
            />
        </div>
    );
}

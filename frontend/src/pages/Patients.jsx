import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from '@/shared/ui';
import {
    useDeletePatient,
    usePatientDirectory,
} from '@/hooks/usePatients';
import PatientTable from '@/features/patients/PatientTable';
import PatientFilters from '@/features/patients/PatientFilters';
import PatientQuickActions from '@/features/patients/PatientQuickActions';
import PatientModal from '@/features/patients/modals/PatientModal.jsx';

export default function Patients() {
    const { t } = useTranslation();
    const [searchParams, setSearchParams] = useSearchParams();
    const initialQuery = searchParams.get('q') || '';
    const [search, setSearch] = useState(initialQuery);
    const [debouncedSearch, setDebouncedSearch] = useState(initialQuery);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const archivePatient = useDeletePatient();

    useEffect(() => {
        const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
        return () => window.clearTimeout(timer);
    }, [search]);

    useEffect(() => {
        const next = new URLSearchParams(searchParams);
        if (search.trim()) next.set('q', search.trim());
        else next.delete('q');
        if (next.toString() !== searchParams.toString()) {
            setSearchParams(next, { replace: true });
        }
    }, [search, searchParams, setSearchParams]);

    const directory = usePatientDirectory({ query: debouncedSearch, limit: 30 });
    const patients = useMemo(
        () => directory.data?.pages.flatMap((page) => page.items) || [],
        [directory.data],
    );

    const handleArchivePatient = useCallback(async (id, name) => {
        if (!window.confirm(t('patients.delete_confirm', { name, defaultValue: `Archive ${name}?` }))) return;
        try {
            await archivePatient.mutateAsync(id);
            toast.success(t('patients.archive_success', 'Patient archived successfully'));
        } catch (err) {
            toast.error(err.response?.data?.detail || t('patients.delete_error'));
        }
    }, [archivePatient, t]);

    return (
        <div className="min-h-screen space-y-5 pb-20 animate-in fade-in duration-300">
            <PatientQuickActions onAddClick={() => setIsModalOpen(true)} />

            <section className="rounded-2xl border border-border bg-surface shadow-sm overflow-hidden">
                <PatientFilters
                    search={search}
                    onSearchChange={setSearch}
                    isFetching={directory.isFetching && !directory.isFetchingNextPage}
                />

                <PatientTable
                    patients={patients}
                    isLoading={directory.isLoading}
                    isError={directory.isError}
                    error={directory.error}
                    searchQuery={debouncedSearch}
                    onRetry={directory.refetch}
                    onArchive={handleArchivePatient}
                    onAdd={() => setIsModalOpen(true)}
                    hasNextPage={directory.hasNextPage}
                    isFetchingNextPage={directory.isFetchingNextPage}
                    onLoadMore={() => directory.fetchNextPage()}
                />
            </section>

            <PatientModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
            />
        </div>
    );
}

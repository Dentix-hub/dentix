import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/auth/useAuth';
import { toast } from '@/shared/ui';
import { useDeletePatient, usePatientDirectory, useRecentPatients } from '@/hooks/usePatients';
import { getRecentPatientIds } from '@/features/patients/recentPatients';
import PatientTable from '@/features/patients/PatientTable';
import PatientFilters from '@/features/patients/PatientFilters';
import PatientQuickFilters from '@/features/patients/PatientQuickFilters';
import PatientQuickActions from '@/features/patients/PatientQuickActions';
import PatientModal from '@/features/patients/modals/PatientModal.jsx';

const VALID_SCOPES = new Set(['all', 'today', 'recent', 'mine']);

export default function Patients() {
    const { t } = useTranslation();
    const { user } = useAuth();
    const [searchParams, setSearchParams] = useSearchParams();
    const initialQuery = searchParams.get('q') || '';
    const requestedScope = searchParams.get('scope') || 'all';
    const initialScope = VALID_SCOPES.has(requestedScope) ? requestedScope : 'all';
    const [search, setSearch] = useState(initialQuery);
    const [debouncedSearch, setDebouncedSearch] = useState(initialQuery);
    const [scope, setScope] = useState(initialScope);
    const [recentIds, setRecentIds] = useState(() => getRecentPatientIds());
    const [isModalOpen, setIsModalOpen] = useState(false);
    const archivePatient = useDeletePatient();
    const isDoctor = user?.role === 'doctor';

    useEffect(() => {
        if (scope === 'mine' && !isDoctor) setScope('all');
    }, [scope, isDoctor]);

    useEffect(() => {
        const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
        return () => window.clearTimeout(timer);
    }, [search]);

    useEffect(() => {
        if (scope === 'recent') setRecentIds(getRecentPatientIds());
    }, [scope]);

    useEffect(() => {
        const next = new URLSearchParams(searchParams);
        if (search.trim()) next.set('q', search.trim());
        else next.delete('q');
        if (scope !== 'all') next.set('scope', scope);
        else next.delete('scope');
        if (next.toString() !== searchParams.toString()) {
            setSearchParams(next, { replace: true });
        }
    }, [search, scope, searchParams, setSearchParams]);

    useEffect(() => {
        // Command palette emits /patients?action=new to open the add form.
        if (searchParams.get('action') === 'new') {
            setIsModalOpen(true);
            const next = new URLSearchParams(searchParams);
            next.delete('action');
            setSearchParams(next, { replace: true });
        }
    }, [searchParams, setSearchParams]);

    const directory = usePatientDirectory({
        query: debouncedSearch,
        limit: 30,
        scope: scope === 'recent' ? 'all' : scope,
        enabled: scope !== 'recent',
    });
    const recent = useRecentPatients(recentIds, debouncedSearch, {
        enabled: scope === 'recent' && recentIds.length > 0,
    });

    const patients = useMemo(() => {
        if (scope === 'recent') return recent.data || [];
        return directory.data?.pages.flatMap((page) => page.items) || [];
    }, [scope, recent.data, directory.data]);

    const activeIsLoading = scope === 'recent' ? recent.isLoading : directory.isLoading;
    const activeIsFetching = scope === 'recent' ? recent.isFetching : directory.isFetching;
    const activeIsError = scope === 'recent' ? recent.isError : directory.isError;
    const activeRefetch = scope === 'recent' ? recent.refetch : directory.refetch;

    const handleArchivePatient = useCallback(async (id, name) => {
        if (!window.confirm(t('patients.archive_confirm', { name }))) return;
        try {
            await archivePatient.mutateAsync(id);
            toast.success(t('patients.archive_success'));
            if (scope === 'recent') setRecentIds(getRecentPatientIds().filter((patientId) => patientId !== id));
        } catch (err) {
            toast.error(err.response?.data?.detail || t('patients.archive_error'));
        }
    }, [archivePatient, scope, t]);

    return (
        <div className="min-h-screen space-y-5 pb-20 animate-in fade-in duration-300">
            <PatientQuickActions onAddClick={() => setIsModalOpen(true)} />

            <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
                <PatientFilters
                    search={search}
                    onSearchChange={setSearch}
                    isFetching={activeIsFetching && !directory.isFetchingNextPage}
                />
                <PatientQuickFilters
                    scope={scope}
                    onScopeChange={setScope}
                    isDoctor={isDoctor}
                />

                <PatientTable
                    patients={patients}
                    isLoading={activeIsLoading}
                    isError={activeIsError}
                    searchQuery={debouncedSearch}
                    scope={scope}
                    onRetry={activeRefetch}
                    onArchive={handleArchivePatient}
                    onAdd={() => setIsModalOpen(true)}
                    hasNextPage={scope !== 'recent' && directory.hasNextPage}
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

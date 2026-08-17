import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getDoctorRevenue, getMyDoctorRevenue, updateDoctorCompensation } from '@/api/financials';
import { financeKeys } from '../../queryKeys';
import { getPresetDates } from '../../utils/datePresets';
import { useFinancePermissions } from '../../useFinancePermissions';

/**
 * Hook for managing Doctor Compensation V2 list, calculations, and rules.
 */
export function useDoctorCompensation() {
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();
    const { isDoctor, user } = useFinancePermissions();

    // Default to 'this_month' if dates not provided
    const defaultDates = getPresetDates('this_month');
    const from = searchParams.get('from') || defaultDates.from;
    const to = searchParams.get('to') || defaultDates.to;
    const search = searchParams.get('q') || '';

    // 1. Fetch Doctor Revenue List
    const doctorsQuery = useQuery({
        queryKey: financeKeys.doctorRevenue(from, to, isDoctor ? `self-${user?.id}` : 'all'),
        queryFn: async () => {
            const res = await (isDoctor ? getMyDoctorRevenue(from, to) : getDoctorRevenue(from, to));
            const data = res.data?.data?.doctors || res.data?.doctors || res.data || [];
            return Array.isArray(data) ? data : [];
        },
        enabled: Boolean(from && to),
        staleTime: 30 * 1000,
    });

    const doctors = doctorsQuery.data || [];

    // Filter by doctor name search query
    const filteredDoctors = doctors.filter((doc) => {
        if (!search.trim()) return true;
        return (doc.doctor_name || '').toLowerCase().includes(search.trim().toLowerCase());
    });

    // Clinic-wide aggregates
    const totalDoctorDues = doctors.reduce((sum, doc) => sum + (Number(doc.total_due) || 0), 0);
    const totalDoctorRevenue = doctors.reduce((sum, doc) => sum + (Number(doc.revenue) || 0), 0);
    const totalDoctorCollected = doctors.reduce((sum, doc) => sum + (Number(doc.collected) || 0), 0);

    const updateDateRange = ({ from: newFrom, to: newTo }) => {
        const params = new URLSearchParams(searchParams);
        if (newFrom) params.set('from', newFrom);
        else params.delete('from');
        if (newTo) params.set('to', newTo);
        else params.delete('to');
        setSearchParams(params);
    };

    const updateSearch = (newSearch) => {
        const params = new URLSearchParams(searchParams);
        if (newSearch) params.set('q', newSearch);
        else params.delete('q');
        setSearchParams(params);
    };

    // Update Compensation Rules Mutation
    const updateMutation = useMutation({
        mutationFn: ({ doctorId, data }) => updateDoctorCompensation(doctorId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: financeKeys.doctorRevenue() });
            queryClient.invalidateQueries({ queryKey: financeKeys.overview() });
        },
    });

    return {
        doctors: filteredDoctors,
        totalDoctorDues,
        totalDoctorRevenue,
        totalDoctorCollected,
        from,
        to,
        search,
        isLoading: doctorsQuery.isLoading,
        isError: doctorsQuery.isError,
        refetch: doctorsQuery.refetch,
        updateDateRange,
        updateSearch,
        updateCompensation: updateMutation.mutateAsync,
        isUpdating: updateMutation.isPending,
    };
}

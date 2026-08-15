import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getDoctorDetails, getMyDoctorDetails, updateDoctorCompensation } from '@/api/financials';
import { financeKeys } from '../../queryKeys';
import { getPresetDates } from '../../utils/datePresets';
import { useFinancePermissions } from '../../useFinancePermissions';

/**
 * Hook for managing single doctor detailed financial breakdown and case drill-down.
 */
export function useDoctorDetails(doctorId) {
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();
    const { isDoctor, user } = useFinancePermissions();
    const effectiveDoctorId = isDoctor ? user?.id : doctorId;

    const defaultDates = getPresetDates('this_month');
    const from = searchParams.get('from') || defaultDates.from;
    const to = searchParams.get('to') || defaultDates.to;

    const detailsQuery = useQuery({
        queryKey: financeKeys.doctorDetails(effectiveDoctorId, from, to),
        queryFn: async () => {
            if (!doctorId) return null;
            const res = await (isDoctor
                ? getMyDoctorDetails(from, to)
                : getDoctorDetails(doctorId, from, to));
            return res.data?.data || res.data || null;
        },
        enabled: Boolean(effectiveDoctorId && from && to),
        staleTime: 30 * 1000,
    });

    const updateDateRange = ({ from: newFrom, to: newTo }) => {
        const params = new URLSearchParams(searchParams);
        if (newFrom) params.set('from', newFrom);
        else params.delete('from');
        if (newTo) params.set('to', newTo);
        else params.delete('to');
        setSearchParams(params);
    };

    const updateMutation = useMutation({
        mutationFn: (data) => updateDoctorCompensation(doctorId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: financeKeys.doctorDetails(doctorId) });
            queryClient.invalidateQueries({ queryKey: financeKeys.doctorRevenue() });
            queryClient.invalidateQueries({ queryKey: financeKeys.overview() });
        },
    });

    return {
        data: detailsQuery.data,
        from,
        to,
        isLoading: detailsQuery.isLoading,
        isError: detailsQuery.isError,
        refetch: detailsQuery.refetch,
        updateDateRange,
        updateCompensation: updateMutation.mutateAsync,
        isUpdating: updateMutation.isPending,
    };
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getPayments, createPayment, deletePayment } from '@/api/billing';
import { financeKeys } from '../../queryKeys';

const positiveIntParam = (value) => {
    if (!value) return null;
    const parsed = Number.parseInt(value, 10);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
};

/**
 * Payments V2 query state is URL-owned so filters/deep links survive refresh
 * and browser navigation. Server filtering remains authoritative.
 */
export function usePayments(pageSize = 20) {
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();

    const search = searchParams.get('q') || '';
    const from = searchParams.get('from') || '';
    const to = searchParams.get('to') || '';
    const patientId = positiveIntParam(searchParams.get('patient_id'));
    const fileNumber = positiveIntParam(searchParams.get('file_number'));
    const paymentId = positiveIntParam(searchParams.get('payment_id'));
    const doctorId = positiveIntParam(searchParams.get('doctor_id'));
    const pageParam = Number.parseInt(searchParams.get('page') || '1', 10);
    const currentPage = Number.isNaN(pageParam) || pageParam < 1 ? 1 : pageParam;

    const skip = (currentPage - 1) * pageSize;
    const queryFilters = {
        search,
        from,
        to,
        patientId,
        fileNumber,
        paymentId,
        doctorId,
        skip,
        limit: pageSize,
    };

    const paymentsQuery = useQuery({
        queryKey: financeKeys.payments(queryFilters),
        queryFn: async () => {
            const params = {
                skip,
                limit: pageSize + 1,
            };
            if (search.trim()) params.search = search.trim();
            if (from) params.start_date = from;
            if (to) params.end_date = to;
            if (patientId) params.patient_id = patientId;
            if (fileNumber) params.file_number = fileNumber;
            if (paymentId) params.payment_id = paymentId;
            if (doctorId) params.doctor_id = doctorId;

            const res = await getPayments(params);
            return Array.isArray(res.data?.data)
                ? res.data.data
                : Array.isArray(res.data)
                ? res.data
                : [];
        },
        staleTime: 30 * 1000,
    });

    const rawData = paymentsQuery.data || [];
    const hasNextPage = rawData.length > pageSize;
    const items = hasNextPage ? rawData.slice(0, pageSize) : rawData;

    const updateParams = (updater, { resetPage = true, replace = false } = {}) => {
        const params = new URLSearchParams(searchParams);
        updater(params);
        if (resetPage) params.delete('page');
        setSearchParams(params, { replace });
    };

    const updateSearch = (newSearch) => {
        updateParams((params) => {
            if (newSearch) params.set('q', newSearch);
            else params.delete('q');
        });
    };

    const updateDateRange = (newFrom, newTo) => {
        updateParams((params) => {
            if (newFrom) params.set('from', newFrom);
            else params.delete('from');
            if (newTo) params.set('to', newTo);
            else params.delete('to');
        });
    };

    const setPage = (newPage) => {
        updateParams(
            (params) => {
                if (newPage > 1) params.set('page', String(newPage));
                else params.delete('page');
            },
            { resetPage: false },
        );
    };

    const clearPaymentSelection = () => {
        updateParams(
            (params) => params.delete('payment_id'),
            { resetPage: false, replace: true },
        );
    };

    const clearIdentifierFilters = () => {
        updateParams((params) => {
            params.delete('patient_id');
            params.delete('file_number');
            params.delete('payment_id');
            params.delete('doctor_id');
        });
    };

    const invalidatePaymentTruth = () => {
        queryClient.invalidateQueries({ queryKey: financeKeys.paymentsRoot() });
        queryClient.invalidateQueries({ queryKey: financeKeys.receivablesRoot() });
        queryClient.invalidateQueries({ queryKey: financeKeys.summaryRoot() });
        queryClient.invalidateQueries({ queryKey: financeKeys.activityRoot() });
    };

    const createMutation = useMutation({
        mutationFn: (data) => createPayment(data),
        onSuccess: invalidatePaymentTruth,
    });

    const deleteMutation = useMutation({
        mutationFn: (id) => deletePayment(id),
        onSuccess: invalidatePaymentTruth,
    });

    return {
        items,
        search,
        from,
        to,
        patientId,
        fileNumber,
        paymentId,
        doctorId,
        currentPage,
        pageSize,
        hasNextPage,
        hasPrevPage: currentPage > 1,
        hasIdentifierFilters: Boolean(patientId || fileNumber || paymentId || doctorId),
        isLoading: paymentsQuery.isLoading,
        isError: paymentsQuery.isError,
        refetch: paymentsQuery.refetch,
        updateSearch,
        updateDateRange,
        setPage,
        clearPaymentSelection,
        clearIdentifierFilters,
        createPayment: createMutation.mutateAsync,
        isCreating: createMutation.isPending,
        deletePayment: deleteMutation.mutateAsync,
        isDeleting: deleteMutation.isPending,
    };
}

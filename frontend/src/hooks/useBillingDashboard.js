import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getComprehensiveStats } from '@/api';

export function useBillingDashboard() {
    const today = new Date();
    const oneMonthAgo = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate()).toISOString().split('T')[0];
    const currentDay = today.toISOString().split('T')[0];

    const [startDate, setStartDate] = useState(oneMonthAgo);
    const [endDate, setEndDate] = useState(currentDay);
    const [selectedPatientId, setSelectedPatientId] = useState('');

    const { data: comprehensiveStats, isLoading, refetch } = useQuery({
        queryKey: ['billing_dashboard_stats', startDate, endDate, selectedPatientId],
        queryFn: async () => {
            const res = await getComprehensiveStats(startDate, endDate, selectedPatientId);
            return res.data;
        }
    });

    return {
        startDate,
        setStartDate,
        endDate,
        setEndDate,
        selectedPatientId,
        setSelectedPatientId,
        comprehensiveStats,
        isLoading,
        refetch
    };
}

export default useBillingDashboard;

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api';

export const SYSTEM_HEALTH_QUERY_KEY = ['admin', 'health', 'alerts'];

export const fetchSystemHealth = async () => {
    const res = await api.get('/api/v1/admin/health/alerts');
    const data = res.data?.data || res.data;
    const score = typeof data?.score === 'number' ? data.score : (data?.score !== undefined ? Number(data.score) : 0);
    return {
        ...data,
        score,
        alerts: Array.isArray(data?.alerts) ? data.alerts : [],
        status: data?.status || (score >= 90 ? 'healthy' : (score >= 70 ? 'warning' : (score > 0 ? 'critical' : 'unknown'))),
    };
};

export function useSystemHealth(options = {}) {
    return useQuery({
        queryKey: SYSTEM_HEALTH_QUERY_KEY,
        queryFn: fetchSystemHealth,
        refetchInterval: 30000,
        refetchIntervalInBackground: false,
        staleTime: 15000,
        ...options,
    });
}

export function useInvalidateSystemHealth() {
    const queryClient = useQueryClient();
    return () => queryClient.invalidateQueries({ queryKey: SYSTEM_HEALTH_QUERY_KEY });
}

export const HEALTH_STATUS_CLASS_MAP = {
    healthy: {
        bgLight: 'bg-emerald-50 dark:bg-emerald-950/20',
        text: 'text-emerald-600 dark:text-emerald-400',
        dot: 'bg-emerald-500',
        glow: 'bg-emerald-500/5 group-hover:bg-emerald-500/10',
    },
    warning: {
        bgLight: 'bg-amber-50 dark:bg-amber-950/20',
        text: 'text-amber-600 dark:text-amber-400',
        dot: 'bg-amber-500',
        glow: 'bg-amber-500/5 group-hover:bg-amber-500/10',
    },
    critical: {
        bgLight: 'bg-rose-50 dark:bg-rose-950/20',
        text: 'text-rose-600 dark:text-rose-400',
        dot: 'bg-rose-500',
        glow: 'bg-rose-500/5 group-hover:bg-rose-500/10',
    },
    unknown: {
        bgLight: 'bg-slate-50 dark:bg-slate-800',
        text: 'text-slate-600 dark:text-slate-400',
        dot: 'bg-slate-400',
        glow: 'bg-slate-500/5 group-hover:bg-slate-500/10',
    },
};

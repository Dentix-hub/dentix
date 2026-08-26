import { useEffect, useState, useCallback } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import DashboardStats from '@/features/admin/SuperAdmin/DashboardStats';
import SystemHealth from '@/features/admin/SuperAdmin/SystemHealth';
import ActivityFeed from '@/features/admin/SuperAdmin/ActivityFeed';
import AdminCharts from '@/features/admin/SuperAdmin/AdminCharts';
import { ShieldCheck, Activity, AlertCircle, RefreshCw } from 'lucide-react';
import { SkeletonStatCard } from '@/shared/ui/Skeleton';
import { useTranslation } from 'react-i18next';

export default function Overview() {
    const { t } = useTranslation();
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchStats = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await api.get('/api/v1/admin/stats');
            setStats(res.data?.data || res.data);
        } catch (err) {
            logger.error('Failed to fetch admin stats', err);
            setError(err);
            setStats(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchStats();
    }, [fetchStats]);

    if (loading) {
        return (
            <div className="space-y-6 animate-pulse">
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center gap-4">
                    <SkeletonStatCard />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl h-80" />
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl h-80" />
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500 pb-12">
            {/* Header section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex items-center gap-4 bg-white dark:bg-slate-900 p-6 pe-8 ps-8 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                    <div className="bg-gradient-to-br from-indigo-500 to-teal-600 p-3.5 rounded-2xl shadow-lg shadow-indigo-500/20 text-white shrink-0">
                        <ShieldCheck size={28} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white">
                            {t('super_admin.overview.title', 'مركز القيادة')}
                        </h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium mt-0.5 text-sm">
                            {t('super_admin.overview.subtitle', 'إدارة وتحليلات النظام المركزية')}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-4 py-2.5 rounded-2xl border border-slate-200 dark:border-slate-700">
                    <Activity size={18} className="text-indigo-500" />
                    <span className="font-bold text-sm">
                        {t('super_admin.overview.platform_admin', 'لوحة الإدارة المركزية')}
                    </span>
                </div>
            </div>

            {/* Error Banner when stats request fails */}
            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-2xl flex items-center justify-between">
                    <div className="flex items-center gap-3 text-red-700 dark:text-red-300">
                        <AlertCircle size={20} />
                        <span className="font-medium text-sm">
                            {t('super_admin.overview.stats_error', 'تعذر تحميل إحصائيات مركز القيادة')}
                        </span>
                    </div>
                    <button
                        type="button"
                        onClick={fetchStats}
                        className="flex items-center gap-1.5 px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-bold rounded-xl transition cursor-pointer"
                    >
                        <RefreshCw size={14} />
                        {t('common.retry', 'إعادة المحاولة')}
                    </button>
                </div>
            )}

            {/* 1. Main Stats KPIs (4 metrics) */}
            {stats && <DashboardStats stats={stats} />}
            
            {/* 2. Primary Analytics & Activity Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Visualizations & Analytics */}
                <div className="xl:col-span-2 space-y-8">
                    {stats && <AdminCharts stats={stats} />}
                </div>

                {/* Activity Feed */}
                <div className="xl:col-span-1 space-y-8">
                    {stats && <ActivityFeed activities={stats.activity_feed} />}
                </div>
            </div>

            {/* 3. System Health & Infrastructure Monitoring */}
            <div>
                <SystemHealth />
            </div>
        </div>
    );
}

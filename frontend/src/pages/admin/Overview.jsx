import { useEffect, useState } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import DashboardStats from '@/features/admin/SuperAdmin/DashboardStats';
import SystemHealth from '@/features/admin/SuperAdmin/SystemHealth';
import ActivityFeed from '@/features/admin/SuperAdmin/ActivityFeed';
import AdminCharts from '@/features/admin/SuperAdmin/AdminCharts';
import { ShieldCheck, Zap } from 'lucide-react';
import { SkeletonStatCard } from '@/shared/ui/Skeleton';

export default function Overview() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await api.get('/api/v1/admin/stats');
                setStats(res.data);
            } catch (err) {
                logger.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchStats();
    }, []);

    if (loading) {
        return (
            <div className="space-y-6">
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
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl h-80 animate-pulse" />
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl h-80 animate-pulse" />
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-fade-in-up pb-12">
            {/* Header section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex items-center gap-4 bg-white dark:bg-slate-900 p-6 pe-8 ps-8 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                    <div className="bg-gradient-to-br from-indigo-500 to-teal-600 p-4 rounded-2xl shadow-lg shadow-indigo-500/20 text-white">
                        <ShieldCheck size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white">مركز القيادة</h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">إدارة وتحليلات النظام المركزية</p>
                    </div>
                </div>

                <div className="flex items-center gap-2 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 px-4 py-2 rounded-2xl border border-indigo-100 dark:border-indigo-900/30">
                    <Zap size={18} fill="currentColor" />
                    <span className="font-bold text-sm">النظام يعمل بكفاءة عالية</span>
                </div>
            </div>

            {/* Main Stats KPIs */}
            {stats && <DashboardStats stats={stats} />}
            
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Visualizations Column */}
                <div className="xl:col-span-2 space-y-8">
                    {stats && <AdminCharts stats={stats} />}
                    <SystemHealth />
                </div>

                {/* Sidebar Column */}
                <div className="space-y-8">
                    {stats && <ActivityFeed activities={stats.activity_feed} />}
                    
                    <div className="bg-gradient-to-br from-slate-800 to-slate-900 p-6 rounded-3xl text-white shadow-xl">
                        <h4 className="text-lg font-bold mb-2">تحديثات AI القادمة</h4>
                        <p className="text-slate-400 text-sm leading-relaxed mb-4">
                            نقوم حالياً بتدريب نماذج التنبؤ بالنمو لتزويدك بتقارير استباقية حول أداء العيادات.
                        </p>
                        <div className="flex items-center gap-2 text-teal-400 font-bold text-xs">
                            <div className="w-2 h-2 bg-teal-400 rounded-full animate-ping" />
                            جاري التطوير...
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}


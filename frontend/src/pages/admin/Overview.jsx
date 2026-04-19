import { useEffect, useState } from 'react';
import { api } from '@/api';
import DashboardStats from '@/features/admin/SuperAdmin/DashboardStats';
import { ShieldCheck } from 'lucide-react';
export default function Overview() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await api.get('/api/v1/admin/stats');
                setStats(res.data);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchStats();
    }, []);
    if (loading) return <div className="p-8 text-center text-slate-500">جاري تحميل الإحصائيات...</div>;
    return (
        <div className="space-y-6 animate-fade-in-up">
            <div className="flex items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="bg-gradient-to-br from-indigo-500 to-teal-600 p-4 rounded-2xl shadow-lg shadow-indigo-500/20 text-white">
                    <ShieldCheck size={32} />
                </div>
                <div>
                    <h1 className="text-2xl font-black text-slate-800 dark:text-white">لوحة التحكم</h1>
                    <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">نظرة عامة على أداء النظام</p>
                </div>
            </div>
            {stats && <DashboardStats stats={stats} />}
            {/* AI Analytics Section */}
            <div className="pt-6 border-t border-slate-200 dark:border-slate-800">
                <h2 className="text-xl font-bold mb-4 text-slate-700 dark:text-slate-300">تحليلات الذكاء الاصطناعي</h2>
            </div>
        </div>
    );
}


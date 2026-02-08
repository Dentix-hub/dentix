import React from 'react';
import { Building2, TrendingUp, AlertCircle, DollarSign, Users, Activity } from 'lucide-react';
import StatCard from '@/shared/ui/StatCard';

const DashboardStats = ({ stats }) => {
    if (!stats) return null;

    return (
        <div className="space-y-8 animate-fade-in">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard icon={Building2} title="إجمالي العيادات" value={stats.total_tenants} subtext="المسجلة في النظام" color="indigo" />
                <StatCard icon={TrendingUp} title="اشتراكات نشطة" value={stats.active_tenants} subtext="تعمل حالياً" color="emerald" />
                <StatCard icon={AlertCircle} title="اشتراكات منتهية" value={stats.expired_tenants} subtext="تحتاج تجديد" color="rose" />
                <StatCard icon={DollarSign} title="الإيرادات الكلية" value={`${(stats.total_revenue || 0).toLocaleString()} ج.م`} subtext="منذ البداية" color="violet" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm">
                    <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                        <Users className="text-indigo-500" />
                        توزيع الخطط
                    </h3>
                    <div className="space-y-4">
                        {Object.entries(stats.plan_distribution || {}).map(([plan, count]) => (
                            <div key={plan} className="flex justify-between items-center p-4 bg-slate-50 dark:bg-slate-800/50 rounded-2xl">
                                <span className="font-bold text-slate-700 dark:text-slate-200">{plan}</span>
                                <div className="flex items-center gap-2">
                                    <span className="text-2xl font-black text-indigo-600 dark:text-indigo-400">{count}</span>
                                    <span className="text-xs text-slate-400">عيادة</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm">
                    <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                        <Activity className="text-emerald-500" />
                        أحدث النشاطات
                    </h3>
                    <div className="text-center text-slate-400 py-10 bg-slate-50 dark:bg-slate-800/50 rounded-2xl border-2 border-dashed border-slate-200 dark:border-slate-700">
                        قريباً: رسوم بيانية تفاعلية 📈
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DashboardStats;

import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { Brain, DollarSign, Activity, Zap, TrendingUp } from 'lucide-react';
import { getAIStats } from '@/api';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export default function AIStats() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await getAIStats();
                setStats(res.data);
            } catch (err) {
                console.error("Failed to load AI stats", err);
            } finally {
                setLoading(false);
            }
        };
        fetchStats();
    }, []);

    if (loading) return (
        <div className="flex h-[50vh] items-center justify-center">
            <div className="flex flex-col items-center gap-4">
                <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin"></div>
                <p className="text-slate-400 font-medium">جاري تحليل البيانات...</p>
            </div>
        </div>
    );

    if (!stats) return <div className="p-8 text-center text-red-500">فشل تحميل الإحصائيات</div>;

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 pb-20" dir="rtl">

            {/* Header Section */}
            <div className="relative overflow-hidden bg-gradient-to-r from-indigo-600 to-violet-600 rounded-3xl p-8 text-white shadow-xl shadow-indigo-500/20">
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-16 -mt-16 blur-3xl"></div>
                <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/10 rounded-full -ml-8 -mb-8 blur-2xl"></div>

                <div className="relative z-10">
                    <h1 className="text-3xl font-black mb-2 flex items-center gap-3">
                        <Brain className="w-8 h-8 text-indigo-100" />
                        مركز قيادة الذكاء الاصطناعي
                    </h1>
                    <p className="text-indigo-100/90 text-lg max-w-2xl">
                        متابعة حية لأداء المساعد الذكي، تحليل التكلفة، ونشاط المستخدمين.
                    </p>
                </div>
            </div>

            {/* Key Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    title="إجمالي الطلبات"
                    value={stats.total_requests}
                    icon={Activity}
                    color="indigo"
                    trend="+12%"
                />
                <MetricCard
                    title="التكلفة التقديرية"
                    value={`$${stats.estimated_cost}`}
                    icon={DollarSign}
                    color="emerald"
                    subtext="Llama 3 70B (Free Tier)"
                />
                <MetricCard
                    title="الأدوات النشطة"
                    value={stats.tool_usage.length}
                    icon={Zap}
                    color="amber"
                />
                <MetricCard
                    title="المستخدمين المتفاعلين"
                    value={stats.top_users.length}
                    icon={TrendingUp}
                    color="rose"
                />
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                {/* Tool Usage Chart */}
                <div className="bg-white dark:bg-slate-800 p-8 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-700 flex flex-col">
                    <div className="mb-8">
                        <h3 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                            <span className="w-2 h-8 bg-indigo-500 rounded-full"></span>
                            أكثر الأدوات استخداماً
                        </h3>
                        <p className="text-slate-400 text-sm mt-1 mr-4">توزيع استخدام أدوات النظام المختلفة</p>
                    </div>

                    <div className="h-[400px] w-full" dir="ltr">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={stats.tool_usage} layout="vertical" margin={{ left: 20, right: 30, top: 10, bottom: 10 }}>
                                <XAxis type="number" hide />
                                <YAxis
                                    dataKey="name"
                                    type="category"
                                    width={180}
                                    tick={{ fontSize: 13, fill: '#64748b', fontWeight: 500 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <Tooltip
                                    cursor={{ fill: '#f1f5f9', opacity: 0.4 }}
                                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
                                />
                                <Bar
                                    dataKey="value"
                                    fill="#6366f1"
                                    radius={[0, 6, 6, 0]}
                                    barSize={24}
                                    background={{ fill: '#f8fafc', radius: [0, 6, 6, 0] }}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Users Activity Chart */}
                <div className="bg-white dark:bg-slate-800 p-8 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-700 flex flex-col">
                    <div className="mb-8">
                        <h3 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                            <span className="w-2 h-8 bg-emerald-500 rounded-full"></span>
                            نشاط المستخدمين
                        </h3>
                        <p className="text-slate-400 text-sm mt-1 mr-4">نسبة تفاعل كل مستخدم مع النظام</p>
                    </div>

                    <div className="h-[400px] w-full relative">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                                <Pie
                                    data={stats.top_users}
                                    cx="50%"
                                    cy="45%"
                                    innerRadius={80}
                                    outerRadius={120}
                                    paddingAngle={5}
                                    dataKey="count"
                                    stroke="none"
                                >
                                    {stats.top_users.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
                                />
                                <Legend
                                    verticalAlign="bottom"
                                    height={36}
                                    iconType="circle"
                                    formatter={(value) => <span className="text-slate-600 dark:text-slate-300 font-medium ml-2">{value}</span>}
                                />
                            </PieChart>
                        </ResponsiveContainer>

                        {/* Center Text */}
                        <div className="absolute top-[45%] left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center pointer-events-none">
                            <p className="text-3xl font-black text-slate-800 dark:text-white">{stats.total_requests}</p>
                            <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Total</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function MetricCard({ title, value, icon: Icon, color, subtext, trend }) {
    // Map color names to tailwind classes for dynamic usage
    const colorMap = {
        indigo: 'bg-indigo-50 text-indigo-600 ring-indigo-100',
        emerald: 'bg-emerald-50 text-emerald-600 ring-emerald-100',
        amber: 'bg-amber-50 text-amber-600 ring-amber-100',
        rose: 'bg-rose-50 text-rose-600 ring-rose-100',
        blue: 'bg-blue-50 text-blue-600 ring-blue-100',
    };

    const styleClass = colorMap[color] || colorMap.indigo;

    return (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl shadow-[0_2px_20px_-4px_rgba(0,0,0,0.05)] border border-slate-100 dark:border-slate-700 hover:translate-y-[-4px] transition-all duration-300">
            <div className="flex justify-between items-start mb-4">
                <div className={`p-3.5 rounded-2xl ${styleClass} ring-4 ring-opacity-50`}>
                    <Icon size={24} strokeWidth={2.5} />
                </div>
                {trend && (
                    <span className="bg-emerald-100 text-emerald-700 text-xs font-bold px-2 py-1 rounded-full flex items-center">
                        {trend} ↗
                    </span>
                )}
            </div>

            <h3 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight mb-1">{value}</h3>
            <p className="text-slate-500 font-medium text-sm">{title}</p>
            {subtext && <p className="text-xs text-slate-400 mt-3 pt-3 border-t border-slate-50 dark:border-slate-700 border-dashed">{subtext}</p>}
        </div>
    );
}

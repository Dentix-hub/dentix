import { useState, useEffect } from 'react';
import logger from '@/utils/logger';
import {
    Cpu,
    Activity,
    DollarSign,
    Users,
    ShieldCheck,
    BarChart3,
    Clock,
    AlertCircle,
    Terminal,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { api } from '@/api';
import {
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    BarChart,
    Bar,
    AreaChart,
    Area,
    LazyChart
} from '@/components/charts/LazyChart';

export default function AIAdminDashboard() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [stats, setStats] = useState(null);
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [period, setPeriod] = useState('month');

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const [statsRes, logsRes] = await Promise.all([
                    api.get(`/api/v1/ai/admin/stats?period=${period}`),
                    api.get(`/api/v1/ai/admin/logs?limit=10`)
                ]);
                setStats(statsRes.data?.data || statsRes.data);
                const logsData = logsRes.data?.data || logsRes.data;
                setLogs(Array.isArray(logsData) ? logsData : []);
            } catch (error) {
                logger.error("AI Analytics error:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [period]);

    if (loading && !stats) return <LoadingPulse />;

    const successRateFormatted = stats?.success_rate !== null && stats?.success_rate !== undefined
        ? `${stats.success_rate}%`
        : '—';

    const costFormatted = stats?.estimated_cost !== null && stats?.estimated_cost !== undefined
        ? `$${Number(stats.estimated_cost).toFixed(4)}`
        : '$0.0000';

    return (
        <div className="space-y-8 animate-in fade-in duration-500" dir={isRtl ? 'rtl' : 'ltr'}>
            {/* Header */}
            <div className="relative p-8 rounded-[2.5rem] bg-indigo-600 overflow-hidden shadow-xl shadow-indigo-500/20">
                <div className="absolute top-0 end-0 w-96 h-96 bg-indigo-400 rounded-full blur-[100px] opacity-20 -me-20 -mt-20 pointer-events-none" />
                <div className="absolute bottom-0 start-0 w-64 h-64 bg-indigo-900 rounded-full blur-[80px] opacity-30 -ms-20 -mb-20 pointer-events-none" />
                
                <div className="relative flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                    <div className="text-start">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-white/20 backdrop-blur-md rounded-xl">
                                <Cpu className="text-white" size={24} />
                            </div>
                            <span className="text-indigo-100 font-bold uppercase tracking-widest text-xs">
                                {t('super_admin.ai.command_center') || 'مركز إدارة الذكاء الاصطناعي'}
                            </span>
                        </div>
                        <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
                            {t('super_admin.ai.title') || 'تحليلات واستهلاك الذكاء الاصطناعي'}
                        </h1>
                        <p className="text-indigo-100/80 mt-2 font-medium max-w-xl text-sm">
                            {t('super_admin.ai.subtitle') || 'مراقبة دقيقة للأداء والتكاليف ومعدلات النجاح لخدمات الذكاء الاصطناعي'}
                        </p>
                    </div>

                    <div className="flex bg-white/10 backdrop-blur-md p-1.5 rounded-2xl border border-white/10 shrink-0">
                        {[
                            { id: 'today', label: t('super_admin.ai.periods.today') || 'اليوم' },
                            { id: 'week', label: t('super_admin.ai.periods.week') || 'الأسبوع' },
                            { id: 'month', label: t('super_admin.ai.periods.month') || 'الشهر' }
                        ].map((p) => (
                            <button
                                key={p.id}
                                type="button"
                                onClick={() => setPeriod(p.id)}
                                className={`px-5 py-2 rounded-xl text-sm font-bold transition-all cursor-pointer ${
                                    period === p.id ? 'bg-white text-indigo-600 shadow-md' : 'text-white hover:bg-white/10'
                                }`}
                            >
                                {p.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Truthful Top Metrics Grid (3 authentic metrics) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-6 rounded-[2rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm transition-colors">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 bg-blue-50 text-blue-500 dark:bg-blue-500/10 ${isRtl ? 'me-auto' : 'ms-auto'}`}>
                        <Activity size={28} />
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 font-bold text-xs uppercase tracking-widest text-start">
                        {t('super_admin.ai.stats.total_requests') || 'إجمالي الطلبات'}
                    </p>
                    <div className="flex items-baseline gap-1 mt-1 text-start">
                        <h3 className="text-3xl font-black text-slate-800 dark:text-white">{stats?.total_requests ?? 0}</h3>
                    </div>
                </div>

                <div className="p-6 rounded-[2rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm transition-colors">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 bg-emerald-50 text-emerald-500 dark:bg-emerald-500/10 ${isRtl ? 'me-auto' : 'ms-auto'}`}>
                        <ShieldCheck size={28} />
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 font-bold text-xs uppercase tracking-widest text-start">
                        {t('super_admin.ai.stats.success_rate') || 'نسبة النجاح'}
                    </p>
                    <div className="flex items-baseline gap-1 mt-1 text-start">
                        <h3 className="text-3xl font-black text-slate-800 dark:text-white">{successRateFormatted}</h3>
                    </div>
                </div>

                <div className="p-6 rounded-[2rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm transition-colors">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 bg-amber-50 text-amber-500 dark:bg-amber-500/10 ${isRtl ? 'me-auto' : 'ms-auto'}`}>
                        <DollarSign size={28} />
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 font-bold text-xs uppercase tracking-widest text-start">
                        {t('super_admin.ai.stats.estimated_cost') || 'التكلفة المقدرة'}
                    </p>
                    <div className="flex items-baseline gap-1 mt-1 text-start">
                        <h3 className="text-3xl font-black text-slate-800 dark:text-white">{costFormatted}</h3>
                    </div>
                </div>
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Tool Usage Chart */}
                <div className="p-8 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm">
                    <div className="flex justify-between items-center mb-8">
                        <div className="text-start">
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.ai.charts.tool_usage') || 'استخدام الأدوات'}</h3>
                            <p className="text-sm text-slate-400 font-medium mt-1">{t('super_admin.ai.charts.most_used') || 'أكثر الأدوات طلباً في الفترة المحددة'}</p>
                        </div>
                        <BarChart3 className="text-indigo-500 shrink-0" size={24} />
                    </div>
                    
                    <div className="h-80 w-full" dir="ltr">
                        <LazyChart>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={stats?.tool_usage || []}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" className="text-slate-200 dark:text-slate-800" opacity={0.6} />
                                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#94A3B8', fontSize: 11, fontWeight: 700}} />
                                    <YAxis axisLine={false} tickLine={false} tick={{fill: '#94A3B8', fontSize: 11, fontWeight: 700}} />
                                    <Tooltip 
                                        cursor={{fill: 'rgba(99, 102, 241, 0.05)'}}
                                        contentStyle={{
                                            borderRadius: '1rem', 
                                            border: '1px solid rgba(148, 163, 184, 0.2)', 
                                            boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', 
                                            backgroundColor: '#1e293b',
                                            color: '#f8fafc'
                                        }}
                                        itemStyle={{ fontWeight: 700, color: '#f8fafc' }}
                                    />
                                    <Bar dataKey="value" fill="#6366F1" radius={[8, 8, 0, 0]} barSize={36} />
                                </BarChart>
                            </ResponsiveContainer>
                        </LazyChart>
                    </div>
                </div>

                {/* Trend Chart */}
                <div className="p-8 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm">
                    <div className="flex justify-between items-center mb-8">
                        <div className="text-start">
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.ai.charts.usage_trends') || 'اتجاهات الاستخدام'}</h3>
                            <p className="text-sm text-slate-400 font-medium mt-1">{t('super_admin.ai.charts.daily_activity') || 'النشاط اليومي حسب الفترة'}</p>
                        </div>
                        <Activity className="text-emerald-500 shrink-0" size={24} />
                    </div>
                    
                    <div className="h-80 w-full" dir="ltr">
                        <LazyChart>
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={stats?.usage_trends || []}>
                                    <defs>
                                        <linearGradient id="usageGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.25}/>
                                            <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" className="text-slate-200 dark:text-slate-800" opacity={0.6} />
                                    <XAxis 
                                        dataKey="date" 
                                        axisLine={false} 
                                        tickLine={false} 
                                        tick={{fill: '#94A3B8', fontSize: 11, fontWeight: 700}}
                                        tickFormatter={(val) => {
                                            try {
                                                return new Date(val).toLocaleDateString(i18n.language, {day: 'numeric', month: 'short'});
                                            } catch {
                                                return val;
                                            }
                                        }}
                                    />
                                    <YAxis axisLine={false} tickLine={false} tick={{fill: '#94A3B8', fontSize: 11, fontWeight: 700}} />
                                    <Tooltip 
                                        contentStyle={{
                                            borderRadius: '1rem', 
                                            border: '1px solid rgba(148, 163, 184, 0.2)', 
                                            boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', 
                                            backgroundColor: '#1e293b',
                                            color: '#f8fafc'
                                        }}
                                        itemStyle={{ fontWeight: 700, color: '#f8fafc' }}
                                    />
                                    <Area type="monotone" dataKey="count" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#usageGradient)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </LazyChart>
                    </div>
                </div>
            </div>

            {/* Bottom Grid: Top Users & Recent Logs */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Top Engaged Users */}
                <div className="lg:col-span-1 p-8 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-3 mb-6">
                            <Users className="text-emerald-500" size={24} />
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.ai.users.top_engaged') || 'أكثر المستخدمين تفاعلاً'}</h3>
                        </div>
                        
                        <div className="space-y-3">
                            {stats?.top_users?.length > 0 ? stats.top_users.map((u, i) => (
                                <div key={i} className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                                    <div className="flex items-center gap-3 text-start">
                                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center font-bold shrink-0">
                                            {u.name ? u.name.charAt(0).toUpperCase() : '?'}
                                        </div>
                                        <div>
                                            <div className="font-bold text-slate-700 dark:text-slate-200 text-sm">{u.name || 'Unknown'}</div>
                                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{t('super_admin.ai.users.system_user') || 'مستخدم'}</div>
                                        </div>
                                    </div>
                                    <div className="text-base font-black text-indigo-600 dark:text-indigo-400">{u.count}</div>
                                </div>
                            )) : (
                                <div className="p-8 text-center text-slate-400 font-medium italic">
                                    {t('super_admin.ai.users.no_users') || 'لا يوجد نشاط مستخدمين مسجل'}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Recent Activity Log */}
                <div className="lg:col-span-2 p-8 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm overflow-hidden">
                    <div className="flex items-center gap-3 mb-6">
                        <Terminal className="text-indigo-500" size={24} />
                        <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.ai.logs.title') || 'سجل العمليات الأخير'}</h3>
                    </div>

                    <div className="overflow-x-auto min-w-full">
                        <table className="w-full text-start">
                            <thead>
                                <tr className="text-slate-400 text-xs font-bold uppercase tracking-widest border-b border-slate-100 dark:border-slate-800 text-start">
                                    <th className="pb-4 pe-4 text-start">{t('super_admin.ai.logs.user') || 'المستخدم'}</th>
                                    <th className="pb-4 text-start">{t('super_admin.ai.logs.tool') || 'الأداة'}</th>
                                    <th className="pb-4 text-start">{t('super_admin.ai.logs.status') || 'الحالة'}</th>
                                    <th className="pb-4 text-start">{t('super_admin.ai.logs.time') || 'الوقت'}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                {logs.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="p-8 text-center text-slate-400 font-medium italic">
                                            {t('super_admin.ai.logs.no_logs') || 'لا توجد سجلات ذكاء اصطناعي حديثة'}
                                        </td>
                                    </tr>
                                ) : (
                                    logs.map((log, idx) => (
                                        <tr key={log.id || idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                            <td className="py-4 pe-4 text-start">
                                                <div className="font-bold text-slate-700 dark:text-slate-200 text-sm">{log.username || 'System'}</div>
                                                <div className="text-[10px] text-slate-400 font-bold">Tenant ID: {log.tenant_id ?? 'Global'}</div>
                                            </td>
                                            <td className="py-4 text-start">
                                                <span className="px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold text-xs">
                                                    {log.tool || log.response_tool || 'N/A'}
                                                </span>
                                            </td>
                                            <td className="py-4 text-start">
                                                {(log.status === 'SUCCESS' || log.success) ? (
                                                    <div className="flex items-center gap-1.5 text-emerald-500 font-bold text-xs">
                                                        <ShieldCheck size={16} />
                                                        <span>{t('super_admin.ai.logs.success') || 'ناجح'}</span>
                                                    </div>
                                                ) : (
                                                    <div className="flex items-center gap-1.5 text-rose-500 font-bold text-xs">
                                                        <AlertCircle size={16} />
                                                        <span>{t('super_admin.ai.logs.failed') || 'فاشل'}</span>
                                                    </div>
                                                )}
                                            </td>
                                            <td className="py-4 text-start">
                                                <div className="flex items-center gap-1.5 text-slate-400 font-medium text-xs">
                                                    <Clock size={14} />
                                                    <span>{log.created_at ? new Date(log.created_at).toLocaleTimeString(i18n.language) : '—'}</span>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}

function LoadingPulse() {
    return (
        <div className="space-y-8 animate-pulse">
            <div className="h-64 rounded-[2.5rem] bg-slate-200 dark:bg-slate-800" />
            <div className="grid grid-cols-3 gap-6">
                {[1, 2, 3].map(i => <div key={i} className="h-32 rounded-[2rem] bg-slate-200 dark:bg-slate-800" />)}
            </div>
            <div className="grid grid-cols-2 gap-8">
                <div className="h-80 rounded-[2.5rem] bg-slate-200 dark:bg-slate-800" />
                <div className="h-80 rounded-[2.5rem] bg-slate-200 dark:bg-slate-800" />
            </div>
        </div>
    );
}

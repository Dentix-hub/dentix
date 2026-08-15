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
    ArrowUpRight,
    Terminal,
    Database
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
                setStats(statsRes.data);
                setLogs(logsRes.data);
            } catch (error) {
                logger.error("AI Analytics error:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [period]);

    if (loading && !stats) return <LoadingPulse />;

    return (
        <div className="space-y-8 animate-in fade-in duration-700">
            {/* Header with Glassmorphism */}
            <div className="relative p-8 rounded-[2.5rem] bg-indigo-600 overflow-hidden shadow-2xl shadow-indigo-500/20">
                <div className="absolute top-0 end-0 w-96 h-96 bg-indigo-400 rounded-full blur-[100px] opacity-20 -me-20 -mt-20" />
                <div className="absolute bottom-0 start-0 w-64 h-64 bg-indigo-900 rounded-full blur-[80px] opacity-30 -ms-20 -mb-20" />
                
                <div className={`relative flex flex-col md:flex-row justify-between items-start md:items-center gap-6 ${isRtl ? 'md:flex-row-reverse' : ''}`}>
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <div className={`flex items-center gap-3 mb-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <div className="p-2 bg-white/20 backdrop-blur-md rounded-xl">
                                <Cpu className="text-white" size={24} />
                            </div>
                            <span className="text-indigo-100 font-bold uppercase tracking-widest text-xs">{t('super_admin.ai.command_center')}</span>
                        </div>
                        <h1 className="text-4xl font-extrabold text-white tracking-tight">{t('super_admin.ai.title')}</h1>
                        <p className="text-indigo-100/80 mt-2 font-medium max-w-xl">
                            {t('super_admin.ai.subtitle')}
                        </p>
                    </div>

                    <div className="flex bg-white/10 backdrop-blur-md p-1 rounded-2xl border border-white/10">
                        {[
                            { id: 'today', label: t('super_admin.ai.periods.today') },
                            { id: 'week', label: t('super_admin.ai.periods.week') },
                            { id: 'month', label: t('super_admin.ai.periods.month') }
                        ].map((p) => (
                            <button
                                key={p.id}
                                onClick={() => setPeriod(p.id)}
                                className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${
                                    period === p.id ? 'bg-white text-indigo-600 shadow-lg' : 'text-white hover:bg-white/5'
                                }`}
                            >
                                {p.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Top Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                    { label: t('super_admin.ai.stats.total_requests'), value: stats?.total_requests, icon: Activity, color: 'blue', suffix: '' },
                    { label: t('super_admin.ai.stats.success_rate'), value: `${stats?.success_rate}%`, icon: ShieldCheck, color: 'emerald', suffix: '' },
                    { label: t('super_admin.ai.stats.estimated_cost'), value: stats?.estimated_cost, icon: DollarSign, color: 'amber', suffix: '$' },
                    { label: t('super_admin.ai.stats.active_models'), value: '3', icon: Database, color: 'indigo', suffix: '' },
                ].map((m, i) => (
                    <div key={i} className="group p-6 rounded-[2rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
                        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform ${
                            isRtl ? 'me-auto' : 'ms-auto'
                        } ${
                            m.color === 'blue' ? 'bg-blue-50 text-blue-500 dark:bg-blue-500/10' :
                            m.color === 'emerald' ? 'bg-emerald-50 text-emerald-500 dark:bg-emerald-500/10' :
                            m.color === 'amber' ? 'bg-amber-50 text-amber-500 dark:bg-amber-500/10' :
                            'bg-indigo-50 text-indigo-500 dark:bg-indigo-500/10'
                        }`}>
                            <m.icon size={28} />
                        </div>
                        <p className={`text-slate-500 dark:text-slate-400 font-bold text-xs uppercase tracking-widest ${isRtl ? 'text-right' : 'text-left'}`}>{m.label}</p>
                        <div className={`flex items-baseline gap-1 mt-1 ${isRtl ? 'justify-end' : 'justify-start'}`}>
                            <h3 className="text-3xl font-black text-slate-800 dark:text-white">{m.value}</h3>
                            <span className="text-lg font-bold text-slate-400">{m.suffix}</span>
                        </div>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Usage Chart */}
                <div className="p-8 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm">
                    <div className={`flex justify-between items-center mb-8 ${isRtl ? 'text-right flex-row-reverse' : 'text-left'}`}>
                        <div>
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.ai.charts.tool_usage')}</h3>
                            <p className="text-sm text-slate-400 font-medium mt-1">{t('super_admin.ai.charts.most_used')}</p>
                        </div>
                        <BarChart3 className="text-indigo-500" size={24} />
                    </div>
                    
                    <div className="h-80 w-full">
                        <LazyChart>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={stats?.tool_usage || []}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 700}} />
                                    <YAxis axisLine={false} tickLine={false} tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 700}} />
                                    <Tooltip 
                                        cursor={{fill: '#F8FAFC'}}
                                        contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', direction: isRtl ? 'rtl' : 'ltr'}}
                                    />
                                    <Bar dataKey="value" fill="#6366F1" radius={[8, 8, 0, 0]} barSize={40} />
                                </BarChart>
                            </ResponsiveContainer>
                        </LazyChart>
                    </div>
                </div>

                {/* Trend Chart */}
                <div className="p-8 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm">
                    <div className={`flex justify-between items-center mb-8 ${isRtl ? 'text-right flex-row-reverse' : 'text-left'}`}>
                        <div>
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.ai.charts.usage_trends')}</h3>
                            <p className="text-sm text-slate-400 font-medium mt-1">{t('super_admin.ai.charts.daily_activity')}</p>
                        </div>
                        <Activity className="text-emerald-500" size={24} />
                    </div>
                    
                    <div className="h-80 w-full">
                        <LazyChart>
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={stats?.usage_trends || []}>
                                    <defs>
                                        <linearGradient id="usageGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                                            <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" opacity={0.5} />
                                    <XAxis 
                                        dataKey="date" 
                                        axisLine={false} 
                                        tickLine={false} 
                                        tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 700}}
                                        tickFormatter={(val) => new Date(val).toLocaleDateString(isRtl ? 'ar-EG' : 'en-US', {day: 'numeric', month: 'short'})}
                                    />
                                    <YAxis axisLine={false} tickLine={false} tick={{fill: '#94A3B8', fontSize: 10, fontWeight: 700}} />
                                    <Tooltip 
                                        contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'}}
                                    />
                                    <Area type="monotone" dataKey="count" stroke="#10b981" strokeWidth={4} fillOpacity={1} fill="url(#usageGradient)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </LazyChart>
                    </div>
                </div>
            </div>

                <div className="lg:col-span-1 p-8 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm">
                    <div className={`flex items-center gap-3 mb-6 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <Users className="text-emerald-500" size={24} />
                        <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.ai.users.top_engaged')}</h3>
                    </div>
                    
                    <div className="space-y-4">
                        {stats?.top_users?.length > 0 ? stats.top_users.map((u, i) => (
                            <div key={i} className={`flex items-center justify-between p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors border border-slate-100 dark:border-slate-800/50 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                <div className={`flex items-center gap-3 ${isRtl ? 'flex-row-reverse text-right' : 'text-left'}`}>
                                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center font-bold">
                                        {u.name ? u.name.charAt(0).toUpperCase() : '?'}
                                    </div>
                                    <div>
                                        <div className="font-bold text-slate-700 dark:text-slate-200">{u.name}</div>
                                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{t('super_admin.ai.users.system_user')}</div>
                                    </div>
                                </div>
                                <div className="text-lg font-black text-indigo-600">{u.count}</div>
                            </div>
                        )) : (
                            <div className="p-8 text-center text-slate-400 font-medium italic">
                                {t('super_admin.ai.users.no_users')}
                            </div>
                        )}
                    </div>

                    <button className="w-full mt-6 py-4 rounded-2xl bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 font-bold text-sm hover:bg-indigo-100 transition-all">
                        {t('super_admin.ai.users.view_all')}
                    </button>
                </div>

                {/* Recent Activity Log */}
                <div className="lg:col-span-2 p-8 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm overflow-hidden">
                    <div className={`flex justify-between items-center mb-8 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className={`flex items-center gap-3 ${isRtl ? 'flex-row-reverse text-right' : 'text-left'}`}>
                            <Terminal className="text-indigo-500" size={24} />
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.ai.logs.title')}</h3>
                        </div>
                        <button className={`text-indigo-600 font-bold text-sm flex items-center gap-2 hover:translate-x-${isRtl ? '[-4px]' : '[4px]'} transition-transform ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <span>{t('super_admin.ai.logs.view_all')}</span>
                            <ArrowUpRight size={18} />
                        </button>
                    </div>

                    <div className="overflow-x-auto">
                        <table className={`w-full ${isRtl ? 'text-right' : 'text-left'}`} dir={isRtl ? 'rtl' : 'ltr'}>
                            <thead>
                                <tr className="text-slate-400 text-xs font-bold uppercase tracking-widest border-b border-slate-100 dark:border-slate-800">
                                    <th className="pb-4 pe-4">{t('super_admin.ai.logs.user')}</th>
                                    <th className="pb-4">{t('super_admin.ai.logs.tool')}</th>
                                    <th className="pb-4">{t('super_admin.ai.logs.status')}</th>
                                    <th className={`pb-4 ps-4 ${isRtl ? 'text-left' : 'text-right'}`}>{t('super_admin.ai.logs.time')}</th>
                                </tr>
                            </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {logs.map((log) => (
                                <tr key={log.id} className="group hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                    <td className="py-4 pe-4">
                                        <div className="font-bold text-slate-700 dark:text-slate-200">{log.username}</div>
                                        <div className="text-[10px] text-slate-400 font-bold">Tenant ID: {log.tenant_id}</div>
                                    </td>
                                    <td className="py-4">
                                        <span className="px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold text-xs">
                                            {log.response_tool}
                                        </span>
                                    </td>
                                    <td className="py-4">
                                            {log.success ? (
                                                <div className="flex items-center gap-2 text-emerald-500 font-bold text-sm">
                                                    <ShieldCheck size={16} />
                                                    <span>{t('super_admin.ai.logs.success')}</span>
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-2 text-red-500 font-bold text-sm">
                                                    <AlertCircle size={16} />
                                                    <span>{t('super_admin.ai.logs.failed')}</span>
                                                </div>
                                            )}
                                    </td>
                                        <td className={`py-4 ps-4 ${isRtl ? 'text-left' : 'text-right'}`}>
                                            <div className={`flex items-center gap-2 text-slate-400 font-medium text-xs ${isRtl ? 'justify-end' : 'justify-end'}`}>
                                                <span>{new Date(log.created_at).toLocaleTimeString(isRtl ? 'ar-SA' : 'en-US')}</span>
                                                <Clock size={14} />
                                            </div>
                                        </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

function LoadingPulse() {
    return (
        <div className="space-y-8 animate-pulse">
            <div className="h-64 rounded-[2.5rem] bg-slate-200 dark:bg-slate-800" />
            <div className="grid grid-cols-4 gap-6">
                {[1,2,3,4].map(i => <div key={i} className="h-32 rounded-[2rem] bg-slate-200 dark:bg-slate-800" />)}
            </div>
            <div className="grid grid-cols-3 gap-8">
                <div className="col-span-2 h-96 rounded-[2.5rem] bg-slate-200 dark:bg-slate-800" />
                <div className="h-96 rounded-[2.5rem] bg-slate-200 dark:bg-slate-800" />
            </div>
        </div>
    );
}

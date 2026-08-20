import { useState, useEffect, useCallback } from 'react';
import logger from '@/utils/logger';
import { useTranslation } from 'react-i18next';
import { api } from '@/api';
import {
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    AreaChart,
    Area,
    LazyChart
} from '@/components/charts/LazyChart';
import {
    TrendingUp,
    AlertTriangle,
    PieChart as PieIcon,
    Download,
    Users
} from 'lucide-react';
import { toast } from '@/shared/ui';

const COLORS = ['#10b981', '#6366f1', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export default function FinanceReports() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchReports = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.get('/api/v1/admin/finance/reports');
            setData(res.data);
        } catch (err) {
            logger.error('Failed to fetch finance reports:', err);
            toast.error(t('super_admin.finance.error_fetch'));
        } finally {
            setLoading(false);
        }
    }, [t]);

    useEffect(() => {
        fetchReports();
    }, [fetchReports]);

    const handleExport = (type) => {
        if (!data) return;
        
        let exportData = [];
        let filename = `report_${type}_${new Date().toISOString().split('T')[0]}.csv`;
        
        if (type === 'revenue_by_plan') {
            exportData = data.revenue_by_plan.map(p => ({ [t('super_admin.tenants.plan')]: p.name, [t('super_admin.ai.logs.status')]: p.value }));
        } else if (type === 'overdue_clinics') {
            exportData = data.overdue_clinics.map(c => ({ [t('super_admin.tenants.title')]: c.name, [t('super_admin.plans.expiry')]: c.expiry_date, [t('super_admin.finance.overdue_clinics')]: c.days_overdue }));
        } else if (type === 'churn_risks') {
            exportData = data.churn_risks.map(c => ({ [t('super_admin.tenants.title')]: c.name, [t('super_admin.ai.logs.time')]: c.last_active, [t('super_admin.tenants.plan')]: c.plan_name }));
        }

        if (exportData.length === 0) {
            toast.error(t('common.no_results'));
            return;
        }

        const headers = Object.keys(exportData[0]).join(',');
        const rows = exportData.map(row => Object.values(row).join(',')).join('\n');
        const csvContent = "\ufeff" + headers + '\n' + rows;
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        toast.success(t('super_admin.finance.export_success', { type }));
    };

    if (loading) return (
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
            <p className="text-slate-500 font-bold animate-pulse">{t('super_admin.finance.loading')}</p>
        </div>
    );

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header / Stats Summary */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 p-8 rounded-[2.5rem] text-white shadow-xl shadow-emerald-500/20 relative overflow-hidden group col-span-1 md:col-span-2">
                    <div className="absolute top-0 end-0 w-32 h-32 bg-white/10 rounded-full blur-3xl -me-16 -mt-16 group-hover:scale-150 transition-transform duration-700"></div>
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <p className="text-emerald-100 font-bold text-xs uppercase tracking-widest mb-1">{t('super_admin.finance.monthly_forecast_title')}</p>
                        <div className={`flex items-baseline gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <h3 className="text-4xl font-black">{data?.monthly_forecast?.toLocaleString()}</h3>
                            <span className="text-xl font-bold">{t('super_admin.finance.currency')}</span>
                        </div>
                        <div className={`mt-4 flex items-center gap-2 text-xs font-bold bg-white/20 backdrop-blur-md w-fit px-3 py-1.5 rounded-full ${isRtl ? 'flex-row-reverse me-auto ms-0' : 'ms-auto me-0'}`}>
                            <TrendingUp size={14} />
                            <span>{t('super_admin.finance.mrr_desc')}</span>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-900 p-8 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 shadow-sm flex flex-col justify-between">
                    <div className={`flex justify-between items-start ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className={isRtl ? 'text-right' : 'text-left'}>
                            <p className="text-slate-500 font-bold text-xs uppercase tracking-widest mb-1">{t('super_admin.finance.overdue_clinics')}</p>
                            <h3 className="text-4xl font-black text-slate-800 dark:text-white">{data?.overdue_clinics?.length || 0}</h3>
                        </div>
                        <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-500 rounded-2xl">
                            <AlertTriangle size={24} />
                        </div>
                    </div>
                    <div className={`mt-4 text-xs font-bold text-red-500 ${isRtl ? 'text-right' : 'text-left'}`}>{t('super_admin.finance.collection_alert')}</div>
                </div>

                <div className="bg-white dark:bg-slate-900 p-8 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 shadow-sm flex flex-col justify-between">
                    <div className={`flex justify-between items-start ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className={isRtl ? 'text-right' : 'text-left'}>
                            <p className="text-slate-500 font-bold text-xs uppercase tracking-widest mb-1">{t('super_admin.finance.churn_risk_title')}</p>
                            <h3 className="text-4xl font-black text-slate-800 dark:text-white">{data?.churn_risks?.length || 0}</h3>
                        </div>
                        <div className="p-3 bg-amber-50 dark:bg-amber-900/20 text-amber-500 rounded-2xl">
                            <Users size={24} />
                        </div>
                    </div>
                    <div className={`mt-4 text-xs font-bold text-amber-500 ${isRtl ? 'text-right' : 'text-left'}`}>{t('super_admin.finance.inactive_clinics')}</div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Revenue by Plan Chart */}
                <div className="bg-white dark:bg-slate-900 p-8 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 shadow-sm">
                    <div className={`flex justify-between items-center mb-8 ${isRtl ? 'flex-row-reverse' : ''}`} dir={isRtl ? 'rtl' : 'ltr'}>
                        <div className={`flex items-center gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <PieIcon className="text-emerald-500" size={24} />
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.finance.revenue_by_plan')}</h3>
                        </div>
                        <button onClick={() => handleExport('revenue_by_plan')} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors">
                            <Download size={20} className="text-slate-400" />
                        </button>
                    </div>
                    
                    <div className="h-80">
                        <LazyChart>
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={data?.revenue_by_plan || []}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={80}
                                        outerRadius={110}
                                        paddingAngle={5}
                                        dataKey="value"
                                    >
                                        {(data?.revenue_by_plan || []).map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip 
                                        contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', direction: isRtl ? 'rtl' : 'ltr'}}
                                        formatter={(value) => `${value.toLocaleString()} ${t('super_admin.finance.currency')}`}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        </LazyChart>
                    </div>

                    <div className={`grid grid-cols-2 gap-4 mt-4 ${isRtl ? 'text-right' : 'text-left'}`}>
                        {(data?.revenue_by_plan || []).map((p, i) => (
                            <div key={i} className={`flex items-center gap-2 text-sm font-bold text-slate-600 dark:text-slate-300 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }}></div>
                                <span>{p.name}: {p.value.toLocaleString()} {t('super_admin.finance.currency')}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Overdue Clinics List */}
                <div className="bg-white dark:bg-slate-900 p-8 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 shadow-sm flex flex-col">
                    <div className={`flex justify-between items-center mb-8 ${isRtl ? 'flex-row-reverse' : ''}`} dir={isRtl ? 'rtl' : 'ltr'}>
                        <div className={`flex items-center gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <AlertTriangle className="text-red-500" size={24} />
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.finance.overdue_clinics')}</h3>
                        </div>
                        <button onClick={() => handleExport('overdue_clinics')} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors">
                            <Download size={20} className="text-slate-400" />
                        </button>
                    </div>

                    <div className="flex-1 space-y-4 overflow-y-auto max-h-[400px] pe-2 custom-scrollbar">
                        {data?.overdue_clinics?.length > 0 ? data.overdue_clinics.map((clinic) => (
                            <div key={clinic.id} className={`flex items-center justify-between p-4 rounded-2xl bg-red-50/50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/20 group hover:bg-red-50 dark:hover:bg-red-900/20 transition-all ${isRtl ? 'flex-row-reverse' : ''}`}>
                                <div className={`flex items-center gap-4 ${isRtl ? 'flex-row-reverse text-right' : 'text-left'}`}>
                                    <div className="w-12 h-12 rounded-xl bg-red-500/10 text-red-600 flex items-center justify-center font-black">
                                        {clinic.days_overdue}
                                    </div>
                                    <div>
                                        <div className="font-bold text-slate-800 dark:text-white">{clinic.name}</div>
                                        <div className="text-xs text-slate-500 font-bold">{t('super_admin.tenants.plan')}: {clinic.plan_name}</div>
                                    </div>
                                </div>
                                <div className={isRtl ? 'text-left' : 'text-right'}>
                                    <div className="text-sm font-black text-red-600">{t('super_admin.finance.overdue_clinics')} {clinic.days_overdue} {t('common.days')}</div>
                                    <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{t('super_admin.plans.expiry')}: {new Date(clinic.expiry_date).toLocaleDateString(isRtl ? 'ar-EG' : 'en-US')}</div>
                                </div>
                            </div>
                        )) : (
                            <div className="h-full flex flex-col items-center justify-center text-slate-400 italic">
                                <ShieldCheck size={48} className="mb-4 opacity-20" />
                                <p>{t('super_admin.finance.no_overdue')}</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Churn Risk Section */}
            <div className="bg-white dark:bg-slate-900 p-8 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 shadow-sm">
                <div className={`flex justify-between items-center mb-8 ${isRtl ? 'flex-row-reverse' : ''}`} dir={isRtl ? 'rtl' : 'ltr'}>
                    <div className={`flex items-center gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <Users className="text-amber-500" size={24} />
                        <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.finance.churn_risk_title')} ({t('super_admin.finance.inactive_clinics')})</h3>
                    </div>
                    <button onClick={() => handleExport('churn_risks')} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors">
                        <Download size={20} className="text-slate-400" />
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {data?.churn_risks?.length > 0 ? data.churn_risks.map((clinic) => (
                        <div key={clinic.id} className="p-6 rounded-[2rem] border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 hover:border-amber-200 dark:hover:border-amber-900/50 transition-all group">
                            <div className={`flex items-start justify-between mb-4 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                <div className="p-3 bg-white dark:bg-slate-800 rounded-2xl shadow-sm">
                                    <Users size={24} className="text-amber-500" />
                                </div>
                                <div className="px-3 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 text-[10px] font-black rounded-full uppercase">{t('super_admin.finance.high_risk')}</div>
                            </div>
                            <h4 className={`font-black text-slate-800 dark:text-white mb-1 ${isRtl ? 'text-right' : 'text-left'}`}>{clinic.name}</h4>
                            <p className={`text-xs text-slate-500 font-bold mb-4 ${isRtl ? 'text-right' : 'text-left'}`}>{clinic.plan_name}</p>
                            <div className={`flex items-center justify-between text-xs pt-4 border-t border-slate-100 dark:border-slate-800 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                <span className="text-slate-400 font-bold">{t('super_admin.ai.logs.time')}:</span>
                                <span className="text-slate-700 dark:text-slate-300 font-black">
                                    {clinic.last_active ? new Date(clinic.last_active).toLocaleDateString(isRtl ? 'ar-EG' : 'en-US') : t('common.no_results')}
                                </span>
                            </div>
                        </div>
                    )) : (
                        <div className="col-span-full h-32 flex flex-col items-center justify-center text-slate-400 italic">
                            <p>{t('super_admin.finance.no_churn')}</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Growth Trends Chart */}
            <div className="bg-white dark:bg-slate-900 p-8 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 shadow-sm">
                    <div className={`flex items-center gap-3 ${isRtl ? 'flex-row-reverse text-right' : 'text-left'}`}>
                        <TrendingUp className="text-indigo-500" size={24} />
                        <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.finance.growth_trends')}</h3>
                    </div>

                <div className="h-80">
                    <LazyChart>
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={data?.growth_trends || []}>
                                <defs>
                                    <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                                <XAxis 
                                    dataKey="month" 
                                    axisLine={false} 
                                    tickLine={false} 
                                    tick={{fill: '#94A3B8', fontSize: 12, fontWeight: 700}} 
                                    dy={10} 
                                />
                                <YAxis 
                                    axisLine={false} 
                                    tickLine={false} 
                                    tick={{fill: '#94A3B8', fontSize: 12, fontWeight: 700}} 
                                    formatter={(value) => `${value / 1000}k`}
                                />
                                <Tooltip 
                                    contentStyle={{borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', direction: isRtl ? 'rtl' : 'ltr'}}
                                    formatter={(value) => [`${value.toLocaleString()} ${t('super_admin.finance.currency')}`, t('super_admin.finance.title')]}
                                />
                                <Area 
                                    type="monotone" 
                                    dataKey="revenue" 
                                    stroke="#6366f1" 
                                    strokeWidth={4}
                                    fillOpacity={1} 
                                    fill="url(#colorRev)" 
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </LazyChart>
                </div>
            </div>
        </div>
    );
}

function ShieldCheck({ size, className }) {
    return (
        <svg 
            xmlns="http://www.w3.org/2000/svg" 
            width={size} 
            height={size} 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            className={className}
        >
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
            <path d="m9 12 2 2 4-4" />
        </svg>
    );
}

import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    BarChart,
    Bar,
    PieChart,
    Pie,
    Cell,
    LazyChart
} from '@/components/charts/LazyChart';

function formatMonthLabel(monthKey, isRtl) {
    if (!monthKey || typeof monthKey !== 'string') return monthKey || '';
    const parts = monthKey.split('-');
    if (parts.length !== 2) return monthKey;
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10);
    if (isNaN(year) || isNaN(month)) return monthKey;

    const date = new Date(year, month - 1, 1);
    return date.toLocaleDateString(isRtl ? 'ar-EG' : 'en-US', { month: 'short', year: '2-digit' });
}

const AdminCharts = memo(function AdminCharts({ stats }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    // Process Revenue Data with formatted labels
    const revenueData = Object.entries(stats?.monthly_revenue || {})
        .map(([name, value]) => ({ 
            name, 
            label: formatMonthLabel(name, isRtl),
            value: value != null ? Number(value) : 0 
        }))
        .sort((a, b) => a.name.localeCompare(b.name));

    // Process Growth Data with formatted labels
    const growthData = Object.entries(stats?.clinic_growth || {})
        .map(([name, count]) => ({ 
            name, 
            label: formatMonthLabel(name, isRtl),
            count: count != null ? Number(count) : 0 
        }))
        .sort((a, b) => a.name.localeCompare(b.name));

    // Process Plan Data
    const planData = Object.entries(stats?.plan_distribution || {})
        .map(([name, value]) => ({ 
            name, 
            value: value != null ? Number(value) : 0 
        }));

    const COLORS = ['#6366f1', '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" dir={isRtl ? 'rtl' : 'ltr'}>
            {/* Revenue Trend */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm">
                <h3 className="text-lg font-bold mb-6 text-slate-800 dark:text-white">{t('super_admin.charts.revenue_title') || 'إيرادات الاشتراكات (آخر 12 شهر)'}</h3>
                <div className="h-[300px] w-full">
                    <LazyChart>
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={revenueData} layout="horizontal">
                                <defs>
                                    <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15}/>
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#94a3b820" />
                                <XAxis 
                                    dataKey="label" 
                                    axisLine={false} 
                                    tickLine={false} 
                                    tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 600 }}
                                    orientation="bottom"
                                    reversed={isRtl}
                                />
                                <YAxis 
                                    axisLine={false} 
                                    tickLine={false} 
                                    tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 600 }}
                                    orientation={isRtl ? 'right' : 'left'}
                                    tickFormatter={(value) => `${value >= 1000 ? `${value / 1000}k` : value}`}
                                />
                                <Tooltip 
                                    contentStyle={{ 
                                        borderRadius: '16px', 
                                        border: '1px solid rgba(148, 163, 184, 0.1)', 
                                        boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)',
                                        backgroundColor: '#1e293b',
                                        color: '#fff',
                                        textAlign: isRtl ? 'right' : 'left'
                                    }}
                                    formatter={(value) => [`${Number(value).toLocaleString(isRtl ? 'ar-EG' : 'en-US')} ${t('super_admin.finance.currency') || 'ج.م'}`, t('super_admin.finance.title') || 'الإيرادات'] }
                                />
                                <Area 
                                    type="monotone" 
                                    dataKey="value" 
                                    stroke="#6366f1" 
                                    strokeWidth={3}
                                    fillOpacity={1} 
                                    fill="url(#colorRev)" 
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </LazyChart>
                </div>
            </div>

            {/* Clinic Growth */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm">
                <h3 className="text-lg font-bold mb-6 text-slate-800 dark:text-white">{t('super_admin.charts.growth_title') || 'نمو العيادات (آخر 12 شهر)'}</h3>
                <div className="h-[300px] w-full">
                    <LazyChart>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={growthData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#94a3b820" />
                                <XAxis 
                                    dataKey="label" 
                                    axisLine={false} 
                                    tickLine={false} 
                                    tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 600 }}
                                    reversed={isRtl}
                                />
                                <YAxis 
                                    axisLine={false} 
                                    tickLine={false} 
                                    tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 600 }}
                                    orientation={isRtl ? 'right' : 'left'}
                                    allowDecimals={false}
                                />
                                <Tooltip 
                                    cursor={{ fill: 'rgba(20, 184, 166, 0.05)' }}
                                    contentStyle={{ 
                                        borderRadius: '16px', 
                                        border: '1px solid rgba(148, 163, 184, 0.1)', 
                                        boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)',
                                        backgroundColor: '#1e293b',
                                        color: '#fff',
                                        textAlign: isRtl ? 'right' : 'left'
                                    }}
                                    formatter={(value) => [`${value} ${t('super_admin.tenants.title') || 'عيادة'}`, t('super_admin.charts.growth_title') || 'النمو'] }
                                />
                                <Bar 
                                    dataKey="count" 
                                    fill="#14b8a6" 
                                    radius={[6, 6, 0, 0]} 
                                    barSize={32}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </LazyChart>
                </div>
            </div>

            {/* Plan Distribution */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm lg:col-span-2">
                <h3 className="text-lg font-bold mb-6 text-slate-800 dark:text-white">{t('super_admin.charts.distribution_title') || 'توزيع الخطط'}</h3>
                <div className={`w-full min-h-[300px] flex flex-col md:flex-row items-center justify-around gap-8 ${isRtl ? 'md:flex-row-reverse' : ''}`}>
                    <div className="h-[280px] w-full max-w-md">
                        <LazyChart>
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={planData}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={65}
                                        outerRadius={105}
                                        paddingAngle={5}
                                        dataKey="value"
                                    >
                                        {planData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip 
                                        contentStyle={{ 
                                            borderRadius: '16px', 
                                            border: '1px solid rgba(148, 163, 184, 0.1)', 
                                            boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)',
                                            backgroundColor: '#1e293b',
                                            color: '#fff',
                                            textAlign: isRtl ? 'right' : 'left'
                                        }}
                                        formatter={(value) => [`${value} ${t('super_admin.tenants.title') || 'عيادة'}`, t('super_admin.tenants.plan') || 'الخطة'] }
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        </LazyChart>
                    </div>
                    
                    {/* Custom Non-Duplicated Legend Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-md">
                        {planData.length > 0 ? planData.map((plan, idx) => (
                            <div key={idx} className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 flex items-center justify-between gap-3">
                                <div className="flex items-center gap-2.5">
                                    <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                                    <span className="text-xs font-bold text-slate-600 dark:text-slate-300 truncate max-w-[120px]">{plan.name}</span>
                                </div>
                                <span className="text-base font-black text-slate-800 dark:text-white">{plan.value}</span>
                            </div>
                        )) : (
                            <div className="col-span-full text-center text-slate-400 py-6 text-sm italic">
                                {t('common.no_results') || 'لا توجد بيانات متاحة'}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
});

export default AdminCharts;

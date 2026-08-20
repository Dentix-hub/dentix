import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDoctorRevenue } from '@/api';
import { useTranslation } from 'react-i18next';
import { Users, Award, TrendingUp, UserCheck, Calendar } from 'lucide-react';

export default function DoctorPerformanceTab() {
    const { i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    const today = new Date();
    const oneMonthAgo = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate()).toISOString().split('T')[0];
    const currentDay = today.toISOString().split('T')[0];

    const [startDate, setStartDate] = useState(oneMonthAgo);
    const [endDate, setEndDate] = useState(currentDay);

    const { data, isLoading } = useQuery({
        queryKey: ['doctor_revenue_analytics', startDate, endDate],
        queryFn: async () => {
            const res = await getDoctorRevenue(startDate, endDate);
            const doctors = (res.data?.doctors || []).filter(d => d.doctor_name !== 'غير محدد');
            return doctors;
        },
        staleTime: 2 * 60 * 1000,
    });

    const doctors = data || [];

    const totalProductivity = doctors.reduce((acc, doc) => acc + (doc.net_revenue || 0), 0);
    const totalCommissions = doctors.reduce((acc, doc) => {
        const comm = (doc.net_revenue || 0) * ((doc.commission_percent || 0) / 100);
        return acc + comm + (doc.fixed_salary || 0);
    }, 0);

    if (isLoading) {
        return (
            <div className="space-y-6 animate-pulse">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[1, 2, 3].map(i => <div key={i} className="h-28 bg-surface rounded-2xl"></div>)}
                </div>
                <div className="h-64 bg-surface rounded-3xl"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header & Date Range */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface p-5 rounded-3xl border border-border/50 shadow-sm">
                <div>
                    <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
                        <Users className="text-indigo-500" size={20} />
                        {isRtl ? 'تقرير أداء وإنتاجية الأطباء والعمولات' : 'Doctor Performance & Commissions'}
                    </h3>
                    <p className="text-xs text-text-secondary mt-0.5">
                        {isRtl ? 'متابعة الإنتاجية الفردية وحساب العمولات والمستحقات لكل طبيب' : 'Track individual doctor productivity, commissions, and total earnings'}
                    </p>
                </div>
                <div className="flex items-center gap-2 bg-surface-hover p-1.5 rounded-2xl border border-border/50 text-xs font-mono">
                    <Calendar size={14} className="text-text-tertiary ms-1" />
                    <input
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        className="bg-transparent text-text-primary outline-none"
                    />
                    <span className="text-text-tertiary">→</span>
                    <input
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="bg-transparent text-text-primary outline-none"
                    />
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-surface p-5 rounded-2xl border border-border/50 shadow-sm flex items-center gap-4">
                    <div className="p-3 bg-indigo-500/10 text-indigo-500 rounded-2xl">
                        <UserCheck size={24} />
                    </div>
                    <div>
                        <div className="text-xs text-text-secondary font-bold">{isRtl ? 'الأطباء النشطون' : 'Active Doctors'}</div>
                        <div className="text-2xl font-black text-text-primary">{doctors.length}</div>
                    </div>
                </div>

                <div className="bg-surface p-5 rounded-2xl border border-border/50 shadow-sm flex items-center gap-4">
                    <div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-2xl">
                        <TrendingUp size={24} />
                    </div>
                    <div>
                        <div className="text-xs text-text-secondary font-bold">{isRtl ? 'إجمالي إنتاجية الأطباء' : 'Total Productivity'}</div>
                        <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400 font-mono">
                            ${totalProductivity.toLocaleString()}
                        </div>
                    </div>
                </div>

                <div className="bg-surface p-5 rounded-2xl border border-border/50 shadow-sm flex items-center gap-4">
                    <div className="p-3 bg-amber-500/10 text-amber-500 rounded-2xl">
                        <Award size={24} />
                    </div>
                    <div>
                        <div className="text-xs text-text-secondary font-bold">{isRtl ? 'إجمالي المستحقات والعمولات' : 'Total Commissions'}</div>
                        <div className="text-2xl font-black text-amber-600 dark:text-amber-400 font-mono">
                            ${totalCommissions.toLocaleString()}
                        </div>
                    </div>
                </div>
            </div>

            {/* Doctor Breakdown Grid */}
            <div className="bg-surface rounded-3xl border border-border/50 shadow-sm overflow-hidden p-6">
                <h4 className="font-bold text-text-primary text-base mb-4">
                    {isRtl ? 'تفاصيل إنتاجية ومستحقات كل طبيب' : 'Individual Doctor Breakdown'}
                </h4>

                <div className="overflow-x-auto">
                    <table className="w-full text-xs text-start">
                        <thead className="bg-surface-hover text-text-secondary uppercase font-bold text-[11px]">
                            <tr>
                                <th className="p-3.5 text-start">{isRtl ? 'اسم الطبيب' : 'Doctor Name'}</th>
                                <th className="p-3.5 text-center">{isRtl ? 'إجمالي الإنتاجية' : 'Net Revenue'}</th>
                                <th className="p-3.5 text-center">{isRtl ? 'نسبة العمولة' : 'Commission %'}</th>
                                <th className="p-3.5 text-center">{isRtl ? 'الراتب الثابت' : 'Fixed Salary'}</th>
                                <th className="p-3.5 text-center">{isRtl ? 'إجمالي المستحق' : 'Total Earnings'}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/40 text-text-primary font-medium">
                            {doctors.map((doc, i) => {
                                const commVal = (doc.net_revenue || 0) * ((doc.commission_percent || 0) / 100);
                                const totalDocEarn = commVal + (doc.fixed_salary || 0);
                                return (
                                    <tr key={i} className="hover:bg-surface-hover/50 transition-colors">
                                        <td className="p-3.5 font-bold text-sm flex items-center gap-2">
                                            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
                                            {doc.doctor_name}
                                        </td>
                                        <td className="p-3.5 text-center font-mono font-bold text-emerald-600 dark:text-emerald-400 text-sm">
                                            ${(doc.net_revenue || 0).toLocaleString()}
                                        </td>
                                        <td className="p-3.5 text-center">
                                            <span className="px-2 py-1 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 rounded-lg font-bold">
                                                {doc.commission_percent || 0}%
                                            </span>
                                        </td>
                                        <td className="p-3.5 text-center font-mono text-text-secondary">
                                            ${(doc.fixed_salary || 0).toLocaleString()}
                                        </td>
                                        <td className="p-3.5 text-center font-mono font-black text-amber-600 dark:text-amber-400 text-sm">
                                            ${totalDocEarn.toLocaleString()}
                                        </td>
                                    </tr>
                                );
                            })}
                            {doctors.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="p-8 text-center text-text-tertiary">
                                        {isRtl ? 'لا توجد بيانات أطباء للفترة المحددة' : 'No doctor data found for this period'}
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

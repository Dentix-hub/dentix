import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getProfitability } from '@/api/analytics';
import KPIGrid from './components/KPIGrid';
import ProfitChart from './components/ProfitChart';
import AiAdvisor from './components/AiAdvisor';
import ProcedureCostAnalysis from './components/ProcedureCostAnalysis';
import GeneralCostAnalysis from './components/GeneralCostAnalysis';
import { PieChart, Activity } from 'lucide-react';
import { useTranslation } from 'react-i18next';
const SmartDashboard = () => {
    const { t } = useTranslation();
    const [period, setPeriod] = useState('30d');
    const [activeTab, setActiveTab] = useState('financials'); // financials, procedures
    const { data, isLoading, error } = useQuery({
        queryKey: ['profitability', period],
        queryFn: () => getProfitability(period),
        refetchOnWindowFocus: false,
        staleTime: 5 * 60 * 1000 // 5 minutes
    });
    return (
        <div className="p-4 md:p-8 space-y-6 max-w-[1920px] mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
            {/* Header Area */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                <div>
                    <h1 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight">{t('analytics.dashboard.title')}</h1>
                    <p className="text-slate-500 mt-1 font-medium">{t('analytics.dashboard.subtitle')}</p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                    {/* Period Selector */}
                    <div className="flex bg-white dark:bg-slate-800 rounded-xl p-1.5 border border-slate-200 dark:border-slate-700 shadow-sm">
                        {['7d', '30d', '90d'].map((p) => (
                            <button
                                key={p}
                                onClick={() => setPeriod(p)}
                                className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${period === p
                                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-200 dark:shadow-none'
                                    : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-slate-900'
                                    }`}
                            >
                                {p === '7d' ? t('analytics.dashboard.periods.week') : p === '30d' ? t('analytics.dashboard.periods.month') : t('analytics.dashboard.periods.three_months')}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
            {/* Main Tabs */}
            <div className="border-b border-slate-200 dark:border-slate-700 mb-6">
                <div className="flex space-x-8 rtl:space-x-reverse overflow-x-auto">
                    <button
                        onClick={() => setActiveTab('financials')}
                        className={`pb-4 px-2 text-sm font-bold transition-all border-b-2 flex items-center gap-2 whitespace-nowrap ${activeTab === 'financials'
                            ? 'border-indigo-600 text-indigo-600'
                            : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                            }`}
                    >
                        <PieChart size={18} />
                        {t('analytics.dashboard.tabs.financials')}
                    </button>
                    <button
                        onClick={() => setActiveTab('procedures')}
                        className={`pb-4 px-2 text-sm font-bold transition-all border-b-2 flex items-center gap-2 whitespace-nowrap ${activeTab === 'procedures'
                            ? 'border-indigo-600 text-indigo-600'
                            : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                            }`}
                    >
                        <Activity size={18} />
                        {t('analytics.dashboard.tabs.procedures')}
                    </button>
                </div>
            </div>
            {/* Error State */}
            {error && (
                <div className="bg-red-50 text-red-600 p-4 rounded-xl border border-red-100 flex items-center justify-center font-bold">
                    {t('analytics.dashboard.error_loading')} {error.message}
                </div>
            )}
            {/* Tab: Financial Overview */}
            {activeTab === 'financials' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                    {isLoading && !data ? (
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                {[1, 2, 3, 4].map(i => <div key={i} className="h-32 bg-slate-100 dark:bg-slate-800 rounded-2xl animate-pulse"></div>)}
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div className="h-[450px] bg-slate-100 dark:bg-slate-800 rounded-2xl animate-pulse"></div>
                                <div className="md:col-span-2 h-[450px] bg-slate-100 dark:bg-slate-800 rounded-2xl animate-pulse"></div>
                            </div>
                        </div>
                    ) : (() => {
                        const safeData = {
                            revenue: data?.revenue || 0,
                            net_profit: data?.net_profit || 0,
                            margin_percent: data?.margin_percent || 0,
                            total_costs: data?.total_costs || 0,
                            breakdown: {
                                expenses: data?.breakdown?.expenses || 0,
                                material_costs: data?.breakdown?.material_costs || 0,
                                lab_costs: data?.breakdown?.lab_costs || 0,
                            },
                            ...data
                        };
                        return (
                            <>
                                <KPIGrid data={safeData} />
                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                    <div className="lg:col-span-1 h-full">
                                        <ProfitChart data={safeData} />
                                    </div>
                                    <div className="lg:col-span-2 h-full">
                                        <AiAdvisor stats={safeData} />
                                    </div>
                                </div>
                            </>
                        );
                    })()}
                </div>
            )}
            {/* Tab: Procedure Analytics */}
            {activeTab === 'procedures' && (
                <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
                    {/* Top: General Analysis (All Procedures) */}
                    <GeneralCostAnalysis />
                    <div className="border-t border-slate-200 dark:border-slate-700 my-8"></div>
                    {/* Bottom: Detailed Single Procedure Analysis */}
                    <div className="bg-slate-50 dark:bg-slate-900/50 p-6 rounded-3xl border border-dashed border-slate-200 dark:border-slate-800">
                        <div className="mb-4">
                            <h3 className="text-lg font-bold text-slate-700 dark:text-slate-300">{t('analytics.general_analysis.table.title')}</h3>
                            <p className="text-sm text-slate-500">{t('analytics.general_analysis.table.subtitle')}</p>
                        </div>
                        <ProcedureCostAnalysis />
                    </div>
                </div>
            )}
        </div>
    );
};
export default SmartDashboard;

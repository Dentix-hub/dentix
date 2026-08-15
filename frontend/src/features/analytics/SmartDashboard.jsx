import { useState } from 'react';
import logger from '@/utils/logger';
import { useQuery } from '@tanstack/react-query';
import { getProfitability } from '@/api/analytics';
import KPIGrid from './components/KPIGrid';
import ProfitChart from './components/ProfitChart';
import AiAdvisor from './components/AiAdvisor';
import ProcedureCostAnalysis from './components/ProcedureCostAnalysis';
import GeneralCostAnalysis from './components/GeneralCostAnalysis';
import RevenueTrendChart from './components/RevenueTrendChart';
import AnalyticsDatePicker from './components/AnalyticsDatePicker';
import AnalyticsExportButton from './components/AnalyticsExportButton';
import DoctorPerformanceTab from './components/DoctorPerformanceTab';
import { PieChart, Activity, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const SmartDashboard = () => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [period, setPeriod] = useState('30d');
    const [customStartDate, setCustomStartDate] = useState('');
    const [customEndDate, setCustomEndDate] = useState('');
    const [activeTab, setActiveTab] = useState('financials'); // financials, procedures, doctors

    const { data, isLoading, error } = useQuery({
        queryKey: ['profitability', period],
        queryFn: async () => {
            try {
                const res = await getProfitability(period);
                return res;
            } catch (err) {
                logger.error('[Analytics] Profitability error:', err);
                throw err;
            }
        },
        refetchOnWindowFocus: true,
        staleTime: 2 * 60 * 1000,
        retry: 1
    });

    return (
        <div className="p-4 md:p-8 space-y-6 max-w-[1920px] mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
            {/* Header Area */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                <div>
                    <h1 className="text-3xl font-bold text-slate-800 dark:text-white tracking-tight">{t('analytics.dashboard.title')}</h1>
                    <p className="text-slate-500 mt-1 font-medium">{t('analytics.dashboard.subtitle')}</p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                    <AnalyticsExportButton />
                    <AnalyticsDatePicker
                        period={period}
                        setPeriod={setPeriod}
                        customStartDate={customStartDate}
                        setCustomStartDate={setCustomStartDate}
                        customEndDate={customEndDate}
                        setCustomEndDate={setCustomEndDate}
                    />
                </div>
            </div>

            {/* Main Tabs */}
            <div className="border-b border-slate-200 dark:border-slate-700 mb-6">
                <div className="flex space-x-8 rtl:space-x-reverse overflow-x-auto">
                    <button
                        onClick={() => setActiveTab('financials')}
                        className={`pb-4 px-2 text-sm font-bold transition-all border-b-2 flex items-center gap-2 whitespace-nowrap ${activeTab === 'financials'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                            }`}
                    >
                        <PieChart size={18} />
                        {t('analytics.dashboard.tabs.financials')}
                    </button>
                    <button
                        onClick={() => setActiveTab('procedures')}
                        className={`pb-4 px-2 text-sm font-bold transition-all border-b-2 flex items-center gap-2 whitespace-nowrap ${activeTab === 'procedures'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                            }`}
                    >
                        <Activity size={18} />
                        {t('analytics.dashboard.tabs.procedures')}
                    </button>
                    <button
                        onClick={() => setActiveTab('doctors')}
                        className={`pb-4 px-2 text-sm font-bold transition-all border-b-2 flex items-center gap-2 whitespace-nowrap ${activeTab === 'doctors'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                            }`}
                    >
                        <Users size={18} />
                        {isRtl ? 'أداء الأطباء' : 'Doctors Performance'}
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
                <div className="space-y-6 animate-in fade-in slide-in-from-end-4 duration-300">
                    {isLoading && !data ? (
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                {[1, 2, 3, 4].map(i => <div key={i} className="h-32 bg-slate-100 dark:bg-slate-800 rounded-2xl animate-pulse"></div>)}
                            </div>
                            <div className="h-[300px] bg-slate-100 dark:bg-slate-800 rounded-3xl animate-pulse"></div>
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
                            previous_period: data?.previous_period || null,
                            ...data
                        };
                        return (
                            <>
                                <KPIGrid data={safeData} />

                                {/* Interactive Revenue Trend Curve */}
                                <RevenueTrendChart period={period} />

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
                <div className="space-y-8 animate-in fade-in slide-in-from-end-4 duration-300">
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

            {/* Tab: Doctors Performance */}
            {activeTab === 'doctors' && (
                <div className="space-y-8 animate-in fade-in slide-in-from-end-4 duration-300">
                    <DoctorPerformanceTab />
                </div>
            )}
        </div>
    );
};

export default SmartDashboard;

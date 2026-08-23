import { useState } from 'react';
import ProcedureCostAnalysis from './components/ProcedureCostAnalysis';
import GeneralCostAnalysis from './components/GeneralCostAnalysis';
import AnalyticsExportButton from './components/AnalyticsExportButton';
import DoctorPerformanceTab from './components/DoctorPerformanceTab';
import OverviewPage from '@/features/finance/pages/OverviewPage';
import DateRangePicker from '@/features/finance/components/DateRangePicker';
import { PieChart, Activity, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/**
 * Legacy Analytics workspace.
 *
 * The financial headline tab deliberately consumes the canonical Finance V2
 * Overview rather than `/metrics/profitability`. Unique procedure/provider
 * analytics remain here until the navigation/redirect phase moves them to
 * their final destinations.
 */
const SmartDashboard = () => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [activeTab, setActiveTab] = useState('financials');

    return (
        <div className="p-4 md:p-8 space-y-6 max-w-[1920px] mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                <div>
                    <h1 className="text-3xl font-bold text-slate-800 dark:text-white tracking-tight">
                        {t('analytics.dashboard.title')}
                    </h1>
                    <p className="text-slate-500 mt-1 font-medium">
                        {t('analytics.dashboard.subtitle')}
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                    {activeTab === 'financials' && <DateRangePicker />}
                    {activeTab === 'procedures' && <AnalyticsExportButton />}
                </div>
            </div>

            <div className="border-b border-slate-200 dark:border-slate-700 mb-6">
                <div className="flex space-x-8 rtl:space-x-reverse overflow-x-auto">
                    <button
                        type="button"
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
                        type="button"
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
                        type="button"
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

            {activeTab === 'financials' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-end-4 duration-300">
                    <OverviewPage />
                </div>
            )}

            {activeTab === 'procedures' && (
                <div className="space-y-8 animate-in fade-in slide-in-from-end-4 duration-300">
                    <GeneralCostAnalysis />
                    <div className="border-t border-slate-200 dark:border-slate-700 my-8"></div>
                    <div className="bg-slate-50 dark:bg-slate-900/50 p-6 rounded-3xl border border-dashed border-slate-200 dark:border-slate-800">
                        <div className="mb-4">
                            <h3 className="text-lg font-bold text-slate-700 dark:text-slate-300">
                                {t('analytics.general_analysis.table.title')}
                            </h3>
                            <p className="text-sm text-slate-500">
                                {t('analytics.general_analysis.table.subtitle')}
                            </p>
                        </div>
                        <ProcedureCostAnalysis />
                    </div>
                </div>
            )}

            {activeTab === 'doctors' && (
                <div className="space-y-8 animate-in fade-in slide-in-from-end-4 duration-300">
                    <DoctorPerformanceTab />
                </div>
            )}
        </div>
    );
};

export default SmartDashboard;

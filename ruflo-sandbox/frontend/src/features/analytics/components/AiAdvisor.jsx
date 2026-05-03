import { useState } from 'react';
import { Sparkles, Brain, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { analyzeClinic } from '@/api/analytics';
import { toast } from '@/shared/ui';
const AiAdvisor = ({ stats }) => {
    const { t } = useTranslation();
    const [insights, setInsights] = useState(null);
    const [loading, setLoading] = useState(false);
    const handleAnalyze = async () => {
        if (!stats) return;
        setLoading(true);
        try {
            const data = await analyzeClinic(stats);
            setInsights(data.insights);
        } catch (err) {
            console.error(err);
            toast.error(t('analytics.advisor.error') + ' ' + (err.response?.data?.message || err.message));
        } finally {
            setLoading(false);
        }
    };
    return (
        <div className="bg-gradient-to-br from-indigo-50/50 to-teal-50/50 backdrop-blur-sm p-6 rounded-2xl border border-indigo-100/50 shadow-sm relative overflow-hidden h-full min-h-[400px]">
            {/* Header */}
            <div className="flex justify-between items-center mb-6 relative z-10">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-indigo-600 rounded-xl text-white shadow-lg shadow-indigo-200">
                        <Brain size={24} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-indigo-900">{t('analytics.advisor.title')}</h3>
                        <p className="text-xs text-indigo-500 font-medium">{t('analytics.advisor.subtitle')}</p>
                    </div>
                </div>
                <button
                    onClick={handleAnalyze}
                    disabled={loading || !stats}
                    className="flex items-center gap-2 text-sm font-bold text-indigo-600 hover:bg-white/80 bg-white/40 px-4 py-2 rounded-xl transition-all active:scale-95 disabled:opacity-50 border border-indigo-100"
                >
                    {loading ? <RefreshCw className="animate-spin" size={16} /> : <Sparkles size={16} />}
                    {insights ? t('analytics.advisor.refresh') : t('analytics.advisor.start')}
                </button>
            </div>
            {/* Content */}
            <div className="relative z-10">
                {loading ? (
                    <div className="space-y-4 animate-pulse py-4">
                        <div className="h-4 bg-indigo-200/50 rounded-lg w-3/4"></div>
                        <div className="h-4 bg-indigo-200/50 rounded-lg w-1/2"></div>
                        <div className="h-4 bg-indigo-200/50 rounded-lg w-5/6"></div>
                        <div className="h-4 bg-indigo-200/50 rounded-lg w-2/3"></div>
                    </div>
                ) : insights ? (
                    <div className="prose prose-sm prose-indigo max-w-none text-indigo-900 leading-loose font-medium bg-white/60 p-5 rounded-2xl border border-indigo-50/50 shadow-sm whitespace-pre-line">
                        {insights}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center text-indigo-400 py-20 border-2 border-dashed border-indigo-200/50 rounded-2xl bg-white/20">
                        <Sparkles size={48} className="mb-4 opacity-50 text-indigo-300" />
                        <p className="text-base font-medium text-indigo-800">{t('analytics.advisor.ready_title')}</p>
                        <p className="text-xs text-indigo-500 mt-2 max-w-[200px] text-center">{t('analytics.advisor.ready_desc')}</p>
                    </div>
                )}
            </div>
            {/* Background Decoration */}
            <div className="absolute top-0 right-0 -mt-20 -mr-20 w-64 h-64 bg-teal-200 rounded-full blur-3xl opacity-20 pointer-events-none"></div>
            <div className="absolute bottom-0 left-0 -mb-20 -ml-20 w-64 h-64 bg-indigo-200 rounded-full blur-3xl opacity-20 pointer-events-none"></div>
        </div>
    );
};
export default AiAdvisor;


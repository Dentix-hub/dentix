import { useState } from 'react';
import logger from '@/utils/logger';
import { Sparkles, RefreshCw, Bot } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { analyzeClinic } from '@/api/analytics';
import { toast } from '@/shared/ui';
import InsightCard from './InsightCard';
import { useNavigate } from 'react-router-dom';

export default function AiAdvisor({ stats }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const navigate = useNavigate();

    const [insights, setInsights] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleAnalyze = async () => {
        if (!stats) return;
        setLoading(true);
        try {
            const data = await analyzeClinic(stats);
            setInsights(data.insights);
        } catch (err) {
            logger.error(err);
            toast.error(t('analytics.advisor.error') + ' ' + (err.response?.data?.message || err.message));
        } finally {
            setLoading(false);
        }
    };

    // Default proactive sample cards before user clicks analyze
    const defaultProactiveCards = [
        {
            type: 'alert',
            title: isRtl ? 'ارتفاع تكلفة معمل تركيبة الزيركون' : 'Zirconia Lab Cost Spike',
            body: isRtl ? 'ارتفعت تكلفة تركيبة الزيركون بنسبة 20% لدى "معمل الأمل" مقارنة بمتوسط التكلفة المعيارية.' : 'Zirconia crown lab cost increased by 20% compared to standard market benchmark.',
            actionLabel: isRtl ? 'عرض فواتير المعامل' : 'View Lab Orders',
            onAction: () => navigate('/labs')
        },
        {
            type: 'opportunity',
            title: isRtl ? 'فرصة متابعة مرضى الحشو والتقويم' : 'Patient Follow-up Opportunity',
            body: isRtl ? 'يوجد 14 مريضاً أكملوا علاج اللثة دون جدولة موعد المتابعة الدوري الموصى به.' : '14 patients completed periodontal treatment without booking recommended recall.',
            actionLabel: isRtl ? 'عرض قائمة المواعيد' : 'View Appointments',
            onAction: () => navigate('/appointments')
        },
        {
            type: 'improvement',
            title: isRtl ? 'توصية بتعديل سعر خلع الضرس' : 'Extraction Price Recommendation',
            body: isRtl ? 'هامش ربح خلع الضرس المركب انخفض بسبب تضخم تكلفة المواد والتخدير.' : 'Complex extraction margin dropped due to inflated anesthesia and suture costs.',
            actionLabel: isRtl ? 'مراجعة لائحة الأسعار' : 'Review Price Lists',
            onAction: () => navigate('/settings/price-lists')
        }
    ];

    return (
        <div className="bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-slate-900/80 backdrop-blur-md p-6 rounded-3xl border border-indigo-500/20 shadow-lg relative overflow-hidden h-full min-h-[420px] flex flex-col justify-between">
            <div>
                {/* Header */}
                <div className="flex justify-between items-center mb-5 relative z-10">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-indigo-600/30 text-indigo-400 rounded-2xl border border-indigo-500/30 shadow-lg shadow-indigo-600/20">
                            <Bot size={22} className="animate-pulse" />
                        </div>
                        <div>
                            <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                                {t('analytics.advisor.title')}
                                <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full border border-indigo-400/30">AI Copilot</span>
                            </h3>
                            <p className="text-xs text-indigo-300/80 font-medium">{t('analytics.advisor.subtitle')}</p>
                        </div>
                    </div>
                    <button
                        onClick={handleAnalyze}
                        disabled={loading || !stats}
                        className="flex items-center gap-2 text-xs font-bold text-indigo-300 hover:bg-indigo-500/20 bg-indigo-500/10 px-3.5 py-2 rounded-xl transition-all active:scale-95 disabled:opacity-50 border border-indigo-500/20"
                    >
                        {loading ? <RefreshCw className="animate-spin" size={14} /> : <Sparkles size={14} />}
                        {insights ? t('analytics.advisor.refresh') : t('analytics.advisor.start')}
                    </button>
                </div>

                {/* Content Area */}
                <div className="relative z-10 space-y-3">
                    {loading ? (
                        <div className="space-y-3 animate-pulse py-4">
                            <div className="h-20 bg-indigo-500/10 rounded-2xl border border-indigo-500/20"></div>
                            <div className="h-20 bg-indigo-500/10 rounded-2xl border border-indigo-500/20"></div>
                            <div className="h-20 bg-indigo-500/10 rounded-2xl border border-indigo-500/20"></div>
                        </div>
                    ) : insights ? (
                        <div className="prose prose-sm max-w-none text-slate-200 leading-relaxed font-medium bg-slate-900/60 p-5 rounded-2xl border border-indigo-500/20 shadow-inner whitespace-pre-line text-xs max-h-[320px] overflow-y-auto custom-scrollbar">
                            {insights}
                        </div>
                    ) : (
                        <div className="space-y-3 max-h-[330px] overflow-y-auto custom-scrollbar pr-1">
                            {defaultProactiveCards.map((card, idx) => (
                                <InsightCard
                                    key={idx}
                                    type={card.type}
                                    title={card.title}
                                    body={card.body}
                                    actionLabel={card.actionLabel}
                                    onAction={card.onAction}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Background Glow Effects */}
            <div className="absolute top-0 end-0 -mt-20 -me-20 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div className="absolute bottom-0 start-0 -mb-20 -ms-20 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl pointer-events-none"></div>
        </div>
    );
}

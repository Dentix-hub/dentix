import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Calendar } from 'lucide-react';

export default function AnalyticsDatePicker({ period, setPeriod, customStartDate, setCustomStartDate, customEndDate, setCustomEndDate }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [showCustom, setShowCustom] = useState(period === 'custom');

    const handlePresetClick = (p) => {
        setShowCustom(false);
        setPeriod(p);
    };

    const handleCustomClick = () => {
        setShowCustom(true);
        setPeriod('custom');
    };

    return (
        <div className="flex flex-wrap items-center gap-2">
            <div className="flex bg-surface rounded-xl p-1 border border-border/50 shadow-sm">
                <button
                    onClick={() => handlePresetClick('7d')}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        period === '7d'
                            ? 'bg-primary text-white shadow-sm'
                            : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                    }`}
                >
                    {t('analytics.dashboard.periods.week')}
                </button>
                <button
                    onClick={() => handlePresetClick('30d')}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        period === '30d'
                            ? 'bg-primary text-white shadow-sm'
                            : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                    }`}
                >
                    {t('analytics.dashboard.periods.month')}
                </button>
                <button
                    onClick={() => handlePresetClick('90d')}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        period === '90d'
                            ? 'bg-primary text-white shadow-sm'
                            : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                    }`}
                >
                    {t('analytics.dashboard.periods.three_months')}
                </button>
                <button
                    onClick={handleCustomClick}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1 ${
                        period === 'custom' || showCustom
                            ? 'bg-primary text-white shadow-sm'
                            : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                    }`}
                >
                    <Calendar size={13} />
                    <span>{isRtl ? 'مخصص' : 'Custom'}</span>
                </button>
            </div>

            {showCustom && (
                <div className="flex items-center gap-2 bg-surface p-1 rounded-xl border border-border/50 shadow-sm animate-in fade-in zoom-in-95 duration-200">
                    <input
                        type="date"
                        value={customStartDate || ''}
                        onChange={(e) => setCustomStartDate(e.target.value)}
                        className="bg-surface-hover text-text-primary text-xs px-2.5 py-1 rounded-lg border border-border/50 outline-none focus:border-primary font-mono"
                    />
                    <span className="text-xs text-text-tertiary font-bold">{isRtl ? 'إلى' : 'to'}</span>
                    <input
                        type="date"
                        value={customEndDate || ''}
                        onChange={(e) => setCustomEndDate(e.target.value)}
                        className="bg-surface-hover text-text-primary text-xs px-2.5 py-1 rounded-lg border border-border/50 outline-none focus:border-primary font-mono"
                    />
                </div>
            )}
        </div>
    );
}

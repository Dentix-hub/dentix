import { AlertTriangle, Sparkles, TrendingUp, ShieldAlert, ChevronLeft, ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const TYPE_STYLES = {
    alert: {
        bg: 'bg-amber-500/10 border-amber-500/20 text-amber-900 dark:text-amber-200',
        titleColor: 'text-amber-600 dark:text-amber-400',
        btnBg: 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-700 dark:text-amber-300 border-amber-500/30',
        icon: AlertTriangle,
    },
    opportunity: {
        bg: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-900 dark:text-emerald-200',
        titleColor: 'text-emerald-600 dark:text-emerald-400',
        btnBg: 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
        icon: Sparkles,
    },
    improvement: {
        bg: 'bg-sky-500/10 border-sky-500/20 text-sky-900 dark:text-sky-200',
        titleColor: 'text-sky-600 dark:text-sky-400',
        btnBg: 'bg-sky-500/20 hover:bg-sky-500/30 text-sky-700 dark:text-sky-300 border-sky-500/30',
        icon: TrendingUp,
    },
    risk: {
        bg: 'bg-rose-500/10 border-rose-500/20 text-rose-900 dark:text-rose-200',
        titleColor: 'text-rose-600 dark:text-rose-400',
        btnBg: 'bg-rose-500/20 hover:bg-rose-500/30 text-rose-700 dark:text-rose-300 border-rose-500/30',
        icon: ShieldAlert,
    },
};

export default function InsightCard({ type = 'opportunity', title, body, actionLabel, onAction }) {
    const { i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const style = TYPE_STYLES[type] || TYPE_STYLES.opportunity;
    const Icon = style.icon;

    return (
        <div className={`p-4 rounded-2xl border text-xs space-y-2.5 transition-all shadow-sm ${style.bg}`}>
            <div className="flex items-start justify-between gap-2">
                <div className={`flex items-center gap-1.5 font-extrabold ${style.titleColor}`}>
                    <Icon size={16} className="shrink-0" />
                    <span>{title}</span>
                </div>
            </div>
            <p className="text-[11px] leading-relaxed opacity-90 font-medium">
                {body}
            </p>
            {actionLabel && (
                <button
                    onClick={onAction}
                    className={`w-full text-center py-1.5 px-3 font-bold rounded-xl border transition-all text-xs flex items-center justify-center gap-1 active:scale-95 ${style.btnBg}`}
                >
                    <span>{actionLabel}</span>
                    {isRtl ? <ChevronLeft size={13} /> : <ChevronRight size={13} />}
                </button>
            )}
        </div>
    );
}

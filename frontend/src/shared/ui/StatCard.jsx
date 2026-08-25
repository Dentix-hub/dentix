import { isValidElement } from 'react';

const colorMap = {
    indigo: {
        accentBg: 'bg-indigo-50 dark:bg-indigo-900/20',
        subtextBg: 'bg-indigo-50 dark:bg-indigo-900/30',
        subtextColor: 'text-indigo-600 dark:text-indigo-400',
        iconBg: 'bg-indigo-100 dark:bg-indigo-900/50',
        iconColor: 'text-indigo-600 dark:text-indigo-400'
    },
    emerald: {
        accentBg: 'bg-emerald-50 dark:bg-emerald-900/20',
        subtextBg: 'bg-emerald-50 dark:bg-emerald-900/30',
        subtextColor: 'text-emerald-600 dark:text-emerald-400',
        iconBg: 'bg-emerald-100 dark:bg-emerald-900/50',
        iconColor: 'text-emerald-600 dark:text-emerald-400'
    },
    amber: {
        accentBg: 'bg-amber-50 dark:bg-amber-900/20',
        subtextBg: 'bg-amber-50 dark:bg-amber-900/30',
        subtextColor: 'text-amber-600 dark:text-amber-400',
        iconBg: 'bg-amber-100 dark:bg-amber-900/50',
        iconColor: 'text-amber-600 dark:text-amber-400'
    },
    blue: {
        accentBg: 'bg-blue-50 dark:bg-blue-900/20',
        subtextBg: 'bg-blue-50 dark:bg-blue-900/30',
        subtextColor: 'text-blue-600 dark:text-blue-400',
        iconBg: 'bg-blue-100 dark:bg-blue-900/50',
        iconColor: 'text-blue-600 dark:text-blue-400'
    },
    teal: {
        accentBg: 'bg-teal-50 dark:bg-teal-900/20',
        subtextBg: 'bg-teal-50 dark:bg-teal-900/30',
        subtextColor: 'text-teal-600 dark:text-teal-400',
        iconBg: 'bg-teal-100 dark:bg-teal-900/50',
        iconColor: 'text-teal-600 dark:text-teal-400'
    },
    red: {
        accentBg: 'bg-red-50 dark:bg-red-900/20',
        subtextBg: 'bg-red-50 dark:bg-red-900/30',
        subtextColor: 'text-red-600 dark:text-red-400',
        iconBg: 'bg-red-100 dark:bg-red-900/50',
        iconColor: 'text-red-600 dark:text-red-400'
    },
    rose: {
        accentBg: 'bg-rose-50 dark:bg-rose-900/20',
        subtextBg: 'bg-rose-50 dark:bg-rose-900/30',
        subtextColor: 'text-rose-600 dark:text-rose-400',
        iconBg: 'bg-rose-100 dark:bg-rose-900/50',
        iconColor: 'text-rose-600 dark:text-rose-400'
    },
};

const StatCard = ({ icon: Icon, title, value, subtext, label, color = "indigo", onClick }) => {
    const styles = colorMap[color] || colorMap.indigo;
    
    return (
        <div
            onClick={(e) => {
                if (onClick) {
                    onClick(e);
                }
            }}
            className={`relative overflow-hidden bg-surface dark:bg-surface/50 p-6 rounded-2xl border border-border shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group ${onClick ? 'cursor-pointer active:scale-95' : ''}`}
        >
            <div className={`absolute top-0 end-0 w-32 h-32 ${styles.accentBg} rounded-bl-[100px] transition-all group-hover:scale-110 pointer-events-none`} />
            <div className="relative z-10 flex justify-between items-start">
                <div>
                    <h3 className="text-slate-500 dark:text-slate-400 text-sm font-semibold mb-1">{title || label}</h3>
                    <p className={`text-3xl font-extrabold text-slate-800 dark:text-white mb-2`}>{value}</p>
                    {subtext && <p className={`text-xs font-medium px-2 py-1 rounded-full ${styles.subtextBg} ${styles.subtextColor} inline-block`}>{subtext}</p>}
                </div>
                <div className={`p-3 ${styles.iconBg} ${styles.iconColor} rounded-2xl group-hover:rotate-12 transition-transform`}>
                    {isValidElement(Icon) ? (
                        Icon
                    ) : (
                        <Icon size={28} strokeWidth={2} />
                    )}
                </div>
            </div>
        </div>
    );
};

export default StatCard;

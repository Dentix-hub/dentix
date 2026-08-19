import { Activity, CalendarDays, FileText, FlaskConical, FolderOpen, WalletCards } from 'lucide-react';
import { motion } from '@/lib/motion';

const LEGACY_ICON_MAP = {
    '🦷': Activity,
    '📅': CalendarDays,
    '📝': FileText,
    '💰': WalletCards,
    '📁': FolderOpen,
    '🔬': FlaskConical,
};

function resolveIcon(icon) {
    if (typeof icon === 'string') return LEGACY_ICON_MAP[icon] || null;
    return icon || null;
}

function selectTab(event, id, onChange) {
    event.currentTarget.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
    onChange(id);
}

export default function TabGroup({ tabs, activeTab, onChange, variant = 'pill', className = '' }) {
    if (variant === 'underline') {
        return (
            <div
                role="tablist"
                className={`scrollbar-none relative flex min-w-0 flex-nowrap overflow-x-auto overscroll-x-contain border-b border-slate-200 dark:border-slate-700/50 ${className}`}
            >
                {tabs.map((tab) => {
                    const isActive = activeTab === tab.id;
                    const Icon = resolveIcon(tab.icon);
                    return (
                        <button
                            key={tab.id}
                            type="button"
                            role="tab"
                            aria-selected={isActive}
                            onClick={(event) => selectTab(event, tab.id, onChange)}
                            className={`relative -mb-[2px] inline-flex min-h-11 shrink-0 items-center gap-2 whitespace-nowrap px-3 py-2.5 text-sm font-bold transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 focus:ring-inset sm:px-5 sm:py-3 lg:px-6 ${isActive ? 'text-primary' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'}`}
                        >
                            {Icon && <Icon size={18} className="shrink-0" aria-hidden="true" />}
                            <span>{tab.label}</span>
                            {isActive && (
                                <motion.div
                                    layoutId="tab-underline"
                                    className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-primary"
                                    transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                                />
                            )}
                        </button>
                    );
                })}
            </div>
        );
    }

    if (variant === 'vertical') {
        return (
            <nav role="tablist" className={`space-y-1 ${className}`}>
                {tabs.map((tab) => {
                    const isActive = activeTab === tab.id;
                    const Icon = resolveIcon(tab.icon);
                    return (
                        <button
                            key={tab.id}
                            type="button"
                            role="tab"
                            aria-selected={isActive}
                            onClick={(event) => selectTab(event, tab.id, onChange)}
                            className={`relative flex min-h-11 w-full items-center gap-3 rounded-xl px-4 py-3 font-bold transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary/30 ${isActive ? 'text-white' : 'text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-700/50'}`}
                        >
                            {isActive && (
                                <motion.div
                                    layoutId="tab-vertical-pill"
                                    className="absolute inset-0 rounded-xl bg-primary shadow-lg shadow-primary/30"
                                    transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                                />
                            )}
                            <span className="relative z-10 flex min-w-0 items-center gap-3">
                                {Icon && <Icon size={20} aria-hidden="true" className={`shrink-0 ${isActive ? 'text-white' : 'text-slate-500 dark:text-slate-500'}`} />}
                                <span className="min-w-0 break-words text-start">{tab.label}</span>
                            </span>
                        </button>
                    );
                })}
            </nav>
        );
    }

    return (
        <div
            role="tablist"
            className={`scrollbar-none flex min-w-0 flex-nowrap gap-2 overflow-x-auto overscroll-x-contain rounded-2xl border border-slate-100 bg-surface p-1.5 dark:border-slate-700/50 sm:p-2 ${className}`}
        >
            {tabs.map((tab) => {
                const isActive = activeTab === tab.id;
                const Icon = resolveIcon(tab.icon);
                return (
                    <button
                        key={tab.id}
                        type="button"
                        role="tab"
                        aria-selected={isActive}
                        onClick={(event) => selectTab(event, tab.id, onChange)}
                        className={`relative inline-flex min-h-11 shrink-0 items-center gap-2 whitespace-nowrap rounded-xl px-3 py-2 text-sm font-bold transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 sm:px-4 ${isActive ? 'text-white' : 'text-slate-600 hover:bg-slate-200/50 dark:text-slate-400 dark:hover:bg-slate-700/50'}`}
                    >
                        {isActive && (
                            <motion.div
                                layoutId="tab-pill"
                                className="absolute inset-0 rounded-xl bg-primary shadow"
                                transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                            />
                        )}
                        <span className="relative z-10 flex items-center gap-2">
                            {Icon && <Icon size={16} className="shrink-0" aria-hidden="true" />}
                            <span>{tab.label}</span>
                        </span>
                    </button>
                );
            })}
        </div>
    );
}

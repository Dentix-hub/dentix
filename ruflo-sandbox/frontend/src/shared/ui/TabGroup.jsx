import React from 'react';

export default function TabGroup({ tabs, activeTab, onChange, variant = 'pill', className = '' }) {
    if (variant === 'underline') {
        return (
            <div className={`flex flex-wrap border-b border-slate-200 dark:border-slate-700/50 ${className}`}>
                {tabs.map((t) => {
                    const isActive = activeTab === t.id;
                    const Icon = t.icon;
                    return (
                        <button
                            key={t.id}
                            onClick={() => onChange(t.id)}
                            className={`px-6 py-3 text-sm font-bold flex items-center gap-2 transition-all border-b-2 -mb-[2px] ${
                                isActive
                                    ? 'border-primary text-primary'
                                    : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'
                            }`}
                        >
                            {Icon && <Icon size={18} />}
                            {t.label}
                        </button>
                    );
                })}
            </div>
        );
    }

    if (variant === 'vertical') {
        return (
            <nav className={`space-y-1 ${className}`}>
                {tabs.map((tab) => {
                    const isActive = activeTab === tab.id;
                    const Icon = tab.icon;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => onChange(tab.id)}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-bold ${
                                isActive
                                    ? 'bg-primary text-white shadow-lg shadow-primary/30'
                                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                            }`}
                        >
                            {Icon && <Icon size={20} className={isActive ? 'text-white' : 'text-slate-400 dark:text-slate-500'} />}
                            <span>{tab.label}</span>
                        </button>
                    );
                })}
            </nav>
        );
    }

    // Default: 'pill' variant
    return (
        <div className={`bg-surface rounded-2xl border border-slate-100 dark:border-slate-700/50 p-2 flex flex-wrap gap-2 ${className}`}>
            {tabs.map((t) => {
                const isActive = activeTab === t.id;
                const Icon = t.icon;
                return (
                    <button
                        key={t.id}
                        onClick={() => onChange(t.id)}
                        className={`px-4 py-2 flex items-center gap-2 rounded-xl text-sm font-bold transition-all ${
                            isActive
                                ? 'bg-primary text-white shadow'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                        }`}
                    >
                        {Icon && <Icon size={16} />}
                        {t.label}
                    </button>
                );
            })}
        </div>
    );
}

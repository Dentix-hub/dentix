import { motion } from '@/lib/motion';

export default function TabGroup({ tabs, activeTab, onChange, variant = 'pill', className = '' }) {
    if (variant === 'underline') {
        return (
            <div className={`flex flex-wrap border-b border-slate-200 dark:border-slate-700/50 relative ${className}`}>
                {tabs.map((t) => {
                    const isActive = activeTab === t.id;
                    const Icon = t.icon;
                    return (
                        <button
                            key={t.id}
                            onClick={() => onChange(t.id)}
                            className={`relative px-6 py-3 text-sm font-bold flex items-center gap-2 transition-colors -mb-[2px] ${
                                isActive
                                    ? 'text-primary'
                                    : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'
                            }`}
                        >
                            {Icon && <Icon size={18} />}
                            {t.label}
                            {isActive && (
                                <motion.div
                                    layoutId="tab-underline"
                                    className="absolute bottom-0 start-0 end-0 h-0.5 bg-primary rounded-full"
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
            <nav className={`space-y-1 ${className}`}>
                {tabs.map((tab) => {
                    const isActive = activeTab === tab.id;
                    const Icon = tab.icon;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => onChange(tab.id)}
                            className={`relative w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-colors duration-200 font-bold ${
                                isActive
                                    ? 'text-white'
                                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                            }`}
                        >
                            {isActive && (
                                <motion.div
                                    layoutId="tab-vertical-pill"
                                    className="absolute inset-0 bg-primary rounded-xl shadow-lg shadow-primary/30"
                                    transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                                />
                            )}
                            <span className="relative z-10 flex items-center gap-3">
                                {Icon && <Icon size={20} className={isActive ? 'text-white' : 'text-slate-500 dark:text-slate-500'} />}
                                <span>{tab.label}</span>
                            </span>
                        </button>
                    );
                })}
            </nav>
        );
    }

    // Default: 'pill' variant — with sliding animated pill
    return (
        <div className={`bg-surface rounded-2xl border border-slate-100 dark:border-slate-700/50 p-2 flex flex-wrap gap-2 ${className}`}>
            {tabs.map((t) => {
                const isActive = activeTab === t.id;
                const Icon = t.icon;
                return (
                    <button
                        key={t.id}
                        onClick={() => onChange(t.id)}
                        className={`relative px-4 py-2 flex items-center gap-2 rounded-xl text-sm font-bold transition-colors ${
                            isActive
                                ? 'text-white'
                                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-200/50 dark:hover:bg-slate-700/50'
                        }`}
                    >
                        {isActive && (
                            <motion.div
                                layoutId="tab-pill"
                                className="absolute inset-0 bg-primary rounded-xl shadow"
                                transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                            />
                        )}
                        <span className="relative z-10 flex items-center gap-2">
                            {Icon && <Icon size={16} />}
                            {t.label}
                        </span>
                    </button>
                );
            })}
        </div>
    );
}

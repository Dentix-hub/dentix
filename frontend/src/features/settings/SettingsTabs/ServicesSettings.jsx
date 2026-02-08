import React, { useState } from 'react';
import { List, Banknote, Shield } from 'lucide-react';
import ProceduresSettings from './ProceduresSettings';
import PriceLists from '@/pages/admin/PriceLists';
import InsuranceProviders from '@/pages/admin/InsuranceProviders';
import { useTranslation } from 'react-i18next';

export default function ServicesSettings({ setMessage }) {
    const { t } = useTranslation();
    const [activeSubTab, setActiveSubTab] = useState('procedures');

    const subTabs = [
        { id: 'procedures', label: t('settings.services.tabs.procedures'), icon: List },
        { id: 'price-lists', label: t('settings.services.tabs.price_lists'), icon: Banknote },
        { id: 'insurance', label: t('settings.services.tabs.insurance'), icon: Shield },
    ];

    return (
        <div className="space-y-6">
            {/* Sub-Tab Navigation */}
            <div className="flex flex-wrap items-center gap-2 bg-slate-50 dark:bg-slate-800/50 p-1.5 rounded-xl border border-slate-100 dark:border-white/5 w-fit">
                {subTabs.map(tab => {
                    const Icon = tab.icon;
                    const isActive = activeSubTab === tab.id;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveSubTab(tab.id)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all duration-200 ${isActive
                                ? 'bg-white dark:bg-slate-800 text-indigo-600 shadow-sm border border-slate-200 dark:border-slate-700'
                                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-700/50'
                                }`}
                        >
                            <Icon size={16} />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Content Area */}
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                {activeSubTab === 'procedures' && (
                    <ProceduresSettings setMessage={setMessage} />
                )}

                {activeSubTab === 'price-lists' && (
                    <PriceLists />
                )}

                {activeSubTab === 'insurance' && (
                    <InsuranceProviders />
                )}
            </div>
        </div>
    );
}

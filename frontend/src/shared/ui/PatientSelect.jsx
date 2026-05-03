import React, { useState } from 'react';
import { Combobox, ComboboxInput, ComboboxOptions, ComboboxOption, Transition } from '@headlessui/react';
import { Search, User, Check, ChevronDown, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Fragment } from 'react';

export default function PatientSelect({ patients = [], value, onChange, onQuickAdd, label, placeholder, error, required }) {
    const { t } = useTranslation();
    const [query, setQuery] = useState('');

    const filteredPatients =
        query === ''
            ? [...patients].sort((a, b) => (b.id || 0) - (a.id || 0)).slice(0, 50)
            : patients
                .filter((patient) => {
                    return (
                        patient.name?.toLowerCase().includes(query.toLowerCase()) || 
                        patient.phone?.includes(query)
                    );
                })
                .sort((a, b) => (b.id || 0) - (a.id || 0))
                .slice(0, 50);

    const selectedPatient = patients.find(p => p.id === parseInt(value)) || null;

    return (
        <div className="w-full space-y-1.5">
            {label && (
                <label className="block text-sm font-bold text-text-primary">
                    {label}
                    {required && <span className="text-red-500 ml-1">*</span>}
                </label>
            )}
            <Combobox 
                value={selectedPatient} 
                onChange={(p) => onChange({ target: { value: p?.id || '' } })}
                onClose={() => setQuery('')}
            >
                <div className="relative mt-1">
                    <div className={`relative w-full cursor-default overflow-hidden rounded-xl bg-surface border ${error ? 'border-red-300' : 'border-border'} text-left focus:outline-none focus-within:ring-2 focus-within:ring-primary/20 sm:text-sm transition-all shadow-sm`}>
                        <ComboboxInput
                            className="w-full border-none py-3 pl-10 pr-10 text-sm font-bold leading-5 text-text-primary focus:ring-0 bg-transparent outline-none placeholder:text-slate-400"
                            displayValue={(patient) => patient?.name || ''}
                            onChange={(event) => setQuery(event.target.value)}
                            onFocus={(e) => {
                                // Trigger opening when focused
                                if (!query) e.target.click();
                            }}
                            placeholder={placeholder || t('common.search_patient', 'Search patient...')}
                        />
                        <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                            <Search className="h-4 w-4 text-slate-400" aria-hidden="true" />
                        </div>
                        <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                            <ChevronDown className="h-4 w-4 text-slate-400" aria-hidden="true" />
                        </div>
                    </div>
                    <Transition
                        as={Fragment}
                        leave="transition ease-in duration-100"
                        leaveFrom="opacity-100"
                        leaveTo="opacity-0"
                        afterLeave={() => setQuery('')}
                    >
                        <ComboboxOptions className="absolute mt-1 max-h-60 w-full overflow-auto rounded-xl bg-white dark:bg-slate-900 py-2 text-base shadow-2xl ring-1 ring-black/5 focus:outline-none sm:text-sm z-[100] border border-border/50 backdrop-blur-xl">
                            {filteredPatients.length === 0 && query !== '' ? (
                                <div className="relative cursor-default select-none py-6 px-4 text-slate-500 italic text-center text-xs font-bold">
                                    {t('common.no_results', 'No results found')}
                                </div>
                            ) : (
                                filteredPatients.map((patient) => (
                                    <ComboboxOption
                                        key={patient.id}
                                        className={({ active }) =>
                                            `relative cursor-default select-none py-3 pl-10 pr-4 transition-all mx-2 rounded-xl mb-1 ${
                                                active ? 'bg-primary text-white shadow-lg shadow-primary/20 scale-[1.02]' : 'text-text-primary hover:bg-slate-50 dark:hover:bg-slate-800'
                                            }`
                                        }
                                        value={patient}
                                    >
                                        {({ selected, active }) => (
                                            <>
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-black text-[10px] transition-colors ${active ? 'bg-white/20 text-white' : 'bg-primary/10 text-primary'}`}>
                                                        {patient.name?.charAt(0).toUpperCase() || '?'}
                                                    </div>
                                                    <div className="flex flex-col min-w-0">
                                                        <span className={`block truncate text-sm ${selected ? 'font-black' : 'font-bold'}`}>
                                                            {patient.name}
                                                        </span>
                                                        {patient.phone && (
                                                            <span className={`text-[10px] font-bold uppercase tracking-widest ${active ? 'text-white/70' : 'text-slate-400'}`}>
                                                                {patient.phone}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                {selected ? (
                                                    <span className={`absolute inset-y-0 left-0 flex items-center pl-3 ${active ? 'text-white' : 'text-primary'}`}>
                                                        <Check className="h-4 w-4" aria-hidden="true" />
                                                    </span>
                                                ) : null}
                                            </>
                                        )}
                                    </ComboboxOption>
                                ))
                            )}

                            {onQuickAdd && (
                                <div className="border-t border-border mt-2 pt-2 px-2 pb-1">
                                    <button
                                        type="button"
                                        onClick={() => onQuickAdd(query)}
                                        className="w-full flex items-center gap-3 px-3 py-3 text-sm font-bold text-primary hover:bg-primary/5 rounded-xl transition-all group text-start"
                                    >
                                        <div className="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center shadow-md shadow-primary/20 group-hover:scale-110 transition-transform">
                                            <Plus size={16} />
                                        </div>
                                        <span>{t('patients.add_new', 'Add New Patient')} {query ? `"${query}"` : ''}</span>
                                    </button>
                                </div>
                            )}
                        </ComboboxOptions>
                    </Transition>
                </div>
            </Combobox>
            {error && <p className="text-xs font-bold text-red-500 mt-1 animate-in fade-in slide-in-from-top-1">{error}</p>}
        </div>
    );
}

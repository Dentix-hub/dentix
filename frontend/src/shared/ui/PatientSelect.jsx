import { Fragment, useEffect, useMemo, useState } from 'react';
import { Combobox, ComboboxInput, ComboboxOptions, ComboboxOption, Transition } from '@headlessui/react';
import { Search, Check, ChevronDown, Plus, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useSearchPatients } from '@/hooks/usePatients';

export default function PatientSelect({ patients = [], value, onChange, onQuickAdd, label, placeholder, error, required }) {
    const { t } = useTranslation();
    const [query, setQuery] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');

    useEffect(() => {
        const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 250);
        return () => window.clearTimeout(timer);
    }, [query]);

    const remoteSearch = useSearchPatients(debouncedQuery);
    const remotePatients = remoteSearch.data || [];
    const localRecent = useMemo(
        () => [...patients].sort((a, b) => (b.id || 0) - (a.id || 0)).slice(0, 50),
        [patients],
    );
    const options = debouncedQuery.length >= 2 ? remotePatients : localRecent;
    const selectedPatient = patients.find((p) => p.id === Number.parseInt(value, 10))
        || remotePatients.find((p) => p.id === Number.parseInt(value, 10))
        || null;

    return (
        <div className="w-full space-y-1.5">
            {label && (
                <label className="block text-sm font-bold text-text-primary">
                    {label}{required && <span className="text-red-500 ms-1">*</span>}
                </label>
            )}
            <Combobox value={selectedPatient} onChange={(p) => onChange({ target: { value: p?.id || '' } })} onClose={() => setQuery('')}>
                <div className="relative mt-1">
                    <div className={`relative w-full overflow-hidden rounded-xl bg-surface border ${error ? 'border-red-300' : 'border-border'} focus-within:ring-2 focus-within:ring-primary/20 shadow-sm`}>
                        <ComboboxInput
                            className="w-full border-none py-3 ps-10 pe-10 text-sm font-bold text-text-primary focus:ring-0 bg-transparent outline-none placeholder:text-slate-500"
                            displayValue={(patient) => patient?.name || ''}
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder={placeholder || t('common.search_patient', 'Search patient...')}
                            dir="auto"
                        />
                        <div className="absolute inset-y-0 start-0 flex items-center ps-3 pointer-events-none"><Search className="h-4 w-4 text-slate-500" /></div>
                        <div className="absolute inset-y-0 end-0 flex items-center pe-3 pointer-events-none">
                            {remoteSearch.isFetching && debouncedQuery.length >= 2 ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : <ChevronDown className="h-4 w-4 text-slate-500" />}
                        </div>
                    </div>
                    <Transition as={Fragment} leave="transition ease-in duration-100" leaveFrom="opacity-100" leaveTo="opacity-0" afterLeave={() => setQuery('')}>
                        <ComboboxOptions className="absolute mt-1 max-h-64 w-full overflow-auto rounded-xl bg-white dark:bg-slate-900 py-2 text-base shadow-2xl ring-1 ring-black/5 focus:outline-none sm:text-sm z-[100] border border-border/50">
                            {options.length === 0 && debouncedQuery !== '' ? (
                                <div className="py-6 px-4 text-slate-500 italic text-center text-xs font-bold">{t('common.no_results', 'No results found')}</div>
                            ) : options.map((patient) => (
                                <ComboboxOption
                                    key={patient.id}
                                    className={({ focus }) => `relative cursor-default select-none py-3 ps-10 pe-4 mx-2 rounded-xl mb-1 ${focus ? 'bg-primary text-white' : 'text-text-primary hover:bg-slate-50 dark:hover:bg-slate-800'}`}
                                    value={patient}
                                >
                                    {({ selected, focus }) => (
                                        <>
                                            <div className="flex items-center gap-3">
                                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-[10px] ${focus ? 'bg-white/20 text-white' : 'bg-primary/10 text-primary'}`}>{patient.name?.charAt(0).toUpperCase() || '?'}</div>
                                                <div className="flex min-w-0 flex-1 flex-col">
                                                    <span className="truncate text-sm font-bold" dir="auto">{patient.name}</span>
                                                    <span className={`text-[10px] font-bold ${focus ? 'text-white/70' : 'text-slate-500'}`}>
                                                        <span dir="ltr">#{patient.file_number || patient.id}</span>{patient.phone ? <> · <span dir="ltr">{patient.phone}</span></> : null}
                                                    </span>
                                                </div>
                                            </div>
                                            {selected ? <span className={`absolute inset-y-0 start-0 flex items-center ps-3 ${focus ? 'text-white' : 'text-primary'}`}><Check className="h-4 w-4" /></span> : null}
                                        </>
                                    )}
                                </ComboboxOption>
                            ))}
                            {onQuickAdd && (
                                <div className="border-t border-border mt-2 pt-2 px-2 pb-1">
                                    <button type="button" onClick={() => onQuickAdd(query)} className="w-full flex items-center gap-3 px-3 py-3 text-sm font-bold text-primary hover:bg-primary/5 rounded-xl text-start">
                                        <div className="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center"><Plus size={16} /></div>
                                        <span>{t('patients.add_new', 'Add New Patient')} {query ? `"${query}"` : ''}</span>
                                    </button>
                                </div>
                            )}
                        </ComboboxOptions>
                    </Transition>
                </div>
            </Combobox>
            {error && <p className="text-xs font-bold text-red-500 mt-1">{error}</p>}
        </div>
    );
}

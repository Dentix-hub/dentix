import { useEffect, useRef, useState } from 'react';
import { Search, User, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useSearchPatients } from '@/hooks/usePatients';
import { useTenantStore } from '@/store/tenant.store';
import ClinicDateTime from '@/shared/ui/ClinicDateTime';

export default function GlobalSearch() {
    const { t } = useTranslation();
    const { tenant } = useTenantStore();
    const [query, setQuery] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const searchRef = useRef(null);

    useEffect(() => {
        const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 250);
        return () => window.clearTimeout(timer);
    }, [query]);

    const search = useSearchPatients(debouncedQuery);
    const results = search.data || [];

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (searchRef.current && !searchRef.current.contains(event.target)) setIsOpen(false);
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    useEffect(() => {
        setIsOpen(debouncedQuery.length >= 2);
    }, [debouncedQuery]);

    const clear = () => {
        setQuery('');
        setDebouncedQuery('');
        setIsOpen(false);
    };

    return (
        <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="relative min-w-0 flex-1" ref={searchRef}>
                <div className="relative">
                    <Search className="absolute end-4 top-3.5 text-slate-500" size={20} />
                    <input
                        type="search"
                        placeholder={t('common.search_patient', 'Search patient...')}
                        className="w-full ps-4 pe-12 py-3 bg-slate-100 dark:bg-slate-800 rounded-2xl border border-transparent focus:bg-white dark:focus:bg-slate-900 focus:border-primary/20 outline-none transition-all text-sm font-bold text-slate-700 dark:text-slate-200 shadow-sm"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onFocus={() => debouncedQuery.length >= 2 && setIsOpen(true)}
                        dir="auto"
                    />
                    {query && (
                        <button type="button" onClick={clear} className="absolute start-3 top-3.5 text-slate-500 hover:text-red-500 transition-colors" aria-label={t('common.clear', 'Clear')}>
                            <X size={18} />
                        </button>
                    )}
                </div>

                {isOpen && (
                    <div className="absolute top-full mt-2 w-full bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-slate-100 dark:border-white/5 overflow-hidden z-50">
                        {search.isFetching ? (
                            <div className="p-4 text-center text-slate-500 text-sm font-bold">{t('common.searching', 'Searching...')}</div>
                        ) : results.length > 0 ? (
                            <div className="max-h-[320px] overflow-y-auto custom-scrollbar">
                                {results.map((patient) => (
                                    <Link
                                        key={patient.id}
                                        to={`/patients/${patient.id}`}
                                        onClick={clear}
                                        className="p-4 hover:bg-slate-50 dark:hover:bg-white/5 flex items-center gap-4 transition-colors border-b border-slate-50 dark:border-white/5 last:border-0"
                                    >
                                        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-500 rounded-xl"><User size={20} /></div>
                                        <div className="min-w-0 flex-1">
                                            <p className="truncate font-bold text-slate-800 dark:text-white text-sm" dir="auto">{patient.name}</p>
                                            <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                                                <span dir="ltr">#{patient.file_number || patient.id}</span>
                                                {patient.age ? <span>{patient.age} {t('patients.years_short', 'y')}</span> : null}
                                                {patient.phone ? <span dir="ltr">{patient.phone}</span> : null}
                                            </div>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <div className="p-4 text-center text-slate-500 text-sm font-bold">{t('common.no_results', 'No results')}</div>
                        )}
                    </div>
                )}
            </div>
            <ClinicDateTime timeZone={tenant?.timezone} />
        </div>
    );
}

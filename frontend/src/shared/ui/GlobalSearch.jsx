import { useEffect, useRef, useState } from 'react';
import { Search, User, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useSearchPatients } from '@/hooks/usePatients';
import { useTenantStore } from '@/store/tenant.store';
import ClinicDateTime from '@/shared/ui/ClinicDateTime';
import DentixBottomSheet from '@/shared/ui/DentixBottomSheet';

export default function GlobalSearch() {
    const { t } = useTranslation();
    const { tenant } = useTenantStore();
    const [query, setQuery] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
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

    const closeMobileSearch = () => {
        clear();
        setMobileSearchOpen(false);
    };

    const renderSearchInput = ({ autoFocus = false } = {}) => (
        <div className="relative min-w-0">
            <Search className="pointer-events-none absolute end-4 top-1/2 -translate-y-1/2 text-slate-500" size={20} aria-hidden="true" />
            <input
                type="search"
                placeholder={t('common.search_patient', 'Search patient...')}
                className="min-h-11 w-full rounded-2xl border border-transparent bg-slate-100 py-3 ps-4 pe-12 text-sm font-bold text-slate-700 shadow-sm outline-none transition-all focus:border-primary/20 focus:bg-white focus:ring-2 focus:ring-primary/10 dark:bg-slate-800 dark:text-slate-200 dark:focus:bg-slate-900"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => debouncedQuery.length >= 2 && setIsOpen(true)}
                dir="auto"
                autoFocus={autoFocus}
                autoComplete="off"
            />
            {query && (
                <button
                    type="button"
                    onClick={clear}
                    className="absolute start-1 top-1/2 inline-flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-xl text-slate-500 transition-colors hover:bg-slate-200/70 hover:text-red-500 dark:hover:bg-slate-700"
                    aria-label={t('common.clear', 'Clear')}
                >
                    <X size={18} aria-hidden="true" />
                </button>
            )}
        </div>
    );

    const renderResults = ({ mobile = false } = {}) => {
        if (debouncedQuery.length < 2) {
            return mobile ? (
                <div className="px-2 py-8 text-center text-sm font-medium text-text-secondary">
                    {t('common.search_min_chars', 'Type at least 2 characters to search')}
                </div>
            ) : null;
        }

        if (search.isFetching) {
            return <div className="p-4 text-center text-sm font-bold text-slate-500">{t('common.searching', 'Searching...')}</div>;
        }

        if (results.length === 0) {
            return <div className="p-4 text-center text-sm font-bold text-slate-500">{t('common.no_results', 'No results')}</div>;
        }

        return (
            <div className={`${mobile ? 'max-h-[60dvh]' : 'max-h-[320px]'} overflow-y-auto overscroll-contain`}>
                {results.map((patient) => (
                    <Link
                        key={patient.id}
                        to={`/patients/${patient.id}`}
                        onClick={mobile ? closeMobileSearch : clear}
                        className="flex min-h-14 items-center gap-3 border-b border-slate-100 p-3 transition-colors last:border-0 hover:bg-slate-50 dark:border-white/5 dark:hover:bg-white/5 sm:gap-4 sm:p-4"
                    >
                        <div className="shrink-0 rounded-xl bg-blue-50 p-2 text-blue-500 dark:bg-blue-900/20"><User size={20} aria-hidden="true" /></div>
                        <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-bold text-slate-800 dark:text-white" dir="auto">{patient.name}</p>
                            <div className="mt-1 flex flex-wrap gap-x-2 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                                <span dir="ltr">#{patient.file_number || patient.id}</span>
                                {patient.age ? <span>{patient.age} {t('patients.years_short', 'y')}</span> : null}
                                {patient.phone ? <span dir="ltr">{patient.phone}</span> : null}
                            </div>
                        </div>
                    </Link>
                ))}
            </div>
        );
    };

    return (
        <div className="flex min-w-0 flex-1 items-center justify-end gap-2 sm:gap-3">
            <button
                type="button"
                onClick={() => setMobileSearchOpen(true)}
                className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-slate-600 transition-colors hover:bg-slate-100 hover:text-primary dark:text-slate-300 dark:hover:bg-slate-800 sm:hidden"
                aria-label={t('common.search_patient', 'Search patient')}
            >
                <Search size={21} aria-hidden="true" />
            </button>

            <div className="relative hidden min-w-0 flex-1 sm:block" ref={searchRef}>
                {renderSearchInput()}
                {isOpen && (
                    <div className="absolute top-full z-50 mt-2 w-full overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-xl dark:border-white/5 dark:bg-slate-800">
                        {renderResults()}
                    </div>
                )}
            </div>

            <div className="hidden shrink-0 xl:block">
                <ClinicDateTime timeZone={tenant?.timezone} />
            </div>

            <DentixBottomSheet
                open={mobileSearchOpen}
                onOpenChange={setMobileSearchOpen}
                title={t('common.search_patient', 'Search patient')}
                closeLabel={t('common.close', 'Close')}
            >
                <div className="space-y-3">
                    {renderSearchInput({ autoFocus: true })}
                    <div className="overflow-hidden rounded-2xl border border-border bg-surface-elevated">
                        {renderResults({ mobile: true })}
                    </div>
                </div>
            </DentixBottomSheet>
        </div>
    );
}

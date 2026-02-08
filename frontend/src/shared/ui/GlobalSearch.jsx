import React, { useState, useEffect, useRef } from 'react';
import { Search, User, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { searchPatients } from '@/api';

export default function GlobalSearch() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [isOpen, setIsOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const searchRef = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        // Close on click outside
        const handleClickOutside = (event) => {
            if (searchRef.current && !searchRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    useEffect(() => {
        const delayDebounceFn = setTimeout(async () => {
            if (query.trim().length > 1) {
                setLoading(true);
                try {
                    const res = await searchPatients(query);
                    setResults(res.data);
                    setIsOpen(true);
                } catch (err) {
                    console.error("Search Error", err);
                } finally {
                    setLoading(false);
                }
            } else {
                setResults([]);
                setIsOpen(false);
            }
        }, 300);

        return () => clearTimeout(delayDebounceFn);
    }, [query]);

    const handleSelect = (patientId) => {
        navigate(`/patients/${patientId}`);
        setIsOpen(false);
        setQuery('');
    };

    return (
        <div className="relative w-full max-w-md mx-auto block" ref={searchRef}>
            <div className="relative">
                <Search className="absolute right-4 top-3.5 text-slate-400" size={20} />
                <input
                    type="text"
                    placeholder="بحث..."
                    className="w-full pl-4 pr-12 py-3 bg-slate-100 dark:bg-slate-800 rounded-2xl border border-transparent focus:bg-white dark:focus:bg-slate-900 focus:border-primary/20 outline-none transition-all text-sm font-bold text-slate-700 dark:text-slate-200 shadow-sm"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => query.length > 1 && setIsOpen(true)}
                />
                {query && (
                    <button
                        onClick={() => { setQuery(''); setIsOpen(false); }}
                        className="absolute left-3 top-3.5 text-slate-400 hover:text-red-500 transition-colors"
                    >
                        <X size={18} />
                    </button>
                )}
            </div>

            {/* Results Dropdown */}
            {isOpen && (
                <div className="absolute top-full mt-2 w-full bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-slate-100 dark:border-white/5 overflow-hidden z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                    {loading ? (
                        <div className="p-4 text-center text-slate-400 text-sm font-bold">جاري البحث...</div>
                    ) : results.length > 0 ? (
                        <div className="max-h-[300px] overflow-y-auto custom-scrollbar">
                            {results.map((patient) => (
                                <div
                                    key={patient.id}
                                    onClick={() => handleSelect(patient.id)}
                                    className="p-4 hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer flex items-center gap-4 transition-colors border-b border-slate-50 dark:border-white/5 last:border-0"
                                >
                                    <div className="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-500 rounded-xl">
                                        <User size={20} />
                                    </div>
                                    <div>
                                        <p className="font-bold text-slate-800 dark:text-white text-sm">{patient.name}</p>
                                        <div className="flex gap-3 text-xs text-slate-500 dark:text-slate-400 mt-1">
                                            <span>{patient.phone}</span>
                                            {patient.address && <span>• {patient.address}</span>}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="p-4 text-center text-slate-400 text-sm font-bold">لا توجد نتائج</div>
                    )}
                </div>
            )}
        </div>
    );
}

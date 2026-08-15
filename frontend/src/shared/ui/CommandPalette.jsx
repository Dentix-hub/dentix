import { useState, useEffect, useMemo, useRef } from 'react';
import { Search, Users, Calendar, Settings, Home, Package, Command, X, ArrowRight } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import { motion } from '@/lib/motion';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const CommandPalette = ({ isOpen, onClose, patients = [], appointments = [] }) => {
    const { t } = useTranslation();
    const [query, setQuery] = useState('');
    const [selectedIndex, setSelectedIndex] = useState(0);
    const navigate = useNavigate();
    const inputRef = useRef(null);

    // Reset query and index when closed
    useEffect(() => {
        if (!isOpen) {
            setQuery('');
            setSelectedIndex(0);
        } else {
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    }, [isOpen]);

    // Filtering logic
    const results = useMemo(() => {
        if (!query) return [];
        
        const q = query.toLowerCase();
        const items = [];
        
        // 1. Pages
        const pages = [
            { id: 'p1', type: 'page', title: t('sidebar.dashboard'), icon: Home, url: '/' },
            { id: 'p2', type: 'page', title: t('sidebar.appointments'), icon: Calendar, url: '/appointments' },
            { id: 'p3', type: 'page', title: t('sidebar.patients'), icon: Users, url: '/patients' },
            { id: 'p4', type: 'page', title: t('sidebar.inventory'), icon: Package, url: '/inventory' },
            { id: 'p5', type: 'page', title: t('sidebar.settings'), icon: Settings, url: '/settings' },
        ];
        
        pages.filter(p => p.title.toLowerCase().includes(q))
             .forEach(p => items.push({ ...p, section: t('command_palette.sections.pages') }));

        // 2. Actions (Commands)
        const actions = [
            { id: 'a1', type: 'action', title: t('command_palette.add_patient'), icon: Users, url: '/patients?action=new' },
            { id: 'a2', type: 'action', title: t('command_palette.new_appointment'), icon: Calendar, url: '/appointments?action=new' },
        ];
        
        actions.filter(a => a.title.toLowerCase().includes(q))
               .forEach(a => items.push({ ...a, section: t('command_palette.sections.actions') }));

        // 3. Search Patients
        patients.filter(p => 
            p.name?.toLowerCase().includes(q) || 
            p.phone?.includes(q)
        ).slice(0, 5).forEach(p => {
            items.push({
                id: `patient-${p.id}`,
                type: 'patient',
                title: p.name,
                subtitle: p.phone,
                icon: Users,
                url: `/patients/${p.id}`,
                section: t('command_palette.sections.patients')
            });
        });

        // 4. Search Appointments (By patient name)
        appointments.filter(appt => 
            appt.patient_name?.toLowerCase().includes(q)
        ).slice(0, 3).forEach(appt => {
            items.push({
                id: `appt-${appt.id}`,
                type: 'appointment',
                title: appt.patient_name,
                subtitle: `${appt.date} @ ${appt.time}`,
                icon: Calendar,
                url: `/appointments?id=${appt.id}`,
                section: t('command_palette.sections.appointments')
            });
        });

        return items;
    }, [query, t, patients, appointments]);

    // Handle index bounds when results change
    useEffect(() => {
        setSelectedIndex(0);
    }, [results]);

    // Keyboard handling
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (!isOpen) return;

            if (e.key === 'Escape') onClose();
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex(prev => (prev + 1) % (results.length || 1));
            }
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex(prev => (prev - 1 + (results.length || 1)) % (results.length || 1));
            }
            if (e.key === 'Enter' && results.length > 0) {
                e.preventDefault();
                const selected = results[selectedIndex];
                navigate(selected.url);
                onClose();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, results, selectedIndex, navigate, onClose]);

    const handleSelect = (url) => {
        navigate(url);
        onClose();
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[9999] flex items-start justify-center pt-[15vh] px-4 overflow-hidden">
                    {/* Backdrop */}
                    <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-slate-900/60 backdrop-blur-md" 
                    />
                    
                    {/* Palette */}
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.95, y: -20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: -20 }}
                        className="relative w-full max-w-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl rounded-[2.5rem] shadow-2xl border border-white/20 dark:border-white/5 overflow-hidden flex flex-col"
                    >
                        {/* Search Input Area */}
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800/50 flex items-center gap-4">
                            <div className="bg-primary/10 p-2.5 rounded-2xl text-primary">
                                <Search size={22} />
                            </div>
                            <input 
                                ref={inputRef}
                                className="flex-1 bg-transparent border-none outline-none text-xl font-bold text-slate-800 dark:text-slate-100 placeholder:text-slate-500"
                                placeholder={t('command_palette.placeholder')}
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                            />
                            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-800/50 rounded-xl text-[10px] font-bold text-slate-500 uppercase tracking-widest ring-1 ring-slate-200/50 dark:ring-white/5">
                                <Command size={12} />
                                <span>K</span>
                            </div>
                            <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors">
                                <X size={20} className="text-slate-500" />
                            </button>
                        </div>
                        
                        {/* Results Area */}
                        <div className="max-h-[50vh] overflow-y-auto p-4 custom-scrollbar">
                            {results.length > 0 ? (
                                <div className="space-y-4">
                                    {/* Grouped Results */}
                                    {Object.entries(
                                        results.reduce((acc, curr) => {
                                            if (!acc[curr.section]) acc[curr.section] = [];
                                            acc[curr.section].push(curr);
                                            return acc;
                                        }, {})
                                    ).map(([section, sectionItems]) => (
                                        <div key={section} className="space-y-1">
                                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-3 mb-2">{section}</p>
                                            {sectionItems.map((res) => {
                                                const globalIndex = results.indexOf(res);
                                                const isSelected = selectedIndex === globalIndex;
                                                
                                                return (
                                                    <button
                                                        key={res.id}
                                                        onClick={() => handleSelect(res.url)}
                                                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                                                        className={`w-full flex items-center gap-4 p-4 rounded-2xl transition-all text-left group border relative ${
                                                            isSelected 
                                                            ? 'bg-primary/5 border-primary/20 shadow-sm' 
                                                            : 'bg-transparent border-transparent'
                                                        }`}
                                                    >
                                                        {isSelected && (
                                                            <motion.div 
                                                                layoutId="active-highlight"
                                                                className="absolute inset-0 bg-primary/[0.03] rounded-2xl"
                                                                transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                                                            />
                                                        )}
                                                        <div className={`p-3 rounded-xl transition-all shadow-sm ${
                                                            isSelected 
                                                            ? 'bg-primary/10 text-primary scale-110' 
                                                            : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                                                        }`}>
                                                            <res.icon size={20} />
                                                        </div>
                                                        <div className="flex-1 min-w-0 relative">
                                                            <h4 className={`font-bold text-sm tracking-tight truncate ${
                                                                isSelected ? 'text-primary' : 'text-slate-800 dark:text-slate-100'
                                                            }`}>{res.title}</h4>
                                                            {res.subtitle && <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-0.5">{res.subtitle}</p>}
                                                        </div>
                                                        <div className={`flex items-center gap-2 text-[10px] font-bold text-primary uppercase tracking-widest transition-all transform ${
                                                            isSelected ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-2'
                                                        }`}>
                                                            {t('command_palette.go_to')}
                                                            <div className="bg-primary/10 p-1 rounded-md">
                                                                <ArrowRight size={10} />
                                                            </div>
                                                        </div>
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    ))}
                                </div>
                            ) : query ? (
                                <div className="py-20 text-center">
                                    <div className="inline-flex p-6 rounded-[2rem] bg-slate-50 dark:bg-slate-800/50 mb-4 shadow-inner">
                                        <Search size={40} className="text-slate-300" />
                                    </div>
                                    <p className="text-slate-500 font-bold text-lg mb-1">{t('command_palette.no_results')}</p>
                                    <p className="text-slate-500 text-sm">{t('command_palette.no_results_desc', { query })}</p>
                                </div>
                            ) : (
                                <div className="space-y-6 px-2">
                                     <div>
                                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">{t('command_palette.quick_nav')}</p>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            {[
                                                { title: t('command_palette.add_patient'), icon: Users, url: '/patients?action=new', color: 'text-blue-500', bg: 'bg-blue-500/10' },
                                                { title: t('command_palette.new_appointment'), icon: Calendar, url: '/appointments?action=new', color: 'text-indigo-500', bg: 'bg-indigo-500/10' },
                                                { title: t('command_palette.inventory_check'), icon: Package, url: '/inventory', color: 'text-amber-500', bg: 'bg-amber-500/10' },
                                                { title: t('command_palette.settings'), icon: Settings, url: '/settings', color: 'text-slate-500', bg: 'bg-slate-500/10' },
                                            ].map(item => (
                                                <button 
                                                    key={item.title}
                                                    onClick={() => handleSelect(item.url)}
                                                    className="flex items-center gap-4 p-5 rounded-2xl border border-slate-100 dark:border-white/5 hover:border-primary/30 hover:bg-white dark:hover:bg-slate-800 hover:shadow-lg transition-all text-left group"
                                                >
                                                    <div className={`p-3 rounded-xl ${item.bg} ${item.color} group-hover:scale-110 transition-transform`}>
                                                        <item.icon size={20} />
                                                    </div>
                                                    <span className="font-bold text-sm text-slate-700 dark:text-slate-200 tracking-tight">{item.title}</span>
                                                </button>
                                            ))}
                                        </div>
                                     </div>
                                </div>
                            )}
                        </div>
                        
                        {/* Footer */}
                        <div className="p-4 bg-slate-50/50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-white/5 flex justify-center gap-6">
                            <div className="flex items-center gap-2">
                                <kbd className="px-2 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-lg text-[10px] font-bold shadow-sm">ESC</kbd>
                                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{t('command_palette.to_close')}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <kbd className="px-2 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-lg text-[10px] font-bold shadow-sm">↵</kbd>
                                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{t('command_palette.to_select')}</span>
                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};

export default CommandPalette;

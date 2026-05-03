import React, { useState, useEffect } from 'react';
import { Search, Users, Calendar, Settings, Home, Package, Command, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const CommandPalette = ({ isOpen, onClose, patients = [], appointments = [] }) => {
    const [query, setQuery] = useState('');
    const navigate = useNavigate();

    // Reset query when closed
    useEffect(() => {
        if (!isOpen) setQuery('');
    }, [isOpen]);

    // Handle ESC key
    useEffect(() => {
        const handleEsc = (e) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleEsc);
        return () => window.removeEventListener('keydown', handleEsc);
    }, [onClose]);

    // Filtering logic
    const getFilteredResults = () => {
        if (!query) return [];
        
        const q = query.toLowerCase();
        const results = [];
        
        // Search Patients
        const matchedPatients = patients.filter(p => 
            p.name?.toLowerCase().includes(q) || 
            p.phone?.includes(q)
        ).slice(0, 5);
        
        matchedPatients.forEach(p => {
            results.push({
                type: 'patient',
                id: p.id,
                title: p.name,
                subtitle: p.phone,
                icon: Users,
                url: `/patients/${p.id}`
            });
        });

        // Search Pages
        const pages = [
            { title: 'Dashboard', icon: Home, url: '/' },
            { title: 'Appointments', icon: Calendar, url: '/appointments' },
            { title: 'Patients', icon: Users, url: '/patients' },
            { title: 'Inventory', icon: Package, url: '/inventory' },
            { title: 'Settings', icon: Settings, url: '/settings' },
        ];
        
        pages.filter(p => p.title.toLowerCase().includes(q))
             .forEach(p => results.push({ ...p, type: 'page' }));

        return results;
    };

    const results = getFilteredResults();

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
                                autoFocus
                                className="flex-1 bg-transparent border-none outline-none text-xl font-bold text-slate-800 dark:text-slate-100 placeholder:text-slate-400"
                                placeholder="Search anything..."
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                            />
                            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-800/50 rounded-xl text-[10px] font-black text-slate-500 uppercase tracking-widest ring-1 ring-slate-200/50 dark:ring-white/5">
                                <Command size={12} />
                                <span>K</span>
                            </div>
                            <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors">
                                <X size={20} className="text-slate-400" />
                            </button>
                        </div>
                        
                        {/* Results Area */}
                        <div className="max-h-[50vh] overflow-y-auto p-4 custom-scrollbar">
                            {results.length > 0 ? (
                                <div className="space-y-1">
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 px-3">Search Results</p>
                                    {results.map((res, idx) => (
                                        <button
                                            key={`${res.type}-${res.id || idx}`}
                                            onClick={() => {
                                                navigate(res.url);
                                                onClose();
                                            }}
                                            className="w-full flex items-center gap-4 p-4 rounded-2xl hover:bg-primary/5 dark:hover:bg-primary/10 transition-all text-left group border border-transparent hover:border-primary/20"
                                        >
                                            <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-500 group-hover:text-primary group-hover:bg-primary/10 transition-all group-hover:scale-110 shadow-sm">
                                                <res.icon size={20} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <h4 className="font-black text-slate-800 dark:text-slate-100 text-sm tracking-tight truncate group-hover:text-primary transition-colors">{res.title}</h4>
                                                {res.subtitle && <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">{res.subtitle}</p>}
                                            </div>
                                            <div className="flex items-center gap-2 text-[10px] font-black text-primary opacity-0 group-hover:opacity-100 transition-all uppercase tracking-widest transform translate-x-2 group-hover:translate-x-0">
                                                Go To
                                                <div className="bg-primary/10 p-1 rounded-md">
                                                    <Search size={10} />
                                                </div>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            ) : query ? (
                                <div className="py-20 text-center">
                                    <div className="inline-flex p-6 rounded-[2rem] bg-slate-50 dark:bg-slate-800/50 mb-4 shadow-inner">
                                        <Search size={40} className="text-slate-300" />
                                    </div>
                                    <p className="text-slate-500 font-bold text-lg mb-1">No matches found</p>
                                    <p className="text-slate-400 text-sm">We couldn't find any results for "{query}"</p>
                                </div>
                            ) : (
                                <div className="space-y-6 px-2">
                                     <div>
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Quick Navigation</p>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            {[
                                                { title: 'Add Patient', icon: Users, url: '/patients?action=new', color: 'text-blue-500', bg: 'bg-blue-500/10' },
                                                { title: 'New Appointment', icon: Calendar, url: '/appointments?action=new', color: 'text-purple-500', bg: 'bg-purple-500/10' },
                                                { title: 'Inventory Check', icon: Package, url: '/inventory', color: 'text-amber-500', bg: 'bg-amber-500/10' },
                                                { title: 'Settings', icon: Settings, url: '/settings', color: 'text-slate-500', bg: 'bg-slate-500/10' },
                                            ].map(item => (
                                                <button 
                                                    key={item.title}
                                                    onClick={() => { navigate(item.url); onClose(); }}
                                                    className="flex items-center gap-4 p-5 rounded-2xl border border-slate-100 dark:border-white/5 hover:border-primary/30 hover:bg-white dark:hover:bg-slate-800 hover:shadow-lg transition-all text-left group"
                                                >
                                                    <div className={`p-3 rounded-xl ${item.bg} ${item.color} group-hover:scale-110 transition-transform`}>
                                                        <item.icon size={20} />
                                                    </div>
                                                    <span className="font-black text-sm text-slate-700 dark:text-slate-200 tracking-tight">{item.title}</span>
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
                                <kbd className="px-2 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-lg text-[10px] font-black shadow-sm">ESC</kbd>
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">to close</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <kbd className="px-2 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-lg text-[10px] font-black shadow-sm">↵</kbd>
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">to select</span>
                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};

export default CommandPalette;

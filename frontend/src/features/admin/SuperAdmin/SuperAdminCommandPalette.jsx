import { useState, useEffect, useCallback } from 'react';
import logger from '@/utils/logger';
import { Search, Building2, Users, CreditCard, Terminal, Cpu, ArrowRight, User } from 'lucide-react';
import { api } from '@/api';
import { useNavigate } from 'react-router-dom';

export default function CommandPalette({ isOpen, onClose }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const navigate = useNavigate();

    const handleSearch = useCallback(async (q) => {
        if (q.length < 2) {
            setResults([]);
            return;
        }
        setLoading(true);
        try {
            const res = await api.get(`/api/v1/admin/system/search?q=${q}`);
            setResults(res.data || []);
            setSelectedIndex(0);
        } catch (err) {
            logger.error('Search failed:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!isOpen) return;
        const timer = setTimeout(() => {
            handleSearch(query);
        }, 300);
        return () => clearTimeout(timer);
    }, [query, handleSearch, isOpen]);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex(prev => (prev + 1) % (results.length || 1));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex(prev => (prev - 1 + (results.length || 1)) % (results.length || 1));
            } else if (e.key === 'Enter') {
                if (results[selectedIndex]) {
                    handleSelect(results[selectedIndex]);
                }
            } else if (e.key === 'Escape') {
                onClose();
            }
        };

        if (isOpen) {
            window.addEventListener('keydown', handleKeyDown);
        }
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, results, selectedIndex]);

    const handleSelect = (item) => {
        navigate(item.url);
        onClose();
        setQuery('');
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] px-4">
            <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm animate-fade-in" onClick={onClose} />
            
            <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden animate-scale-in">
                <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center gap-4">
                    <Search className="text-slate-400" size={24} />
                    <input
                        autoFocus
                        placeholder="ابحث عن عيادة، مستخدم، أو صفحة إدارية..."
                        className="w-full bg-transparent border-none outline-none text-xl font-bold text-slate-800 dark:text-white placeholder-slate-400 text-right"
                        dir="rtl"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-500 text-xs font-bold">
                        <Command size={14} />
                        <span>K</span>
                    </div>
                </div>

                <div className="max-h-[60vh] overflow-y-auto p-2">
                    {loading && (
                        <div className="p-8 text-center text-slate-400">
                            <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                            جاري البحث...
                        </div>
                    )}

                    {!loading && results.length > 0 && (
                        <div className="space-y-1">
                            {results.map((item, index) => (
                                <button
                                    key={`${item.type}-${item.id}`}
                                    onClick={() => handleSelect(item)}
                                    className={`w-full p-4 flex items-center justify-between rounded-2xl transition-all ${
                                        selectedIndex === index 
                                        ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 ring-1 ring-indigo-500/20' 
                                        : 'hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                                    }`}
                                >
                                    <div className="flex items-center gap-4 text-right" dir="rtl">
                                        <div className={`p-3 rounded-xl ${
                                            selectedIndex === index ? 'bg-indigo-100 dark:bg-indigo-800/50' : 'bg-slate-100 dark:bg-slate-800'
                                        }`}>
                                            {item.icon === 'Building2' && <Building2 size={20} />}
                                            {item.icon === 'User' && <User size={20} />}
                                            {item.icon === 'Users' && <Users size={20} />}
                                            {item.icon === 'CreditCard' && <CreditCard size={20} />}
                                            {item.icon === 'Terminal' && <Terminal size={20} />}
                                            {item.icon === 'Cpu' && <Cpu size={20} />}
                                        </div>
                                        <div>
                                            <div className="font-bold text-lg">{item.title}</div>
                                            <div className="text-sm opacity-60 font-medium">{item.subtitle}</div>
                                        </div>
                                    </div>
                                    {selectedIndex === index && <ArrowRight size={20} className="animate-pulse" />}
                                </button>
                            ))}
                        </div>
                    )}

                    {!loading && query.length >= 2 && results.length === 0 && (
                        <div className="p-12 text-center text-slate-400 italic">
                            لم يتم العثور على نتائج لـ "{query}"
                        </div>
                    )}

                    {!loading && query.length < 2 && (
                        <div className="p-8">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 text-right">اقتراحات سريعة</div>
                            <div className="grid grid-cols-2 gap-3" dir="rtl">
                                {[
                                    { title: 'العيادات النشطة', url: '/admin/tenants?status=active', icon: <Building2 size={18} /> },
                                    { title: 'سجل الأخطاء', url: '/admin/system/logs', icon: <Terminal size={18} /> },
                                    { title: 'الإيرادات', url: '/admin/finance', icon: <CreditCard size={18} /> },
                                    { title: 'تحليلات AI', url: '/ai/stats', icon: <Cpu size={18} /> },
                                ].map(rec => (
                                    <button 
                                        key={rec.url}
                                        onClick={() => handleSelect(rec)}
                                        className="flex items-center gap-3 p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-100 dark:border-slate-800 transition-all text-slate-600 dark:text-slate-400 font-bold"
                                    >
                                        {rec.icon}
                                        <span className="text-sm">{rec.title}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                <div className="p-4 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                    <div className="flex gap-4">
                        <span className="flex items-center gap-1"><span className="px-1 py-0.5 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700">↵</span> للتنفيذ</span>
                        <span className="flex items-center gap-1"><span className="px-1 py-0.5 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700">↑↓</span> للتنقل</span>
                    </div>
                    <div className="flex items-center gap-1">
                        اضغط <span className="px-1 py-0.5 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700">ESC</span> للإغلاق
                    </div>
                </div>
            </div>
        </div>
    );
}

import { useState, useEffect, useCallback, useMemo } from 'react';
import logger from '@/utils/logger';
import { Search, Building2, Users, CreditCard, Terminal, Cpu, ArrowRight, User, Command, Settings as SettingsIcon, Mail, Shield } from 'lucide-react';
import { api } from '@/api';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function SuperAdminCommandPalette({ isOpen, onClose }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const navigate = useNavigate();

    const staticAdminActions = useMemo(() => [
        { type: 'page', id: 'overview', title: t('super_admin.palette.overview_title', 'لوحة التحكم الرئيسية'), subtitle: t('super_admin.palette.overview_sub', 'نظرة عامة ومؤشرات النظام'), url: '/admin', icon: 'Shield' },
        { type: 'page', id: 'tenants', title: t('super_admin.palette.tenants_title', 'إدارة العيادات والمستأجرين'), subtitle: t('super_admin.palette.tenants_sub', 'الاشتراكات والعيادات النشطة'), url: '/admin/tenants', icon: 'Building2' },
        { type: 'page', id: 'users', title: t('super_admin.palette.users_title', 'إدارة المستخدمين'), subtitle: t('super_admin.palette.users_sub', 'حسابات المستخدمين والمشرفين'), url: '/admin/users', icon: 'Users' },
        { type: 'page', id: 'finance', title: t('super_admin.palette.finance_title', 'التقارير المالية والفوترة'), subtitle: t('super_admin.palette.finance_sub', 'الإيرادات والمدفوعات والاشتراكات'), url: '/admin/finance', icon: 'CreditCard' },
        { type: 'page', id: 'messages', title: t('super_admin.palette.support_title', 'رسائل الدعم والتواصل'), subtitle: t('super_admin.palette.support_sub', 'صندوق رسائل العيادات والدعم'), url: '/admin/messages', icon: 'Mail' },
        { type: 'page', id: 'ai', title: t('super_admin.palette.ai_title', 'تحليلات الذكاء الاصطناعي'), subtitle: t('super_admin.palette.ai_sub', 'استهلاك وتكاليف نماذج AI'), url: '/ai/stats', icon: 'Cpu' },
        { type: 'page', id: 'logs', title: t('super_admin.palette.logs_title', 'سجل أخطاء النظام'), subtitle: t('super_admin.palette.logs_sub', 'مراقبة أخطاء الخادم والتشخيص'), url: '/admin/system/logs', icon: 'Terminal' },
        { type: 'page', id: 'settings', title: t('super_admin.palette.settings_title', 'إعدادات النظام العامة'), subtitle: t('super_admin.palette.settings_sub', 'تكوين الخادم والميزات والأمان'), url: '/admin/settings', icon: 'Settings' },
    ], [t]);

    const handleSelect = useCallback((item) => {
        if (!item || !item.url) return;
        navigate(item.url);
        onClose();
        setQuery('');
    }, [navigate, onClose]);

    const handleSearch = useCallback(async (q) => {
        const trimmed = q.trim().toLowerCase();
        if (trimmed.length < 2) {
            setResults([]);
            return;
        }

        setLoading(true);
        try {
            // 1. Search matching static system actions
            const matchedActions = staticAdminActions.filter(action =>
                action.title.toLowerCase().includes(trimmed) ||
                action.subtitle.toLowerCase().includes(trimmed) ||
                action.url.toLowerCase().includes(trimmed)
            );

            // 2. Search matching tenants from backend API
            let matchedTenants = [];
            try {
                const res = await api.get('/api/v1/admin/tenants');
                const tenantsList = Array.isArray(res.data) ? res.data : (Array.isArray(res) ? res : []);
                matchedTenants = tenantsList
                    .filter(tn => 
                        (tn.name && tn.name.toLowerCase().includes(trimmed)) ||
                        (tn.domain && tn.domain.toLowerCase().includes(trimmed)) ||
                        (tn.admin_email && tn.admin_email.toLowerCase().includes(trimmed)) ||
                        (tn.contact_phone && tn.contact_phone.includes(trimmed))
                    )
                    .map(tn => ({
                        type: 'tenant',
                        id: `tenant-${tn.id}`,
                        title: tn.name || `${t('super_admin.palette.clinic', 'عيادة')} #${tn.id}`,
                        subtitle: `${tn.domain ? tn.domain + '.dentix.com' : 'portal.dentix.com'} • ${t('super_admin.palette.plan', 'خطة')} ${tn.plan || 'trial'}`,
                        url: `/admin/tenants?id=${tn.id}`,
                        icon: 'Building2',
                    }));
            } catch (err) {
                logger.error('Failed to search tenants in CommandPalette:', err);
            }

            setResults([...matchedActions, ...matchedTenants]);
            setSelectedIndex(0);
        } catch (err) {
            logger.error('CommandPalette search error:', err);
            setResults([]);
        } finally {
            setLoading(false);
        }
    }, [staticAdminActions, t]);

    useEffect(() => {
        if (!isOpen) {
            setQuery('');
            setResults([]);
            return;
        }
        const timer = setTimeout(() => {
            handleSearch(query);
        }, 200);
        return () => clearTimeout(timer);
    }, [query, handleSearch, isOpen]);

    useEffect(() => {
        if (!isOpen) return;

        const handleKeyDown = (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex(prev => (prev + 1) % (results.length || 1));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex(prev => (prev - 1 + (results.length || 1)) % (results.length || 1));
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (results[selectedIndex]) {
                    handleSelect(results[selectedIndex]);
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                onClose();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleSelect, isOpen, onClose, results, selectedIndex]);

    if (!isOpen) return null;

    const renderIcon = (iconName) => {
        switch (iconName) {
            case 'Building2': return <Building2 size={20} />;
            case 'Users': return <Users size={20} />;
            case 'CreditCard': return <CreditCard size={20} />;
            case 'Terminal': return <Terminal size={20} />;
            case 'Cpu': return <Cpu size={20} />;
            case 'Mail': return <Mail size={20} />;
            case 'Settings': return <SettingsIcon size={20} />;
            case 'Shield': return <Shield size={20} />;
            default: return <User size={20} />;
        }
    };

    return (
        <div className="fixed inset-x-0 inset-y-0 z-50 flex items-start justify-center pt-[15vh] px-4" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="fixed inset-x-0 inset-y-0 bg-slate-900/60 backdrop-blur-sm animate-fade-in" onClick={onClose} />
            
            <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden animate-scale-in">
                <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center gap-4">
                    <Search className="text-slate-400 shrink-0" size={24} />
                    <input
                        autoFocus
                        placeholder={t('super_admin.palette.search_placeholder', 'ابحث عن عيادة، مستخدم، أو صفحة إدارية...')}
                        className="w-full bg-transparent border-none outline-none text-xl font-bold text-slate-800 dark:text-white placeholder-slate-400 text-start"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-500 text-xs font-bold shrink-0">
                        <Command size={14} />
                        <span>K</span>
                    </div>
                </div>

                <div className="max-h-[60vh] overflow-y-auto p-2">
                    {loading && (
                        <div className="p-8 text-center text-slate-400">
                            <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                            {t('common.searching', 'جاري البحث...')}
                        </div>
                    )}

                    {!loading && results.length > 0 && (
                        <div className="space-y-1">
                            {results.map((item, index) => (
                                <button
                                    key={`${item.type}-${item.id}`}
                                    type="button"
                                    onClick={() => handleSelect(item)}
                                    className={`w-full p-4 flex items-center justify-between rounded-2xl transition-all cursor-pointer ${
                                        selectedIndex === index 
                                        ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 ring-1 ring-indigo-500/20' 
                                        : 'hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                                    }`}
                                >
                                    <div className="flex items-center gap-4 text-start">
                                        <div className={`p-3 rounded-xl ${
                                            selectedIndex === index ? 'bg-indigo-100 dark:bg-indigo-800/50' : 'bg-slate-100 dark:bg-slate-800'
                                        }`}>
                                            {renderIcon(item.icon)}
                                        </div>
                                        <div className="text-start">
                                            <div className="font-bold text-lg">{item.title}</div>
                                            <div className="text-sm opacity-60 font-medium">{item.subtitle}</div>
                                        </div>
                                    </div>
                                    {selectedIndex === index && <ArrowRight size={20} className="animate-pulse shrink-0" />}
                                </button>
                            ))}
                        </div>
                    )}

                    {!loading && query.trim().length >= 2 && results.length === 0 && (
                        <div className="p-12 text-center text-slate-400 italic">
                            {t('super_admin.palette.no_results', 'لم يتم العثور على نتائج')} &quot;{query}&quot;
                        </div>
                    )}

                    {!loading && query.trim().length < 2 && (
                        <div className="p-8">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 text-start">
                                {t('super_admin.palette.quick_suggestions', 'اقتراحات سريعة')}
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {[
                                    { title: t('sidebar.clinics', 'إدارة العيادات'), url: '/admin/tenants', icon: <Building2 size={18} /> },
                                    { title: t('sidebar.error_log', 'سجل الأخطاء'), url: '/admin/system/logs', icon: <Terminal size={18} /> },
                                    { title: t('sidebar.finance', 'التقارير المالية'), url: '/admin/finance', icon: <CreditCard size={18} /> },
                                    { title: t('sidebar.ai', 'تحليلات AI'), url: '/ai/stats', icon: <Cpu size={18} /> },
                                    { title: t('sidebar.users', 'إدارة المستخدمين'), url: '/admin/users', icon: <Users size={18} /> },
                                    { title: t('sidebar.settings', 'إعدادات النظام'), url: '/admin/settings', icon: <SettingsIcon size={18} /> },
                                ].map(rec => (
                                    <button 
                                        key={rec.url}
                                        type="button"
                                        onClick={() => handleSelect(rec)}
                                        className="flex items-center gap-3 p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-100 dark:border-slate-800 transition-all text-slate-600 dark:text-slate-400 font-bold cursor-pointer text-start"
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
                        <span className="flex items-center gap-1">
                            <span className="px-1.5 py-0.5 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700">↵</span> {t('super_admin.palette.to_select', 'للتنفيذ')}
                        </span>
                        <span className="flex items-center gap-1">
                            <span className="px-1.5 py-0.5 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700">↑↓</span> {t('super_admin.palette.to_navigate', 'للتنقل')}
                        </span>
                    </div>
                    <div className="flex items-center gap-1">
                        {t('super_admin.palette.esc_to_close', 'اضغط ESC للإغلاق')}
                    </div>
                </div>
            </div>
        </div>
    );
}

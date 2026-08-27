import { useState, useEffect, useCallback, useTransition } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import {
    Monitor,
    LogOut,
    Search,
    RefreshCw,
    Smartphone,
    Laptop,
    Globe,
    Clock,
    Calendar,
    ShieldAlert,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast, ConfirmDialog } from '@/shared/ui';

export default function SessionManager() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [, startTransition] = useTransition();

    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

    // Terminate Session Modal State
    const [targetSession, setTargetSession] = useState(null);
    const [isTerminating, setIsTerminating] = useState(false);

    const fetchSessions = useCallback(async (isBackground = false) => {
        if (isBackground) {
            setIsRefreshing(true);
        } else {
            setLoading(true);
        }

        try {
            const res = await api.get('/api/v1/admin/security/sessions');
            const data = res?.data?.data || res?.data;
            setSessions(Array.isArray(data) ? data : []);
        } catch (err) {
            logger.error('Failed to fetch sessions:', err);
            toast.error(t('super_admin.sessions.fetch_error') || 'فشل تحميل الجلسات النشطة');
        } finally {
            setLoading(false);
            setIsRefreshing(false);
        }
    }, [t]);

    useEffect(() => {
        fetchSessions();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleConfirmTerminate = async () => {
        const session = targetSession;
        if (!session) return;
        setIsTerminating(true);
        try {
            await api.delete(`/api/v1/admin/security/sessions/${session.id}`);
            toast.success(t('super_admin.sessions.terminate_success') || 'تم إنهاء الجلسة بنجاح');
            setSessions(prev => prev.filter(s => s.id !== session.id));
        } catch (err) {
            logger.error('Failed to terminate session:', err);
            const detail = err.response?.data?.detail || err.message || t('super_admin.sessions.terminate_failed') || 'فشل إنهاء الجلسة';
            toast.error(detail);
        } finally {
            setIsTerminating(false);
            setTargetSession(null);
        }
    };

    const getDeviceIcon = (userAgent) => {
        const ua = (userAgent || '').toLowerCase();
        if (ua.includes('mobi') || ua.includes('android') || ua.includes('iphone') || ua.includes('ipad')) {
            return <Smartphone size={22} />;
        }
        return <Laptop size={22} />;
    };

    const term = (searchTerm || '').toLowerCase().trim();
    const filteredSessions = sessions.filter(s => {
        if (!term) return true;
        const username = (s.username || '').toLowerCase();
        const tenant = (s.tenant || '').toLowerCase();
        const ip = (s.ip_address || '').toLowerCase();
        const city = (s.location?.city || '').toLowerCase();
        const country = (s.location?.country_code || '').toLowerCase();
        return username.includes(term) || tenant.includes(term) || ip.includes(term) || city.includes(term) || country.includes(term);
    });

    if (loading && sessions.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-64 space-y-4" dir={isRtl ? 'rtl' : 'ltr'}>
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
                <p className="text-slate-500 font-bold animate-pulse">{t('super_admin.sessions.loading') || 'جاري جلب الجلسات النشطة...'}</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500" dir={isRtl ? 'rtl' : 'ltr'}>
            {/* Header / Search Controls */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="text-start">
                    <h2 className="text-2xl font-black text-slate-800 dark:text-white flex items-center gap-2">
                        <Monitor className="text-emerald-500" />
                        {t('super_admin.sessions.title') || 'إدارة الجلسات النشطة'}
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 font-bold text-sm">
                        {t('super_admin.sessions.subtitle') || 'مراقبة وإنهاء جلسات المستخدمين في جميع العيادات'}
                    </p>
                </div>
                <div className="flex gap-2 w-full md:w-auto">
                    <button 
                        type="button"
                        onClick={() => fetchSessions(true)}
                        disabled={loading || isRefreshing}
                        className="p-3 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-2xl hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                        title={t('common.refresh') || 'تحديث'}
                        aria-label={t('common.refresh') || 'تحديث'}
                    >
                        <RefreshCw size={20} className={isRefreshing ? 'animate-spin text-indigo-600' : 'text-slate-600 dark:text-slate-300'} />
                    </button>
                    <div className="relative flex-1 md:w-80">
                        <Search className={`absolute ${isRtl ? 'start-4' : 'end-4'} top-1/2 -translate-y-1/2 text-slate-400`} size={20} />
                        <input 
                            type="text"
                            placeholder={t('super_admin.sessions.search_placeholder') || 'بحث بالاسم، العيادة، أو IP...'}
                            value={searchTerm}
                            onChange={(e) => {
                                const val = e.target.value;
                                startTransition(() => setSearchTerm(val));
                            }}
                            className={`w-full ${isRtl ? 'ps-12 pe-4' : 'pe-12 ps-4'} py-3 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-2xl shadow-sm outline-none focus:ring-2 focus:ring-emerald-500 font-bold text-slate-800 dark:text-slate-200 text-start`}
                        />
                    </div>
                </div>
            </div>

            {/* Session Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredSessions.map((session) => (
                    <div key={session.id} className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-100 dark:border-slate-800 p-6 shadow-sm hover:shadow-md transition-all group flex flex-col justify-between">
                        <div>
                            <div className="flex justify-between items-start mb-6">
                                <div className="flex items-center gap-4">
                                    <div className="w-14 h-14 rounded-2xl bg-slate-50 dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:bg-emerald-50 dark:group-hover:bg-emerald-900/20 group-hover:text-emerald-600 transition-colors shrink-0">
                                        {getDeviceIcon(session.user_agent)}
                                    </div>
                                    <div className="text-start">
                                        <h4 className="font-black text-slate-800 dark:text-white leading-tight">
                                            {session.username || t('super_admin.sessions.anonymous_user') || 'مستخدم غير معروف'}
                                        </h4>
                                        <p className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                                            {session.tenant || 'System'}
                                        </p>
                                    </div>
                                </div>
                                <button 
                                    type="button"
                                    onClick={() => setTargetSession(session)}
                                    disabled={isTerminating && targetSession?.id === session.id}
                                    className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all cursor-pointer disabled:opacity-40"
                                    title={t('super_admin.sessions.terminate_btn') || 'إنهاء الجلسة'}
                                    aria-label={`${t('super_admin.sessions.terminate_btn') || 'إنهاء الجلسة'} ${session.username || ''}`}
                                >
                                    <LogOut size={20} />
                                </button>
                            </div>

                            <div className="space-y-3">
                                <div className="flex items-center justify-between text-xs font-bold py-2 border-b border-slate-50 dark:border-slate-800">
                                    <span className="text-slate-400 flex items-center gap-1">
                                        <Globe size={14} /> IP & Location
                                    </span>
                                    <div className="flex flex-col items-end text-start">
                                        <span className="text-slate-600 dark:text-slate-300 font-mono">{session.ip_address || '—'}</span>
                                        {session.location && (
                                            <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                                                {session.location.city}, {session.location.country_code}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center justify-between text-xs font-bold py-2 border-b border-slate-50 dark:border-slate-800">
                                    <span className="text-slate-400 flex items-center gap-1">
                                        <Clock size={14} /> {t('super_admin.sessions.last_active') || 'آخر نشاط'}
                                    </span>
                                    <span className="text-slate-600 dark:text-slate-300">
                                        {session.last_active ? new Date(session.last_active).toLocaleString(i18n.language) : '—'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between text-xs font-bold py-2">
                                    <span className="text-slate-400 flex items-center gap-1">
                                        <Calendar size={14} /> {t('super_admin.sessions.start_time') || 'تاريخ البدء'}
                                    </span>
                                    <span className="text-slate-600 dark:text-slate-300">
                                        {session.created_at ? new Date(session.created_at).toLocaleDateString(i18n.language) : '—'}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-2xl text-[10px] font-bold text-slate-400 truncate" title={session.user_agent || 'Unknown device'}>
                            {session.user_agent || 'Unknown user agent'}
                        </div>
                    </div>
                ))}
            </div>

            {/* Empty State */}
            {filteredSessions.length === 0 && !loading && (
                <div className="text-center py-20 bg-slate-50 dark:bg-slate-800/20 rounded-[3rem] border-2 border-dashed border-slate-200 dark:border-slate-800">
                    <ShieldAlert size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
                    <p className="text-slate-500 dark:text-slate-400 font-bold">
                        {searchTerm ? (t('super_admin.sessions.no_search_matches') || 'لا توجد جلسات نشطة تطابق البحث') : (t('super_admin.sessions.no_active_sessions') || 'لا توجد جلسات نشطة حالياً')}
                    </p>
                </div>
            )}

            {/* Confirm Terminate Dialog */}
            <ConfirmDialog
                isOpen={!!targetSession}
                onClose={() => setTargetSession(null)}
                onConfirm={handleConfirmTerminate}
                title={t('super_admin.sessions.terminate_confirm_title') || 'تأكيد إنهاء الجلسة'}
                message={t('super_admin.sessions.terminate_confirm_msg', { username: targetSession?.username || 'المستخدم' }) || `هل أنت متأكد من رغبتك في إنهاء جلسة ${targetSession?.username || ''}؟ سيتم تسجيل خروج المستخدم فوراً.`}
                confirmText={t('super_admin.sessions.terminate_confirm_btn') || 'إنهاء الجلسة'}
                cancelText={t('common.cancel') || 'إلغاء'}
                variant="danger"
                isLoading={isTerminating}
            />
        </div>
    );
}

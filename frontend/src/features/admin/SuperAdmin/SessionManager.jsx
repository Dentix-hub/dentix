import React, { useState, useEffect } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import { 
    Monitor, Globe, Clock, Shield, LogOut, Search, 
    RefreshCw, Filter, MoreVertical, Smartphone, Laptop
} from 'lucide-react';
import { toast } from '@/shared/ui';

export default function SessionManager() {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        fetchSessions();
    }, []);

    const fetchSessions = async () => {
        setLoading(true);
        try {
            const res = await api.get('/api/v1/admin/security/sessions');
            setSessions(res.data);
        } catch (err) {
            logger.error('Failed to fetch sessions:', err);
            toast.error('فشل تحميل الجلسات النشطة');
        } finally {
            setLoading(false);
        }
    };

    const handleTerminate = async (sessionId) => {
        if (!window.confirm('هل أنت متأكد من إنهاء هذه الجلسة؟ سيتم تسجيل خروج المستخدم فوراً.')) return;
        
        try {
            await api.delete(`/api/v1/admin/security/sessions/${sessionId}`);
            toast.success('تم إنهاء الجلسة بنجاح');
            setSessions(prev => prev.filter(s => s.id !== sessionId));
        } catch (err) {
            toast.error('فشل إنهاء الجلسة');
        }
    };

    const getDeviceIcon = (userAgent) => {
        const ua = userAgent?.toLowerCase() || '';
        if (ua.includes('mobi') || ua.includes('android') || ua.includes('iphone')) return <Smartphone size={20} />;
        return <Laptop size={20} />;
    };

    const filteredSessions = sessions.filter(s => 
        s.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.tenant.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.ip_address.includes(searchTerm)
    );

    if (loading && sessions.length === 0) return (
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
            <p className="text-slate-500 font-bold animate-pulse">جاري جلب الجلسات النشطة...</p>
        </div>
    );

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header / Stats */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 className="text-2xl font-black text-slate-800 dark:text-white flex items-center gap-2">
                        <Monitor className="text-emerald-500" />
                        إدارة الجلسات النشطة
                    </h2>
                    <p className="text-slate-500 font-bold text-sm">مراقبة وإنهاء جلسات المستخدمين في جميع العيادات</p>
                </div>
                <div className="flex gap-2">
                    <button 
                        onClick={fetchSessions}
                        className="p-3 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-2xl hover:bg-slate-50 transition-colors shadow-sm"
                    >
                        <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
                    </button>
                    <div className="relative">
                        <Search className="absolute end-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
                        <input 
                            type="text"
                            placeholder="بحث بالاسم، العيادة، أو IP..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="pe-12 ps-4 py-3 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-2xl shadow-sm outline-none focus:ring-2 focus:ring-emerald-500 w-64 md:w-80 font-bold text-right"
                        />
                    </div>
                </div>
            </div>

            {/* Session Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredSessions.map((session) => (
                    <div key={session.id} className="bg-white dark:bg-slate-900 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 p-6 shadow-sm hover:shadow-md transition-all group">
                        <div className="flex justify-between items-start mb-6">
                            <div className="flex items-center gap-4">
                                <div className="w-14 h-14 rounded-2xl bg-slate-50 dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:bg-emerald-50 dark:group-hover:bg-emerald-900/20 group-hover:text-emerald-600 transition-colors">
                                    {getDeviceIcon(session.user_agent)}
                                </div>
                                <div className="text-right">
                                    <h4 className="font-black text-slate-800 dark:text-white leading-tight">{session.username}</h4>
                                    <p className="text-xs font-bold text-emerald-600">{session.tenant}</p>
                                </div>
                            </div>
                            <button 
                                onClick={() => handleTerminate(session.id)}
                                className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all"
                                title="إنهاء الجلسة"
                            >
                                <LogOut size={20} />
                            </button>
                        </div>

                        <div className="space-y-3">
                            <div className="flex items-center justify-between text-xs font-bold py-2 border-b border-slate-50 dark:border-slate-800">
                                <span className="text-slate-400">IP & Location</span>
                                <div className="text-left flex flex-col items-end">
                                    <span className="text-slate-600 dark:text-slate-300">{session.ip_address}</span>
                                    {session.location && (
                                        <span className="text-[10px] text-emerald-600">
                                            {session.location.city}, {session.location.country_code}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div className="flex items-center justify-between text-xs font-bold py-2 border-b border-slate-50 dark:border-slate-800">
                                <span className="text-slate-400">آخر نشاط</span>
                                <span className="text-slate-600 dark:text-slate-300" dir="rtl">
                                    {new Date(session.last_active).toLocaleString('ar-EG', { hour: '2-digit', minute: '2-digit' })}
                                </span>
                            </div>
                            <div className="flex items-center justify-between text-xs font-bold py-2">
                                <span className="text-slate-400">تاريخ البدء</span>
                                <span className="text-slate-600 dark:text-slate-300" dir="rtl">
                                    {new Date(session.created_at).toLocaleDateString('ar-EG')}
                                </span>
                            </div>
                        </div>

                        <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-2xl text-[10px] font-bold text-slate-400 truncate" title={session.user_agent}>
                            {session.user_agent}
                        </div>
                    </div>
                ))}
            </div>

            {filteredSessions.length === 0 && !loading && (
                <div className="text-center py-20 bg-slate-50 dark:bg-slate-800/20 rounded-[3rem] border-2 border-dashed border-slate-200 dark:border-slate-800">
                    <Monitor size={48} className="mx-auto text-slate-300 mb-4" />
                    <p className="text-slate-500 font-bold">لا توجد جلسات نشطة تطابق البحث</p>
                </div>
            )}
        </div>
    );
}

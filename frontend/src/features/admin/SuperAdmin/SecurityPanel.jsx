import { useState, useEffect } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import { Shield, Lock, Unlock, AlertTriangle, Ban, History, Globe } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, LazyChart } from '@/components/charts/LazyChart';
import { toast, ConfirmDialog, Modal } from '@/shared/ui';
import HealthAlerts from './HealthAlerts';

export default function SecurityPanel() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [stats, setStats] = useState(null);
    const [chartData, setChartData] = useState([]);
    const [blockedIps, setBlockedIps] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showBlockModal, setShowBlockModal] = useState(false);
    const [isBlocking, setIsBlocking] = useState(false);

    // Unblock Confirmation State
    const [unblockTargetIp, setUnblockTargetIp] = useState(null);
    const [isUnblocking, setIsUnblocking] = useState(false);

    // Form State
    const [blockForm, setBlockForm] = useState({ ip_address: '', reason: '' });

    useEffect(() => {
        fetchSecurityData();
    }, []);

    const fetchSecurityData = async () => {
        setLoading(true);
        try {
            const [statsResult, chartResult, ipsResult] = await Promise.allSettled([
                api.get('/api/v1/admin/system/security/stats'),
                api.get('/api/v1/admin/system/security/chart'),
                api.get('/api/v1/admin/security/blocked-ips')
            ]);

            if (statsResult.status === 'fulfilled') {
                setStats(statsResult.value.data?.data || statsResult.value.data || null);
            } else {
                logger.error('Failed to fetch security stats:', statsResult.reason);
            }

            if (chartResult.status === 'fulfilled') {
                const cData = chartResult.value.data?.data || chartResult.value.data;
                setChartData(Array.isArray(cData) ? cData : []);
            } else {
                logger.error('Failed to fetch security chart:', chartResult.reason);
            }

            if (ipsResult.status === 'fulfilled') {
                const ips = ipsResult.value.data?.data || ipsResult.value.data;
                setBlockedIps(Array.isArray(ips) ? ips : []);
            } else {
                logger.error('Failed to fetch blocked IPs:', ipsResult.reason);
            }
        } finally {
            setLoading(false);
        }
    };

    const handleBlockIp = async (e) => {
        if (e) e.preventDefault();
        const ip = blockForm.ip_address.trim();
        if (!ip) {
            toast.error(t('super_admin.security.ip_required') || 'يرجى إدخال عنوان IP');
            return;
        }

        setIsBlocking(true);
        try {
            await api.post('/api/v1/admin/security/ip-block', {
                ip_address: ip,
                reason: blockForm.reason.trim() || 'Administrative block'
            });
            setShowBlockModal(false);
            setBlockForm({ ip_address: '', reason: '' });
            toast.success(t('super_admin.security.block_success') || `تم حظر IP ${ip} بنجاح`);
            fetchSecurityData();
        } catch (error) {
            const detail = error.response?.data?.detail || error.message || t('super_admin.security.block_failed') || 'فشل حظر عنوان IP';
            toast.error(detail);
        } finally {
            setIsBlocking(false);
        }
    };

    const confirmUnblockIp = async () => {
        if (!unblockTargetIp) return;
        setIsUnblocking(true);
        try {
            await api.delete(`/api/v1/admin/security/ip-block/${unblockTargetIp}`);
            toast.success(t('super_admin.security.unblock_success') || `تم إلغاء حظر ${unblockTargetIp} بنجاح`);
            setUnblockTargetIp(null);
            fetchSecurityData();
        } catch (error) {
            const detail = error.response?.data?.detail || error.message || t('super_admin.security.unblock_failed') || 'فشل إلغاء الحظر';
            toast.error(detail);
        } finally {
            setIsUnblocking(false);
        }
    };

    // Dynamically derive security assurance based on real data
    const getAssuranceDetails = () => {
        const lockedCount = stats?.locked_users?.length || 0;
        const failuresCount = stats?.recent_failures?.length || 0;

        if (lockedCount > 3 || failuresCount > 15) {
            return {
                label: t('super_admin.security.level_critical') || 'حرج',
                bg: 'bg-rose-100 dark:bg-rose-900/30',
                text: 'text-rose-600 dark:text-rose-400',
            };
        }
        if (lockedCount > 0 || failuresCount > 3) {
            return {
                label: t('super_admin.security.level_moderate') || 'متوسط',
                bg: 'bg-amber-100 dark:bg-amber-900/30',
                text: 'text-amber-600 dark:text-amber-400',
            };
        }
        return {
            label: t('super_admin.security.level_optimal') || 'ممتاز',
            bg: 'bg-emerald-100 dark:bg-emerald-900/30',
            text: 'text-emerald-600 dark:text-emerald-400',
        };
    };

    const assurance = getAssuranceDetails();

    if (loading && !stats && chartData.length === 0 && blockedIps.length === 0) {
        return <div className="p-8 text-center text-slate-500 font-bold">{t('super_admin.security.loading_msg') || 'جاري تحميل بيانات الأمان...'}</div>;
    }

    return (
        <div className="space-y-8 pb-12" dir={isRtl ? 'rtl' : 'ltr'}>
            {/* Health Overview */}
            <HealthAlerts />

            {/* Header Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 relative overflow-hidden group">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-2xl shrink-0">
                            <Ban size={24} />
                        </div>
                        <div className="text-start">
                            <p className="text-slate-500 dark:text-slate-400 font-bold text-xs">{t('super_admin.security.blocked_ips') || 'عناوين IP المحظورة'}</p>
                            <h3 className="text-2xl font-black text-slate-800 dark:text-white">{stats?.blocked_ips_count ?? blockedIps.length}</h3>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 relative overflow-hidden group">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded-2xl shrink-0">
                            <Lock size={24} />
                        </div>
                        <div className="text-start">
                            <p className="text-slate-500 dark:text-slate-400 font-bold text-xs">{t('super_admin.security.locked_accounts') || 'الحسابات المقفلة'}</p>
                            <h3 className="text-2xl font-black text-slate-800 dark:text-white">{stats?.locked_users?.length || 0}</h3>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 relative overflow-hidden group">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 rounded-2xl shrink-0">
                            <AlertTriangle size={24} />
                        </div>
                        <div className="text-start">
                            <p className="text-slate-500 dark:text-slate-400 font-bold text-xs">{t('super_admin.security.failed_attempts_24h') || 'محاولات فاشلة (24س)'}</p>
                            <h3 className="text-2xl font-black text-slate-800 dark:text-white">{stats?.recent_failures?.length || 0}</h3>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 relative overflow-hidden group">
                    <div className="flex items-center gap-4">
                        <div className={`p-3 ${assurance.bg} ${assurance.text} rounded-2xl shrink-0`}>
                            <Shield size={24} />
                        </div>
                        <div className="text-start">
                            <p className="text-slate-500 dark:text-slate-400 font-bold text-xs">{t('super_admin.security.security_level') || 'مستوى الأمان المحسوب'}</p>
                            <h3 className={`text-2xl font-black ${assurance.text}`}>{assurance.label}</h3>
                        </div>
                    </div>
                </div>
            </div>

            {/* Login Attempts Chart */}
            <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] shadow-sm border border-slate-100 dark:border-slate-800 p-8">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
                    <div className="text-start">
                        <h3 className="text-2xl font-black text-slate-800 dark:text-white">{t('super_admin.security.login_attempts_title') || 'محاولات تسجيل الدخول'}</h3>
                        <p className="text-slate-500 dark:text-slate-400 text-sm font-bold">{t('super_admin.security.login_attempts_subtitle') || 'سجل الدخول الناجح والفاشل خلال الأيام الأخيرة'}</p>
                    </div>
                    <div className="flex gap-4">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-indigo-500"></div>
                            <span className="text-xs font-bold text-slate-500 dark:text-slate-400">{t('super_admin.security.success') || 'ناجح'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-rose-500"></div>
                            <span className="text-xs font-bold text-slate-500 dark:text-slate-400">{t('super_admin.security.failed') || 'فاشل'}</span>
                        </div>
                    </div>
                </div>

                <div className="h-[350px] w-full" dir="ltr">
                    <LazyChart>
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData}>
                                <defs>
                                    <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2}/>
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                                    </linearGradient>
                                    <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.2}/>
                                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" className="text-slate-200 dark:text-slate-800" opacity={0.6} />
                                <XAxis 
                                    dataKey="date" 
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fill: '#94a3b8', fontSize: 12, fontWeight: 600 }}
                                    dy={10}
                                    tickFormatter={(val) => {
                                        try {
                                            return new Date(val).toLocaleDateString(i18n.language, { day: 'numeric', month: 'short' });
                                        } catch {
                                            return val;
                                        }
                                    }}
                                />
                                <YAxis 
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fill: '#94a3b8', fontSize: 12, fontWeight: 600 }}
                                />
                                <Tooltip 
                                    contentStyle={{ 
                                        borderRadius: '1rem', 
                                        border: '1px solid rgba(148, 163, 184, 0.2)', 
                                        boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)', 
                                        backgroundColor: '#1e293b',
                                        color: '#f8fafc'
                                    }}
                                    itemStyle={{ fontWeight: 700, color: '#f8fafc' }}
                                />
                                <Area type="monotone" dataKey="success" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorSuccess)" />
                                <Area type="monotone" dataKey="failed" stroke="#f43f5e" strokeWidth={3} fillOpacity={1} fill="url(#colorFailed)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </LazyChart>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Blocked IPs Table */}
                <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-[2.5rem] shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                    <div className="p-8 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-gradient-to-r from-red-50 to-transparent dark:from-red-950/20">
                        <div className="text-start">
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.security.blacklist_title') || 'القائمة السوداء لـ IP'}</h3>
                            <p className="text-slate-500 dark:text-slate-400 text-sm font-bold">{t('super_admin.security.blacklist_subtitle') || 'إدارة العناوين المحظورة على مستوى النظام'}</p>
                        </div>
                        <button
                            type="button"
                            onClick={() => setShowBlockModal(true)}
                            className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white rounded-2xl font-black text-sm shadow-xl shadow-red-500/20 transition-all active:scale-95 cursor-pointer"
                        >
                            {t('super_admin.security.block_new_ip') || 'حظر IP جديد'}
                        </button>
                    </div>

                    <div className="p-8">
                        {blockedIps.length === 0 ? (
                            <div className="text-center py-12">
                                <div className="w-20 h-20 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <Shield size={40} />
                                </div>
                                <p className="text-slate-500 dark:text-slate-400 font-bold">{t('super_admin.security.no_blocked_ips') || 'لا توجد عناوين IP محظورة حالياً'}</p>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="text-slate-400 text-xs uppercase tracking-widest text-start">
                                            <th className="pb-6 font-black text-start">IP Address</th>
                                            <th className="pb-6 font-black text-start">{t('super_admin.security.reason') || 'السبب'}</th>
                                            <th className="pb-6 font-black text-center">{t('super_admin.security.actions') || 'الإجراء'}</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                        {blockedIps.map(ip => (
                                            <tr key={ip.id || ip.ip_address} className="text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group">
                                                <td className="py-5 text-start">
                                                    <span className="font-mono text-sm bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded-lg text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                                                        {ip.ip_address}
                                                    </span>
                                                </td>
                                                <td className="py-5 font-bold text-sm text-start">{ip.reason || '-'}</td>
                                                <td className="py-5 text-center">
                                                    <button
                                                        type="button"
                                                        onClick={() => setUnblockTargetIp(ip.ip_address)}
                                                        className="p-2 text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-xl transition-all active:scale-90"
                                                        title={t('super_admin.security.unblock') || 'إلغاء الحظر'}
                                                        aria-label={`${t('super_admin.security.unblock') || 'إلغاء الحظر'} ${ip.ip_address}`}
                                                    >
                                                        <Unlock size={20} />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>

                {/* Recent Logs & Alerts */}
                <div className="space-y-8">
                    <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                        <div className="p-8 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3">
                            <History className="text-indigo-500" size={24} />
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.security.failed_attempts_title') || 'أحدث المحاولات الفاشلة'}</h3>
                        </div>
                        <div className="p-6 max-h-[500px] overflow-y-auto space-y-4">
                            {(!stats?.recent_failures || stats.recent_failures.length === 0) ? (
                                <p className="text-sm text-slate-400 text-center py-6">{t('super_admin.security.no_recent_failures') || 'لا توجد محاولات فاشلة مسجلة'}</p>
                            ) : (
                                stats.recent_failures.slice(0, 10).map((log, idx) => (
                                    <div key={log.id || idx} className="p-5 rounded-3xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 group hover:border-red-200 transition-colors">
                                        <div className="flex justify-between items-start mb-3">
                                            <div className="flex flex-col text-start">
                                                <span className="font-mono text-xs font-bold text-red-500">{log.ip_address}</span>
                                                {log.location && (
                                                    <span className="text-[10px] text-slate-500 font-bold flex items-center gap-1">
                                                        <Globe size={10} />
                                                        {log.location.city}, {log.location.country_code}
                                                    </span>
                                                )}
                                            </div>
                                            <span className="text-[10px] text-slate-400 font-bold">
                                                {log.created_at ? new Date(log.created_at).toLocaleTimeString(i18n.language) : ''}
                                            </span>
                                        </div>
                                        <p className="text-xs font-bold text-slate-600 dark:text-slate-400 text-start">
                                            {t('super_admin.security.failed_attempt_msg') || 'فشل في محاولة تسجيل الدخول'}
                                        </p>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Block IP Modal */}
            <Modal
                isOpen={showBlockModal}
                onClose={() => setShowBlockModal(false)}
                title={t('super_admin.security.block_modal_title') || 'حظر عنوان IP'}
                size="md"
            >
                <form onSubmit={handleBlockIp} className="space-y-6 text-start">
                    <div>
                        <label htmlFor="block_ip_input" className="block text-sm font-black text-slate-700 dark:text-slate-300 mb-2">
                            {t('super_admin.security.target_ip') || 'عنوان IP المستهدف'}
                        </label>
                        <input
                            id="block_ip_input"
                            type="text"
                            dir="ltr"
                            placeholder="192.168.1.1 or 2001:db8::1"
                            value={blockForm.ip_address}
                            onChange={(e) => setBlockForm({ ...blockForm, ip_address: e.target.value })}
                            className="w-full px-6 py-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none font-mono text-lg text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-red-500 transition-all"
                            required
                        />
                    </div>
                    <div>
                        <label htmlFor="block_reason_input" className="block text-sm font-black text-slate-700 dark:text-slate-300 mb-2">
                            {t('super_admin.security.block_reason') || 'سبب الحظر'}
                        </label>
                        <textarea
                            id="block_reason_input"
                            rows="3"
                            placeholder={t('super_admin.security.block_reason_placeholder') || 'أدخل سبب الحظر الإداري...'}
                            value={blockForm.reason}
                            onChange={(e) => setBlockForm({ ...blockForm, reason: e.target.value })}
                            className="w-full px-6 py-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none font-bold text-slate-700 dark:text-white focus:ring-2 focus:ring-red-500 transition-all resize-none"
                        />
                    </div>
                    <div className="flex gap-4 pt-2">
                        <button
                            type="submit"
                            disabled={isBlocking || !blockForm.ip_address.trim()}
                            className="flex-1 py-4 bg-red-500 hover:bg-red-600 disabled:bg-slate-400 text-white rounded-2xl font-black shadow-lg shadow-red-500/20 transition-all active:scale-95"
                        >
                            {isBlocking ? (t('common.saving') || 'جاري الحظر...') : (t('super_admin.security.confirm_block') || 'تأكيد الحظر')}
                        </button>
                        <button
                            type="button"
                            onClick={() => setShowBlockModal(false)}
                            className="px-6 py-4 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-2xl font-bold hover:bg-slate-200 dark:hover:bg-slate-700"
                        >
                            {t('common.cancel') || 'إلغاء'}
                        </button>
                    </div>
                </form>
            </Modal>

            {/* Confirm Dialog for Unblocking IP */}
            <ConfirmDialog
                isOpen={!!unblockTargetIp}
                onClose={() => setUnblockTargetIp(null)}
                onConfirm={confirmUnblockIp}
                title={t('super_admin.security.unblock_confirm_title') || 'تأكيد إلغاء حظر IP'}
                message={t('super_admin.security.unblock_confirm_msg', { ip: unblockTargetIp }) || `هل أنت متأكد من رغبتك في إلغاء حظر عنوان IP: ${unblockTargetIp}؟`}
                confirmText={t('super_admin.security.unblock') || 'إلغاء الحظر'}
                cancelText={t('common.cancel') || 'إلغاء'}
                variant="primary"
                isLoading={isUnblocking}
            />
        </div>
    );
}

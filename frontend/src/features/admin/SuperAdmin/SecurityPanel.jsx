import React, { useState, useEffect } from 'react';
import { api } from '@/api';
import { Shield, Lock, Unlock, AlertTriangle, CheckCircle, Search, Ban, History, Globe } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import HealthAlerts from './HealthAlerts';

export default function SecurityPanel() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [stats, setStats] = useState(null);
    const [chartData, setChartData] = useState([]);
    const [blockedIps, setBlockedIps] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showBlockModal, setShowBlockModal] = useState(false);

    // Form State
    const [blockForm, setBlockForm] = useState({ ip_address: '', reason: '' });

    useEffect(() => {
        fetchSecurityData();
    }, []);

    const fetchSecurityData = async () => {
        try {
            setLoading(true);
            const [statsRes, chartRes, ipsRes] = await Promise.all([
                api.get('/api/v1/admin/system/security/stats'),
                api.get('/api/v1/admin/system/security/chart'),
                api.get('/api/v1/admin/security/blocked-ips')
            ]);
            setStats(statsRes.data || null);
            setChartData(chartRes.data || []);
            setBlockedIps(Array.isArray(ipsRes.data) ? ipsRes.data : []);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleBlockIp = async () => {
        if (!blockForm.ip_address) return alert(t('super_admin.security.ip_required'));
        try {
            await api.post('/api/v1/admin/security/ip-block', blockForm);
            setShowBlockModal(false);
            setBlockForm({ ip_address: '', reason: '' });
            fetchSecurityData();
            alert(t('super_admin.security.block_success'));
        } catch (error) {
            alert(t('super_admin.security.block_failed'));
        }
    };

    const handleUnblockIp = async (ip) => {
        if (!window.confirm(t('super_admin.security.unblock_confirm'))) return;
        try {
            await api.delete(`/api/v1/admin/security/ip-block/${ip}`);
            fetchSecurityData();
        } catch (error) {
            alert(t('super_admin.security.unblock_failed'));
        }
    };

    if (loading && !stats) return <div className="p-8 text-center text-slate-500 font-bold">{t('super_admin.security.loading_msg')}</div>;

    return (
        <div className="space-y-8 pb-12">
            {/* Health Overview */}
            <HealthAlerts />

            {/* Header Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 relative overflow-hidden group">
                    <div className={`absolute ${isRtl ? '-left-4' : '-right-4'} -bottom-4 opacity-10 group-hover:scale-110 transition-transform`}>
                        <Ban size={100} />
                    </div>
                    <div className={`flex items-center gap-4 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className="p-3 bg-red-100 dark:bg-red-900/30 text-red-600 rounded-2xl">
                            <Ban size={24} />
                        </div>
                        <div className={isRtl ? 'text-right' : 'text-left'}>
                            <p className="text-slate-500 dark:text-slate-400 font-bold text-xs">{t('super_admin.security.blocked_ips')}</p>
                            <h3 className="text-2xl font-black text-slate-800 dark:text-white">{stats?.blocked_ips_count || 0}</h3>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 relative overflow-hidden group">
                    <div className={`absolute ${isRtl ? '-left-4' : '-right-4'} -bottom-4 opacity-10 group-hover:scale-110 transition-transform`}>
                        <Lock size={100} />
                    </div>
                    <div className={`flex items-center gap-4 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className="p-3 bg-orange-100 dark:bg-orange-900/30 text-orange-600 rounded-2xl">
                            <Lock size={24} />
                        </div>
                        <div className={isRtl ? 'text-right' : 'text-left'}>
                            <p className="text-slate-500 dark:text-slate-400 font-bold text-xs">{t('super_admin.security.locked_accounts')}</p>
                            <h3 className="text-2xl font-black text-slate-800 dark:text-white">{stats?.locked_users?.length || 0}</h3>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 relative overflow-hidden group">
                    <div className={`absolute ${isRtl ? '-left-4' : '-right-4'} -bottom-4 opacity-10 group-hover:scale-110 transition-transform`}>
                        <AlertTriangle size={100} />
                    </div>
                    <div className={`flex items-center gap-4 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className="p-3 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 rounded-2xl">
                            <AlertTriangle size={24} />
                        </div>
                        <div className={isRtl ? 'text-right' : 'text-left'}>
                            <p className="text-slate-500 dark:text-slate-400 font-bold text-xs">{t('super_admin.security.failed_attempts_24h')}</p>
                            <h3 className="text-2xl font-black text-slate-800 dark:text-white">{stats?.recent_failures?.length || 0}</h3>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 relative overflow-hidden group">
                    <div className={`absolute ${isRtl ? '-left-4' : '-right-4'} -bottom-4 opacity-10 group-hover:scale-110 transition-transform`}>
                        <Shield size={100} />
                    </div>
                    <div className={`flex items-center gap-4 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className="p-3 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 rounded-2xl">
                            <Shield size={24} />
                        </div>
                        <div className={isRtl ? 'text-right' : 'text-left'}>
                            <p className="text-slate-500 dark:text-slate-400 font-bold text-xs">{t('super_admin.security.security_level')}</p>
                            <h3 className="text-2xl font-black text-slate-800 dark:text-white">{t('super_admin.security.security_level_high')}</h3>
                        </div>
                    </div>
                </div>
            </div>

            {/* Login Attempts Chart */}
            <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] shadow-sm border border-slate-100 dark:border-slate-800 p-8">
                <div className={`flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8 ${isRtl ? 'md:flex-row-reverse' : ''}`}>
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <h3 className="text-2xl font-black text-slate-800 dark:text-white">{t('super_admin.security.login_attempts_title')}</h3>
                        <p className="text-slate-500 dark:text-slate-400 text-sm font-bold">{t('super_admin.security.login_attempts_subtitle')}</p>
                    </div>
                    <div className={`flex gap-4 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <div className="w-3 h-3 rounded-full bg-indigo-500"></div>
                            <span className="text-xs font-bold text-slate-500">{t('super_admin.security.success')}</span>
                        </div>
                        <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <div className="w-3 h-3 rounded-full bg-rose-500"></div>
                            <span className="text-xs font-bold text-slate-500">{t('super_admin.security.failed')}</span>
                        </div>
                    </div>
                </div>

                <div className="h-[350px] w-full" dir="ltr">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData}>
                            <defs>
                                <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.1}/>
                                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                                </linearGradient>
                                <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.1}/>
                                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" opacity={0.5} />
                            <XAxis 
                                dataKey="date" 
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#64748b', fontSize: 12, fontWeight: 600 }}
                                dy={10}
                                tickFormatter={(val) => new Date(val).toLocaleDateString(isRtl ? 'ar-EG' : 'en-US', { day: 'numeric', month: 'short' })}
                            />
                            <YAxis 
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#64748b', fontSize: 12, fontWeight: 600 }}
                                orientation={isRtl ? 'right' : 'left'}
                            />
                            <Tooltip 
                                contentStyle={{ borderRadius: '1.5rem', border: 'none', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)', backgroundColor: '#fff' }}
                                itemStyle={{ fontWeight: 800 }}
                            />
                            <Area type="monotone" dataKey="success" stroke="#6366f1" strokeWidth={4} fillOpacity={1} fill="url(#colorSuccess)" />
                            <Area type="monotone" dataKey="failed" stroke="#f43f5e" strokeWidth={4} fillOpacity={1} fill="url(#colorFailed)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Blocked IPs Table */}
                <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-[2.5rem] shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                    <div className={`p-8 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-gradient-to-r from-red-50 to-transparent dark:from-red-900/10 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className={isRtl ? 'text-right' : 'text-left'}>
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.security.blacklist_title')}</h3>
                            <p className="text-slate-500 text-sm font-bold">{t('super_admin.security.blacklist_subtitle')}</p>
                        </div>
                        <button
                            onClick={() => setShowBlockModal(true)}
                            className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white rounded-2xl font-black text-sm shadow-xl shadow-red-500/20 transition-all active:scale-95"
                        >
                            {t('super_admin.security.block_new_ip')}
                        </button>
                    </div>

                    <div className="p-8">
                        {blockedIps.length === 0 ? (
                            <div className="text-center py-12">
                                <div className="w-20 h-20 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <Shield size={40} />
                                </div>
                                <p className="text-slate-500 font-bold">{t('super_admin.security.no_blocked_ips')}</p>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full" dir={isRtl ? 'rtl' : 'ltr'}>
                                    <thead>
                                        <tr className={`text-slate-400 text-xs uppercase tracking-widest ${isRtl ? 'text-right' : 'text-left'}`}>
                                            <th className="pb-6 font-black">IP Address</th>
                                            <th className="pb-6 font-black">{t('super_admin.security.reason')}</th>
                                            <th className="pb-6 font-black text-center">{t('super_admin.security.actions')}</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                        {blockedIps.map(ip => (
                                            <tr key={ip.id} className="text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group">
                                                <td className={`py-5 ${isRtl ? 'text-right' : 'text-left'}`}>
                                                    <span className="font-mono text-sm bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded-lg text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                                                        {ip.ip_address}
                                                    </span>
                                                </td>
                                                <td className={`py-5 font-bold text-sm ${isRtl ? 'text-right' : 'text-left'}`}>{ip.reason || '-'}</td>
                                                <td className="py-5 text-center">
                                                    <button
                                                        onClick={() => handleUnblockIp(ip.ip_address)}
                                                        className="p-2 text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-xl transition-all active:scale-90"
                                                        title={t('super_admin.security.unblock')}
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
                        <div className={`p-8 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <History className="text-indigo-500" size={24} />
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">{t('super_admin.security.failed_attempts_title')}</h3>
                        </div>
                        <div className="p-6 max-h-[500px] overflow-y-auto space-y-4">
                            {stats?.recent_failures?.slice(0, 10).map(log => (
                                <div key={log.id} className="p-5 rounded-3xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 group hover:border-red-200 transition-colors">
                                    <div className={`flex justify-between items-start mb-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                        <div className={`flex flex-col ${isRtl ? 'items-end' : 'items-start'}`}>
                                            <span className="font-mono text-xs font-bold text-red-500">{log.ip_address}</span>
                                            {log.location && (
                                                <span className={`text-[10px] text-slate-500 font-bold flex items-center gap-1 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                                    <Globe size={10} />
                                                    {log.location.city}, {log.location.country_code}
                                                </span>
                                            )}
                                        </div>
                                        <span className="text-[10px] text-slate-400 font-bold">{new Date(log.created_at).toLocaleTimeString(isRtl ? 'ar-EG' : 'en-US')}</span>
                                    </div>
                                    <p className={`text-xs font-bold text-slate-600 dark:text-slate-400 ${isRtl ? 'text-right' : 'text-left'}`}>{t('super_admin.security.failed_attempt_msg')}</p>
                                    <div className={`mt-3 flex items-center justify-between ${isRtl ? 'flex-row-reverse' : ''}`}>
                                        <span className="text-[10px] bg-slate-200 dark:bg-slate-700 px-2 py-1 rounded-full text-slate-500">ID: {log.user_id || 'N/A'}</span>
                                        <button className="text-[10px] text-indigo-600 font-black hover:underline">{t('super_admin.security.view_details')}</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Quick Security Actions */}
                    <div className="bg-indigo-600 rounded-[2.5rem] p-8 text-white relative overflow-hidden">
                        <div className={`absolute ${isRtl ? 'left-0' : 'right-0'} top-0 opacity-10`}>
                            <Shield size={150} />
                        </div>
                        <div className={isRtl ? 'text-right' : 'text-left'}>
                            <h4 className="text-xl font-black mb-2">{t('super_admin.security.quick_actions')}</h4>
                            <p className="text-indigo-100 text-sm font-bold mb-6">{t('super_admin.security.quick_actions_subtitle')}</p>
                            <div className="space-y-3 relative z-10">
                                <button className="w-full py-3 bg-white/10 hover:bg-white/20 rounded-2xl text-sm font-black transition-colors flex items-center justify-center gap-2">
                                    <Globe size={18} />
                                    {t('super_admin.security.check_firewall')}
                                </button>
                                <button className="w-full py-3 bg-white/10 hover:bg-white/20 rounded-2xl text-sm font-black transition-colors flex items-center justify-center gap-2">
                                    <Lock size={18} />
                                    {t('super_admin.security.close_active_sessions')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Block Modal */}
            {showBlockModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-md p-4 animate-in fade-in zoom-in duration-300">
                    <div className="bg-white dark:bg-slate-900 rounded-[3rem] p-10 w-full max-w-lg shadow-2xl border border-white/20">
                        <div className={`w-16 h-16 bg-red-100 text-red-500 rounded-3xl flex items-center justify-center mb-6 ${isRtl ? 'mr-0 ml-auto' : ''}`}>
                            <Ban size={32} />
                        </div>
                        <div className={isRtl ? 'text-right' : 'text-left'}>
                            <h3 className="text-3xl font-black text-slate-800 dark:text-white mb-2">{t('super_admin.security.block_modal_title')}</h3>
                            <p className="text-slate-500 font-bold mb-8 text-lg">{t('super_admin.security.block_modal_subtitle')}</p>

                            <div className="space-y-6">
                                <div>
                                    <label className="block text-sm font-black text-slate-500 mb-2">{t('super_admin.security.target_ip')}</label>
                                    <input
                                        type="text"
                                        dir="ltr"
                                        placeholder="192.168.1.1"
                                        value={blockForm.ip_address}
                                        onChange={(e) => setBlockForm({ ...blockForm, ip_address: e.target.value })}
                                        className={`w-full px-6 py-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none font-mono text-lg focus:ring-4 focus:ring-red-500/10 transition-all ${isRtl ? 'text-right' : 'text-left'}`}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-black text-slate-500 mb-2">{t('super_admin.security.block_reason')}</label>
                                    <textarea
                                        rows="3"
                                        placeholder={t('super_admin.security.block_reason_placeholder')}
                                        value={blockForm.reason}
                                        onChange={(e) => setBlockForm({ ...blockForm, reason: e.target.value })}
                                        className={`w-full px-6 py-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none font-bold text-slate-700 dark:text-white focus:ring-4 focus:ring-red-500/10 transition-all resize-none ${isRtl ? 'text-right' : 'text-left'}`}
                                    />
                                </div>
                                <div className={`flex gap-4 pt-4 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                    <button
                                        onClick={handleBlockIp}
                                        className="flex-[2] py-5 bg-red-500 hover:bg-red-600 text-white rounded-3xl font-black shadow-2xl shadow-red-500/30 transition-all active:scale-95"
                                    >
                                        {t('super_admin.security.confirm_block')}
                                    </button>
                                    <button
                                        onClick={() => setShowBlockModal(false)}
                                        className="flex-1 py-5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-3xl font-black transition-all"
                                    >
                                        {t('super_admin.security.cancel')}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

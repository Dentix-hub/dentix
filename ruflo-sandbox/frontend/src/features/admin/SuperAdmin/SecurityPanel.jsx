import React, { useState, useEffect } from 'react';
import { api } from '@/api';
import { Shield, Lock, Unlock, AlertTriangle, CheckCircle, Search, Ban, History } from 'lucide-react';

export default function SecurityPanel() {
    const [stats, setStats] = useState(null);
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
            const [statsRes, ipsRes] = await Promise.all([
                api.get('/api/v1/admin/security/stats'),
                api.get('/api/v1/admin/security/blocked-ips')
            ]);
            setStats(statsRes.data || null);
            setBlockedIps(Array.isArray(ipsRes.data) ? ipsRes.data : []);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleBlockIp = async () => {
        if (!blockForm.ip_address) return alert("الرجاء إدخال عنوان IP");
        try {
            await api.post('/api/v1/admin/security/ip-block', blockForm);
            setShowBlockModal(false);
            setBlockForm({ ip_address: '', reason: '' });
            fetchSecurityData();
            alert("تم حظر IP بنجاح");
        } catch (error) {
            alert("فشلت عملية الحظر");
        }
    };

    const handleUnblockIp = async (ip) => {
        if (!window.confirm("هل أنت متأكد من فك الحظر؟")) return;
        try {
            await api.delete(`/api/v1/admin/security/ip-block/${ip}`);
            fetchSecurityData();
        } catch (error) {
            alert("فشل فك الحظر");
        }
    };

    if (loading && !stats) return <div className="p-8 text-center text-slate-500">جاري تحميل البيانات الأمنية...</div>;

    return (
        <div className="space-y-8">
            {/* Header Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center gap-4">
                    <div className="p-4 bg-red-100 dark:bg-red-900/30 text-red-600 rounded-2xl">
                        <Ban size={28} />
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400 font-bold text-sm">عناوين IP المحظورة</p>
                        <h3 className="text-3xl font-black text-slate-800 dark:text-white">{stats?.blocked_ips_count || 0}</h3>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center gap-4">
                    <div className="p-4 bg-orange-100 dark:bg-orange-900/30 text-orange-600 rounded-2xl">
                        <Lock size={28} />
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400 font-bold text-sm">حسابات مقفلة حالياً</p>
                        <h3 className="text-3xl font-black text-slate-800 dark:text-white">{stats?.locked_users?.length || 0}</h3>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center gap-4">
                    <div className="p-4 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 rounded-2xl">
                        <AlertTriangle size={28} />
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400 font-bold text-sm">محاولات فاشلة حديثاً</p>
                        <h3 className="text-3xl font-black text-slate-800 dark:text-white">{stats?.recent_failures?.length || 0}</h3>
                    </div>
                </div>
            </div>

            <div className="flex flex-col lg:flex-row gap-8">
                {/* Blocked IPs List */}
                <div className="flex-1 bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                    <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-gradient-to-r from-red-50 to-transparent dark:from-red-900/10">
                        <div className="flex items-center gap-3">
                            <Ban className="text-red-500" size={24} />
                            <h3 className="text-xl font-bold text-slate-800 dark:text-white">قائمة الحظر (Blacklist)</h3>
                        </div>
                        <button
                            onClick={() => setShowBlockModal(true)}
                            className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-xl font-bold text-sm shadow-lg shadow-red-500/20 transition-all"
                        >
                            حظر عنوان جديد
                        </button>
                    </div>

                    <div className="p-6">
                        {blockedIps.length === 0 ? (
                            <div className="text-center py-8 text-slate-400">
                                <CheckCircle className="mx-auto mb-2 text-emerald-500" size={32} />
                                <p>لا توجد عناوين محظورة حالياً</p>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="text-right text-slate-500 text-sm">
                                            <th className="pb-4 font-bold">IP Address</th>
                                            <th className="pb-4 font-bold">السبب</th>
                                            <th className="pb-4 font-bold">بواسطة</th>
                                            <th className="pb-4 font-bold">تحكم</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                        {blockedIps.map(ip => (
                                            <tr key={ip.id} className="text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                                <td className="py-4 font-mono dir-ltr text-left pl-2">{ip.ip_address}</td>
                                                <td className="py-4">{ip.reason || '-'}</td>
                                                <td className="py-4 text-sm text-slate-500">{ip.blocked_by}</td>
                                                <td className="py-4">
                                                    <button
                                                        onClick={() => handleUnblockIp(ip.ip_address)}
                                                        className="p-2 text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-lg transition-colors"
                                                        title="فك الحظر"
                                                    >
                                                        <Unlock size={18} />
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

                {/* Recent Failed Logins */}
                <div className="lg:w-1/3 bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                    <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3">
                        <History className="text-slate-500" size={24} />
                        <h3 className="text-xl font-bold text-slate-800 dark:text-white">آخر المحاولات الفاشلة</h3>
                    </div>
                    <div className="p-4 max-h-[500px] overflow-y-auto space-y-3">
                        {stats?.recent_failures?.map(log => (
                            <div key={log.id} className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                                <div className="flex justify-between items-start mb-2">
                                    <span className="font-mono text-sm bg-slate-200 dark:bg-slate-700 px-2 py-1 rounded text-slate-600 dark:text-slate-300">{log.ip_address}</span>
                                    <span className="text-xs text-slate-400 font-medium" dir="ltr">{new Date(log.created_at).toLocaleString()}</span>
                                </div>
                                <div className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2">
                                    <AlertTriangle size={14} className="text-red-500" />
                                    <span>User ID: {log.user_id || 'Unknown'}</span>
                                </div>
                            </div>
                        ))}
                        {(!stats?.recent_failures || stats.recent_failures.length === 0) && (
                            <div className="text-center py-8 text-slate-400">
                                <p>سجل نظيف! لا توجد محاولات فاشلة.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Block Modal */}
            {showBlockModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 w-full max-w-md shadow-2xl space-y-6">
                        <h3 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                            <Ban className="text-red-500" />
                            حظر عنوان IP جديد
                        </h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">IP Address</label>
                                <input
                                    type="text"
                                    dir="ltr"
                                    placeholder="192.168.1.1"
                                    value={blockForm.ip_address}
                                    onChange={(e) => setBlockForm({ ...blockForm, ip_address: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none font-mono"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">سبب الحظر</label>
                                <input
                                    type="text"
                                    placeholder="محاولات اختراق، سبام..."
                                    value={blockForm.reason}
                                    onChange={(e) => setBlockForm({ ...blockForm, reason: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none"
                                />
                            </div>
                            <div className="flex gap-3 mt-4">
                                <button
                                    onClick={handleBlockIp}
                                    className="flex-1 py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl font-bold shadow-lg shadow-red-500/20"
                                >
                                    تأكيد الحظر
                                </button>
                                <button
                                    onClick={() => setShowBlockModal(false)}
                                    className="px-6 py-3 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl font-bold"
                                >
                                    إلغاء
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}


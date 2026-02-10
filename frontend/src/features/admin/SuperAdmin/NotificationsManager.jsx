import { useState, useEffect } from 'react';
import { Send, Bell, Trash2 } from 'lucide-react';
import { api, broadcastNotification, deleteNotification } from '@/api';
const NotificationsManager = () => {
    const [notifications, setNotifications] = useState([]);
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    // Form State
    const [notifForm, setNotifForm] = useState({
        title: '',
        content: '',
        type: 'info',
        is_global: true,
        tenant_id: null
    });
    useEffect(() => {
        fetchData();
    }, []);
    const fetchData = async () => {
        try {
            setLoading(true);
            const [notifRes, tenantsRes] = await Promise.all([
                api.get('/api/v1/notifications/'),
                api.get('/api/v1/admin/tenants')
            ]);
            setNotifications(Array.isArray(notifRes.data) ? notifRes.data : []);
            setTenants(Array.isArray(tenantsRes.data) ? tenantsRes.data : []);
        } catch (err) {
            console.error("Failed to fetch data for notifications manager", err);
        } finally {
            setLoading(false);
        }
    };
    const handleSendNotification = async () => {
        if (!notifForm.title || !notifForm.content) return alert('الرجاء تعبئة العنوان والمحتوى');
        try {
            await broadcastNotification(notifForm);
            setNotifForm({ title: '', content: '', type: 'info', is_global: true, tenant_id: null });
            fetchData(); // Refresh list
            alert('تم إرسال الإشعار بنجاح');
        } catch (err) {
            console.error(err);
            alert('فشل إرسال الإشعار');
        }
    };
    const handleDeleteNotification = async (id) => {
        if (!window.confirm('هل أنت متأكد من حذف هذا الإشعار؟')) return;
        try {
            await deleteNotification(id);
            setNotifications(prev => prev.filter(n => n.id !== id));
        } catch (err) {
            console.error(err);
            alert('فشل حذف الإشعار');
        }
    };
    if (loading) return <div className="p-10 text-center text-slate-500 animate-pulse">جاري تحميل الإشعارات...</div>;
    return (
        <div className="space-y-8 animate-fade-in text-right">
            <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm">
                <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                    <Send className="text-indigo-500" />
                    إرسال إشعار جديد للنظام
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-bold text-slate-600 dark:text-slate-400 mb-2">عنوان الإشعار</label>
                            <input
                                type="text"
                                value={notifForm.title}
                                onChange={(e) => setNotifForm({ ...notifForm, title: e.target.value })}
                                className="w-full px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                                placeholder="مثال: تحديث جديد للنظام"
                            />
                        </div>
                        <div className="flex gap-4">
                            <div className="flex-1">
                                <label className="block text-sm font-bold text-slate-600 dark:text-slate-400 mb-2">نوع التنبيه</label>
                                <select
                                    value={notifForm.type}
                                    onChange={(e) => setNotifForm({ ...notifForm, type: e.target.value })}
                                    className="w-full px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none font-bold cursor-pointer"
                                >
                                    <option value="info">ℹ️ معلومة</option>
                                    <option value="warning">⚠️ تحذير</option>
                                    <option value="success">✅ نجاح</option>
                                    <option value="error">❌ خطأ (هام)</option>
                                    <option value="system">⚙️ نظام</option>
                                </select>
                            </div>
                            <div className="flex-1">
                                <label className="block text-sm font-bold text-slate-600 dark:text-slate-400 mb-2">المستهدف</label>
                                <select
                                    value={notifForm.is_global ? 'all' : 'specific'}
                                    onChange={(e) => setNotifForm({ ...notifForm, is_global: e.target.value === 'all' })}
                                    className="w-full px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none font-bold cursor-pointer"
                                >
                                    <option value="all">🌍 جميع العيادات</option>
                                    <option value="specific">🏥 عيادة محددة</option>
                                </select>
                            </div>
                        </div>
                        {!notifForm.is_global && (
                            <div>
                                <label className="block text-sm font-bold text-slate-600 dark:text-slate-400 mb-2">اختر العيادة</label>
                                <select
                                    value={notifForm.tenant_id || ''}
                                    onChange={(e) => setNotifForm({ ...notifForm, tenant_id: parseInt(e.target.value) })}
                                    className="w-full px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none font-bold cursor-pointer"
                                >
                                    <option value="" disabled>اختر العيادة...</option>
                                    {(tenants || []).map(t => (
                                        <option key={t.id} value={t.id}>{t.name}</option>
                                    ))}
                                </select>
                            </div>
                        )}
                    </div>
                    <div className="flex flex-col">
                        <label className="block text-sm font-bold text-slate-600 dark:text-slate-400 mb-2">محتوى الرسالة</label>
                        <textarea
                            value={notifForm.content}
                            onChange={(e) => setNotifForm({ ...notifForm, content: e.target.value })}
                            className="flex-1 px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none min-h-[150px]"
                            placeholder="اكتب تفاصيل الإشعار هنا..."
                        />
                        <button
                            onClick={handleSendNotification}
                            className="mt-4 w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20 transition-all"
                        >
                            <Bell size={20} />
                            بث الإشعار الآن
                        </button>
                    </div>
                </div>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm overflow-hidden">
                <div className="p-6 border-b border-slate-50 dark:border-slate-800">
                    <h3 className="font-bold text-slate-800 dark:text-white">سجل الإشعارات المرسلة</h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-right">
                        <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 text-xs font-bold uppercase">
                            <tr>
                                <th className="p-4">التاريخ</th>
                                <th className="p-4">العنوان</th>
                                <th className="p-4">النوع</th>
                                <th className="p-4">النطاق</th>
                                <th className="p-4 text-center">إجراءات</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {notifications.length > 0 ? notifications.map(notif => (
                                <tr key={notif.id} className="hover:bg-slate-50/50 transition-colors">
                                    <td className="p-4 text-sm text-slate-500">
                                        {new Date(notif.created_at).toLocaleDateString('ar-EG')}
                                    </td>
                                    <td className="p-4 font-bold text-slate-800 dark:text-white">{notif.title}</td>
                                    <td className="p-4">
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${notif.type === 'error' ? 'bg-rose-100 text-rose-600' :
                                            notif.type === 'warning' ? 'bg-amber-100 text-amber-600' :
                                                'bg-blue-100 text-blue-600'
                                            }`}>
                                            {notif.type}
                                        </span>
                                    </td>
                                    <td className="p-4 text-sm">
                                        {notif.is_global ? '🌍 الكل' : '🏥 عيادة محددة'}
                                    </td>
                                    <td className="p-4 text-center">
                                        <button
                                            onClick={() => handleDeleteNotification(notif.id)}
                                            className="text-rose-500 hover:bg-rose-50 p-2 rounded-lg transition-colors"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan="5" className="p-10 text-center text-slate-400">لا توجد إشعارات سابقة</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};
export default NotificationsManager;

import { useEffect, useState } from 'react';
import { api, broadcastNotification, deleteNotification, deleteSupportMessage } from '@/api';
import SupportInbox from '@/features/admin/SuperAdmin/SupportInbox';
import NotificationsManager from '@/features/admin/SuperAdmin/NotificationsManager';
import { MessageSquare } from 'lucide-react';
export default function CommunicationsPage() {
    const [activeTab, setActiveTab] = useState('messages');
    const [messages, setMessages] = useState([]);
    const [notifications, setNotifications] = useState([]);
    const [tenants, setTenants] = useState([]); // Needed for notification targeting
    const [notifForm, setNotifForm] = useState({ title: '', content: '', type: 'info', is_global: true, tenant_id: null });
    const [loading, setLoading] = useState(true);
    const fetchData = async () => {
        setLoading(true);
        try {
            const [msgRes, notifRes, tenRes] = await Promise.all([
                api.get('/support/messages'),
                api.get('/api/v1/notifications/'),
                api.get('/api/v1/admin/tenants')
            ]);
            setMessages(Array.isArray(msgRes.data) ? msgRes.data : []);
            setNotifications(Array.isArray(notifRes.data) ? notifRes.data : []);
            setTenants(Array.isArray(tenRes.data) ? tenRes.data : []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };
    useEffect(() => {
        fetchData();
    }, []);
    const handleDeleteMessage = async (id) => {
        if (!window.confirm('هل أنت متأكد من حذف هذه الرسالة؟')) return;
        try {
            await deleteSupportMessage(id);
            setMessages(prev => prev.filter(m => m.id !== id));
            alert('تم حذف الرسالة بنجاح');
        } catch (err) {
            alert('فشل حذف الرسالة');
        }
    };
    const handleSendNotification = async () => {
        if (!notifForm.title || !notifForm.content) return alert('الرجاء تعبئة العنوان والمحتوى');
        try {
            await broadcastNotification(notifForm);
            setNotifForm({ title: '', content: '', type: 'info', is_global: true, tenant_id: null });
            fetchData();
            alert('تم إرسال الإشعار بنجاح');
        } catch (err) {
            alert('فشل إرسال الإشعار');
        }
    };
    const handleDeleteNotification = async (id) => {
        if (!window.confirm('هل أنت متأكد من حذف هذا الإشعار؟')) return;
        try {
            await deleteNotification(id);
            fetchData();
        } catch (err) {
            alert('فشل حذف الإشعار');
        }
    };
    if (loading) return <div className="p-8 text-center text-slate-500">جاري تحميل الرسائل...</div>;
    return (
        <div className="space-y-6 animate-fade-in-up">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-4">
                    <div className="bg-teal-50 dark:bg-teal-900/20 p-4 rounded-2xl text-teal-600 dark:text-teal-400">
                        <MessageSquare size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-black text-slate-800 dark:text-white">التواصل والدعم</h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">رسائل الدعم الفني والإشعارات</p>
                    </div>
                </div>
                <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
                    <button
                        onClick={() => setActiveTab('messages')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'messages' ? 'bg-white dark:bg-slate-700 shadow text-teal-600' : 'text-slate-500'}`}
                    >
                        الرسائل
                    </button>
                    <button
                        onClick={() => setActiveTab('notifications')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'notifications' ? 'bg-white dark:bg-slate-700 shadow text-teal-600' : 'text-slate-500'}`}
                    >
                        الإشعارات
                    </button>
                </div>
            </div>
            {activeTab === 'messages' ? (
                <SupportInbox
                    messages={messages}
                    setMessages={setMessages}
                    handleDeleteMessage={handleDeleteMessage}
                    fetchData={fetchData}
                />
            ) : (
                <NotificationsManager
                    notifForm={notifForm}
                    setNotifForm={setNotifForm}
                    handleSendNotification={handleSendNotification}
                    notifications={notifications}
                    handleDeleteNotification={handleDeleteNotification}
                    tenants={tenants}
                />
            )}
        </div>
    );
}


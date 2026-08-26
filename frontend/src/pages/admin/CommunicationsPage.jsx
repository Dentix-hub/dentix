import { useEffect, useState, useCallback } from 'react';
import logger from '@/utils/logger';
import { api, broadcastNotification, deleteNotification, deleteSupportMessage, getNotifications, getSupportMessages } from '@/api';
import SupportInbox from '@/features/admin/SuperAdmin/SupportInbox';
import NotificationsManager from '@/features/admin/SuperAdmin/NotificationsManager';
import { MessageSquare } from 'lucide-react';
import { toast } from '@/shared/ui';
import { useTranslation } from 'react-i18next';

export default function CommunicationsPage() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    const [activeTab, setActiveTab] = useState('messages');
    const [messages, setMessages] = useState([]);
    const [notifications, setNotifications] = useState([]);
    const [tenants, setTenants] = useState([]);
    const [notifForm, setNotifForm] = useState({ title: '', content: '', type: 'info', is_global: true, tenant_id: null });
    const [loading, setLoading] = useState(true);
    const [isSending, setIsSending] = useState(false);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [msgResult, notifResult, tenantResult] = await Promise.allSettled([
                getSupportMessages(),
                getNotifications(),
                api.get('/api/v1/admin/tenants')
            ]);

            if (msgResult.status === 'fulfilled') {
                const resData = msgResult.value?.data?.data || msgResult.value?.data;
                setMessages(Array.isArray(resData) ? resData : []);
            } else {
                logger.error('Failed to load support messages', msgResult.reason);
            }

            if (notifResult.status === 'fulfilled') {
                const resData = notifResult.value?.data?.data || notifResult.value?.data;
                setNotifications(Array.isArray(resData) ? resData : []);
            } else {
                logger.error('Failed to load notifications', notifResult.reason);
            }

            if (tenantResult.status === 'fulfilled') {
                const resData = tenantResult.value?.data?.data || tenantResult.value?.data;
                setTenants(Array.isArray(resData) ? resData : []);
            } else {
                logger.error('Failed to load tenants', tenantResult.reason);
            }
        } catch (err) {
            logger.error('Error fetching communications data:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleDeleteMessage = async (id) => {
        try {
            await deleteSupportMessage(id);
            setMessages(prev => prev.filter(m => m.id !== id));
            toast.success(t('super_admin.support.success_deleted') || 'تم حذف الرسالة بنجاح');
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || t('super_admin.support.error_deleting') || 'فشل حذف الرسالة';
            toast.error(errorMsg);
            throw err;
        }
    };

    const handleSendNotification = async () => {
        if (isSending) return;

        if (!notifForm.title?.trim() || !notifForm.content?.trim()) {
            toast.error(t('super_admin.notifications.error_fill_required') || 'الرجاء تعبئة العنوان والمحتوى');
            return;
        }

        if (!notifForm.is_global && !notifForm.tenant_id) {
            toast.error(t('super_admin.notifications.error_select_tenant') || 'الرجاء تحديد العيادة المستهدفة');
            return;
        }

        setIsSending(true);
        try {
            const payload = {
                title: notifForm.title.trim(),
                content: notifForm.content.trim(),
                type: notifForm.type,
                is_global: Boolean(notifForm.is_global),
                tenant_id: notifForm.is_global ? null : parseInt(notifForm.tenant_id, 10),
            };
            await broadcastNotification(payload);
            setNotifForm({ title: '', content: '', type: 'info', is_global: true, tenant_id: null });
            fetchData();
            toast.success(t('super_admin.notifications.success_sent') || 'تم إرسال الإشعار بنجاح');
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.response?.data?.message || err.message || t('super_admin.notifications.error_sending') || 'فشل إرسال الإشعار';
            toast.error(errorMsg);
        } finally {
            setIsSending(false);
        }
    };

    const handleDeleteNotification = async (id) => {
        try {
            await deleteNotification(id);
            setNotifications(prev => prev.filter(n => n.id !== id));
            toast.success(t('super_admin.notifications.success_deleted') || 'تم حذف الإشعار بنجاح');
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || t('super_admin.notifications.error_deleting') || 'فشل حذف الإشعار';
            toast.error(errorMsg);
            throw err;
        }
    };

    if (loading) return (
        <div className="p-8 text-center text-slate-500 font-bold animate-pulse">
            {t('super_admin.communications.loading') || 'جاري تحميل الرسائل والإشعارات...'}
        </div>
    );

    return (
        <div className="space-y-6 animate-fade-in-up" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-4">
                    <div className="bg-teal-50 dark:bg-teal-900/20 p-4 rounded-2xl text-teal-600 dark:text-teal-400">
                        <MessageSquare size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white">
                            {t('super_admin.communications.title') || 'التواصل والدعم'}
                        </h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">
                            {t('super_admin.communications.subtitle') || 'رسائل الدعم الفني والإشعارات'}
                        </p>
                    </div>
                </div>
                <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
                    <button
                        onClick={() => setActiveTab('messages')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'messages' ? 'bg-white dark:bg-slate-700 shadow text-teal-600 dark:text-teal-400' : 'text-slate-500 dark:text-slate-400'}`}
                    >
                        {t('super_admin.communications.tabs.messages') || 'الرسائل'}
                    </button>
                    <button
                        onClick={() => setActiveTab('notifications')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'notifications' ? 'bg-white dark:bg-slate-700 shadow text-teal-600 dark:text-teal-400' : 'text-slate-500 dark:text-slate-400'}`}
                    >
                        {t('super_admin.communications.tabs.notifications') || 'الإشعارات'}
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
                    isSending={isSending}
                />
            )}
        </div>
    );
}

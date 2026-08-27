import { useState } from 'react';
import { MessageSquare, AlertCircle, ShieldCheck, Trash2, Eye, User, Building2, Calendar, Tag } from 'lucide-react';
import { updateMessageStatus } from '@/api';
import { useTranslation } from 'react-i18next';
import logger from '@/utils/logger';
import { Modal, ConfirmDialog, toast } from '@/shared/ui';

const SupportInbox = ({ messages = [], setMessages, handleDeleteMessage, fetchData }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    const [viewingMessage, setViewingMessage] = useState(null);
    const [messageToDelete, setMessageToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const handleViewMessage = async (msg) => {
        setViewingMessage(msg);

        if (msg.status === 'unread') {
            try {
                await updateMessageStatus(msg.id, 'read');
                if (typeof setMessages === 'function') {
                    setMessages(current => current.map(item => (
                        item.id === msg.id ? { ...item, status: 'read' } : item
                    )));
                }
            } catch (error) {
                logger.error('Failed to mark support message as read', error);
                toast.error(t('super_admin.support.error_updating_status') || 'فشل تحديث حالة الرسالة');
                if (fetchData) await fetchData();
            }
        }
    };

    const confirmDelete = async () => {
        if (!messageToDelete) return;
        setIsDeleting(true);
        try {
            if (handleDeleteMessage) {
                await handleDeleteMessage(messageToDelete.id);
            }
            setMessageToDelete(null);
        } catch (err) {
            logger.error('Failed to delete support message:', err);
        } finally {
            setIsDeleting(false);
        }
    };

    const safeMessages = Array.isArray(messages) ? messages : [];
    const unreadCount = safeMessages.filter(m => m.status === 'unread').length;
    const highPriorityCount = safeMessages.filter(m => m.priority === 'high').length;

    return (
        <div className={`space-y-8 animate-fade-in ${isRtl ? 'text-right' : 'text-left'}`} dir={isRtl ? 'rtl' : 'ltr'}>
            {/* Messages Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm flex items-center justify-between">
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <p className="text-slate-500 dark:text-slate-400 font-bold text-sm mb-1">{t('super_admin.support.total_messages') || 'إجمالي الرسائل'}</p>
                        <p className="text-3xl font-bold text-slate-800 dark:text-white">{safeMessages.length}</p>
                    </div>
                    <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-2xl">
                        <MessageSquare size={24} />
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm flex items-center justify-between">
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <p className="text-slate-500 dark:text-slate-400 font-bold text-sm mb-1">{t('super_admin.support.unread_messages') || 'رسائل غير مقروءة'}</p>
                        <p className="text-3xl font-bold text-rose-600 dark:text-rose-400">{unreadCount}</p>
                    </div>
                    <div className="p-4 bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 rounded-2xl">
                        <AlertCircle size={24} />
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm flex items-center justify-between">
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <p className="text-slate-500 dark:text-slate-400 font-bold text-sm mb-1">{t('super_admin.support.high_priority') || 'أولوية عاجلة'}</p>
                        <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">{highPriorityCount}</p>
                    </div>
                    <div className="p-4 bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 rounded-2xl">
                        <ShieldCheck size={24} />
                    </div>
                </div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                <div className="p-6 border-b border-slate-50 dark:border-slate-800 flex justify-between items-center">
                    <h3 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        <MessageSquare className="text-indigo-500" size={20} />
                        {t('super_admin.support.title') || 'صندوق رسائل الدعم الفني'}
                    </h3>
                    <span className="text-xs font-bold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded-full">
                        {safeMessages.length} {t('super_admin.support.total_messages') || 'رسائل'}
                    </span>
                </div>
                <div className="overflow-x-auto">
                    <table className={`w-full ${isRtl ? 'text-right' : 'text-left'}`}>
                        <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase">
                            <tr>
                                <th className="p-6">{t('super_admin.support.date_col') || 'التاريخ'}</th>
                                <th className="p-6">{t('super_admin.support.sender_col') || 'المرسل'}</th>
                                <th className="p-6">{t('super_admin.support.clinic_col') || 'العيادة'}</th>
                                <th className="p-6">{t('super_admin.support.subject_col') || 'الموضوع'}</th>
                                <th className="p-6">{t('super_admin.support.priority_col') || 'الأولوية'}</th>
                                <th className="p-6">{t('super_admin.support.status_col') || 'الحالة'}</th>
                                <th className="p-6 text-center">{t('super_admin.support.actions_col') || 'الإجراءات'}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {safeMessages.length > 0 ? safeMessages.map(msg => (
                                <tr key={msg.id} className={`hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors ${msg.status === 'unread' ? 'bg-indigo-50/30 dark:bg-indigo-900/10 font-bold' : ''}`}>
                                    <td className="p-6 text-sm text-slate-500 dark:text-slate-400 whitespace-nowrap">
                                        {msg.created_at ? new Date(msg.created_at).toLocaleString(i18n.language === 'ar' ? 'ar-EG' : 'en-US') : '-'}
                                    </td>
                                    <td className="p-6 font-bold text-slate-800 dark:text-slate-200">{msg.username || '-'}</td>
                                    <td className="p-6 font-medium text-indigo-600 dark:text-indigo-400">{msg.clinic_name || '-'}</td>
                                    <td className="p-6">
                                        <div className="flex flex-col">
                                            <span className="font-bold text-slate-800 dark:text-white">{msg.subject}</span>
                                            <span className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-xs">{msg.message}</span>
                                        </div>
                                    </td>
                                    <td className="p-6 whitespace-nowrap">
                                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${msg.priority === 'high' ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300' :
                                            msg.priority === 'normal' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' :
                                                'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                                            }`}>
                                            {t(`super_admin.support.${msg.priority}`) || msg.priority}
                                        </span>
                                    </td>
                                    <td className="p-6 whitespace-nowrap">
                                        <span className={`px-3 py-1 rounded-lg text-xs font-bold ${msg.status === 'unread' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                                            {t(`super_admin.support.${msg.status}`) || msg.status}
                                        </span>
                                    </td>
                                    <td className="p-6 text-center whitespace-nowrap">
                                        <div className="flex items-center justify-center gap-2">
                                            <button
                                                type="button"
                                                onClick={() => handleViewMessage(msg)}
                                                className="inline-flex items-center gap-1 px-3 py-1.5 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-xl transition-all font-bold text-xs"
                                                title={t('super_admin.support.view_details') || 'عرض التفاصيل'}
                                                aria-label={t('super_admin.support.view_details') || 'عرض التفاصيل'}
                                            >
                                                <Eye size={16} />
                                                {t('super_admin.support.view_details') || 'عرض'}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setMessageToDelete(msg)}
                                                className="p-2 hover:bg-rose-50 dark:hover:bg-rose-900/30 text-rose-500 rounded-xl transition-all"
                                                title={t('super_admin.support.delete_msg') || 'حذف'}
                                                aria-label={t('super_admin.support.delete_msg') || 'حذف'}
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan="7" className="p-20 text-center text-slate-500 dark:text-slate-400 font-bold">
                                        {t('super_admin.support.no_messages') || 'لا توجد رسائل دعم فني'} 📬
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Shared Accessible Message Detail Modal */}
            <Modal
                isOpen={Boolean(viewingMessage)}
                onClose={() => setViewingMessage(null)}
                title={viewingMessage?.subject || t('super_admin.support.view_details') || 'تفاصيل الرسالة'}
                maxWidth="max-w-lg"
            >
                {viewingMessage && (
                    <div className="space-y-6" dir={isRtl ? 'rtl' : 'ltr'}>
                        <div className="grid grid-cols-2 gap-4 bg-slate-50 dark:bg-slate-800/50 p-4 rounded-2xl border border-slate-100 dark:border-slate-800 text-sm">
                            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                                <User size={16} className="text-indigo-500" />
                                <span className="font-bold">{t('super_admin.support.sender_col') || 'المرسل'}:</span>
                                <span>{viewingMessage.username || '-'}</span>
                            </div>
                            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                                <Building2 size={16} className="text-indigo-500" />
                                <span className="font-bold">{t('super_admin.support.clinic_col') || 'العيادة'}:</span>
                                <span>{viewingMessage.clinic_name || '-'}</span>
                            </div>
                            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                                <Calendar size={16} className="text-indigo-500" />
                                <span className="font-bold">{t('super_admin.support.date_col') || 'التاريخ'}:</span>
                                <span>{viewingMessage.created_at ? new Date(viewingMessage.created_at).toLocaleString(i18n.language === 'ar' ? 'ar-EG' : 'en-US') : '-'}</span>
                            </div>
                            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                                <Tag size={16} className="text-indigo-500" />
                                <span className="font-bold">{t('super_admin.support.priority_col') || 'الأولوية'}:</span>
                                <span className={`px-2 py-0.5 rounded text-xs font-bold ${viewingMessage.priority === 'high' ? 'bg-rose-100 text-rose-700' : 'bg-blue-100 text-blue-700'}`}>
                                    {t(`super_admin.support.${viewingMessage.priority}`) || viewingMessage.priority}
                                </span>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase">
                                {t('super_admin.support.message_body') || 'نص الرسالة'}
                            </label>
                            <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl text-slate-800 dark:text-slate-200 whitespace-pre-wrap font-medium text-sm leading-relaxed border border-slate-100 dark:border-slate-700">
                                {viewingMessage.message}
                            </div>
                        </div>

                        <div className="flex justify-end pt-2">
                            <button
                                type="button"
                                onClick={() => setViewingMessage(null)}
                                className="px-6 py-2.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-xl font-bold transition-all text-sm"
                            >
                                {t('common.close') || 'إغلاق'}
                            </button>
                        </div>
                    </div>
                )}
            </Modal>

            {/* Confirm Dialog for Deleting Support Message */}
            <ConfirmDialog
                isOpen={Boolean(messageToDelete)}
                onClose={() => setMessageToDelete(null)}
                onConfirm={confirmDelete}
                title={t('super_admin.support.delete_title') || 'حذف الرسالة'}
                message={t('super_admin.support.delete_confirm_msg') || 'هل أنت متأكد من حذف هذه الرسالة؟ لا يمكن التراجع عن هذا الإجراء.'}
                confirmText={t('common.delete') || 'حذف'}
                cancelText={t('common.cancel') || 'إلغاء'}
                variant="danger"
                isLoading={isDeleting}
            />
        </div>
    );
};

export default SupportInbox;

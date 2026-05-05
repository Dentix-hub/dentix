import React from 'react';
import { MessageSquare, AlertCircle, ShieldCheck, Trash2 } from 'lucide-react';
import { api } from '@/api';
import { useTranslation } from 'react-i18next';

const SupportInbox = ({ messages, setMessages, handleDeleteMessage, fetchData }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    return (
        <div className={`space-y-8 animate-fade-in ${isRtl ? 'text-right' : 'text-left'}`} dir={isRtl ? 'rtl' : 'ltr'}>
            {/* Messages Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm flex items-center justify-between">
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <p className="text-slate-500 font-bold text-sm mb-1">{t('super_admin.support.total_messages')}</p>
                        <p className="text-3xl font-bold text-slate-800 dark:text-white">{messages.length}</p>
                    </div>
                    <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 rounded-2xl">
                        <MessageSquare size={24} />
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm flex items-center justify-between">
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <p className="text-slate-500 font-bold text-sm mb-1">{t('super_admin.support.unread_messages')}</p>
                        <p className="text-3xl font-bold text-rose-600 dark:text-rose-400">{messages.filter(m => m.status === 'unread').length}</p>
                    </div>
                    <div className="p-4 bg-rose-50 dark:bg-rose-900/20 text-rose-600 rounded-2xl">
                        <AlertCircle size={24} />
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm flex items-center justify-between">
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <p className="text-slate-500 font-bold text-sm mb-1">{t('super_admin.support.high_priority')}</p>
                        <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">{messages.filter(m => m.priority === 'high').length}</p>
                    </div>
                    <div className="p-4 bg-amber-50 dark:bg-amber-900/20 text-amber-600 rounded-2xl">
                        <ShieldCheck size={24} />
                    </div>
                </div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                <div className="p-6 border-b border-slate-50 dark:border-slate-800 flex justify-between items-center">
                    <h3 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        <MessageSquare className="text-indigo-500" size={20} />
                        {t('super_admin.support.title')}
                    </h3>
                    <span className="text-xs font-bold text-slate-500 bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded-full">
                        {messages.length} {t('super_admin.support.total_messages')}
                    </span>
                </div>
                <div className="overflow-x-auto">
                    <table className={`w-full ${isRtl ? 'text-right' : 'text-left'}`}>
                        <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase">
                            <tr>
                                <th className="p-6">{t('super_admin.support.date_col')}</th>
                                <th className="p-6">{t('super_admin.support.sender_col')}</th>
                                <th className="p-6">{t('super_admin.support.clinic_col')}</th>
                                <th className="p-6">{t('super_admin.support.subject_col')}</th>
                                <th className="p-6">{t('super_admin.support.priority_col')}</th>
                                <th className="p-6">{t('super_admin.support.status_col')}</th>
                                <th className="p-6 text-center">{t('super_admin.support.actions_col') || 'Actions'}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {messages.length > 0 ? messages.map(msg => (
                                <tr key={msg.id} className={`hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors ${msg.status === 'unread' ? 'bg-indigo-50/30 dark:bg-indigo-900/10' : ''}`}>
                                    <td className="p-6 text-sm text-slate-500">
                                        {new Date(msg.created_at).toLocaleString(i18n.language === 'ar' ? 'ar-EG' : 'en-US')}
                                    </td>
                                    <td className="p-6 font-bold text-slate-800 dark:text-slate-200">{msg.username}</td>
                                    <td className="p-6 font-medium text-indigo-600 dark:text-indigo-400">{msg.clinic_name}</td>
                                    <td className="p-6">
                                        <div className="flex flex-col">
                                            <span className="font-bold text-slate-800 dark:text-white">{msg.subject}</span>
                                            <span className="text-sm text-slate-500 truncate max-w-xs">{msg.message}</span>
                                        </div>
                                    </td>
                                    <td className="p-6">
                                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${msg.priority === 'high' ? 'bg-rose-100 text-rose-700' :
                                            msg.priority === 'normal' ? 'bg-blue-100 text-blue-700' :
                                                'bg-slate-100 text-slate-700'
                                            }`}>
                                            {t(`super_admin.support.${msg.priority}`)}
                                        </span>
                                    </td>
                                    <td className="p-6">
                                        <span className={`px-3 py-1 rounded-lg text-xs font-bold ${msg.status === 'unread' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-500'}`}>
                                            {t(`super_admin.support.${msg.status}`)}
                                        </span>
                                    </td>
                                    <td className="p-6 text-center">
                                        <div className="flex items-center justify-center gap-2">
                                            <button
                                                onClick={() => {
                                                    alert(`${t('super_admin.support.subject_col')}:\n${msg.message}`);
                                                    if (msg.status === 'unread') {
                                                        api.put(`/support/messages/${msg.id}/status?status=read`).then(() => fetchData());
                                                    }
                                                }}
                                                className="p-2 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 text-indigo-600 rounded-xl transition-all"
                                                title={t('super_admin.support.view_details')}
                                            >
                                                {t('super_admin.support.view_details')}
                                            </button>
                                            <button
                                                onClick={() => handleDeleteMessage(msg.id)}
                                                className="p-2 hover:bg-rose-50 dark:hover:bg-rose-900/30 text-rose-500 rounded-xl transition-all"
                                                title={t('super_admin.support.delete_msg')}
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan="7" className="p-20 text-center text-slate-500 font-bold">
                                        {t('super_admin.support.no_messages')} 📬
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default SupportInbox;


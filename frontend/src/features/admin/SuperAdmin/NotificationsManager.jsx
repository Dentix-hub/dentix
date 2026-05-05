import React from 'react';
import { Send, Bell, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const NotificationsManager = ({ notifForm, setNotifForm, handleSendNotification, notifications, handleDeleteNotification, tenants }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    return (
        <div className={`space-y-8 animate-fade-in ${isRtl ? 'text-right' : 'text-left'}`} dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm">
                <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                    <Send className="text-indigo-500" />
                    {t('super_admin.notifications.title')}
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-bold text-slate-600 dark:text-slate-400 mb-2">{t('super_admin.notifications.form_title')}</label>
                            <input
                                type="text"
                                value={notifForm.title}
                                onChange={(e) => setNotifForm({ ...notifForm, title: e.target.value })}
                                className="w-full px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                                placeholder={t('super_admin.notifications.form_title')}
                            />
                        </div>

                        <div className="flex gap-4">
                            <div className="flex-1">
                                <label className="block text-sm font-bold text-slate-600 dark:text-slate-400 mb-2">{t('super_admin.notifications.alert_type')}</label>
                                <select
                                    value={notifForm.type}
                                    onChange={(e) => setNotifForm({ ...notifForm, type: e.target.value })}
                                    className="w-full px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none font-bold cursor-pointer"
                                >
                                    <option value="info">ℹ️ {t('super_admin.notifications.info')}</option>
                                    <option value="warning">⚠️ {t('super_admin.notifications.warning')}</option>
                                    <option value="success">✅ {t('super_admin.notifications.success')}</option>
                                    <option value="error">❌ {t('super_admin.notifications.error')}</option>
                                    <option value="system">⚙️ {t('super_admin.notifications.system')}</option>
                                </select>
                            </div>
                            <div className="flex-1">
                                <label className="block text-sm font-bold text-slate-600 dark:text-slate-400 mb-2">{t('super_admin.notifications.target')}</label>
                                <select
                                    value={notifForm.is_global ? 'all' : 'specific'}
                                    onChange={(e) => setNotifForm({ ...notifForm, is_global: e.target.value === 'all' })}
                                    className="w-full px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none font-bold cursor-pointer"
                                >
                                    <option value="all">🌍 {t('super_admin.notifications.all_clinics')}</option>
                                    <option value="specific">🏥 {t('super_admin.notifications.specific_clinic')}</option>
                                </select>
                            </div>
                        </div>

                        {!notifForm.is_global && (
                            <div>
                                <label className="block text-sm font-bold text-slate-600 dark:text-slate-400 mb-2">{t('super_admin.notifications.select_clinic')}</label>
                                <select
                                    value={notifForm.tenant_id || ''}
                                    onChange={(e) => setNotifForm({ ...notifForm, tenant_id: parseInt(e.target.value) })}
                                    className="w-full px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none font-bold cursor-pointer"
                                >
                                    <option value="" disabled>{t('super_admin.notifications.select_clinic')}...</option>
                                    {(tenants || []).map(t => (
                                        <option key={t.id} value={t.id}>{t.name}</option>
                                    ))}
                                </select>
                            </div>
                        )}
                    </div>

                    <div className="flex flex-col">
                        <label className="block text-sm font-bold text-slate-600 dark:text-slate-400 mb-2">{t('super_admin.notifications.content')}</label>
                        <textarea
                            value={notifForm.content}
                            onChange={(e) => setNotifForm({ ...notifForm, content: e.target.value })}
                            className="flex-1 px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none min-h-[150px]"
                            placeholder={t('super_admin.notifications.content') + "..."}
                        />
                        <button
                            onClick={handleSendNotification}
                            className="mt-4 w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20 transition-all"
                        >
                            <Bell size={20} />
                            {t('super_admin.notifications.broadcast_btn')}
                        </button>
                    </div>
                </div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-100 dark:border-slate-800 shadow-sm overflow-hidden">
                <div className="p-6 border-b border-slate-50 dark:border-slate-800">
                    <h3 className="font-bold text-slate-800 dark:text-white">{t('super_admin.notifications.history_title')}</h3>
                </div>
                <div className="overflow-x-auto">
                    <table className={`w-full ${isRtl ? 'text-right' : 'text-left'}`}>
                        <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 text-xs font-bold uppercase">
                            <tr>
                                <th className="p-4">{t('super_admin.notifications.history_title')}</th>
                                <th className="p-4">{t('super_admin.notifications.form_title')}</th>
                                <th className="p-4">{t('super_admin.notifications.alert_type')}</th>
                                <th className="p-4">{t('super_admin.notifications.target')}</th>
                                <th className="p-4 text-center">{t('super_admin.support.actions_col') || 'Actions'}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {notifications.length > 0 ? notifications.map(notif => (
                                <tr key={notif.id} className="hover:bg-slate-50/50 transition-colors">
                                    <td className="p-4 text-sm text-slate-500">
                                        {new Date(notif.created_at).toLocaleDateString(i18n.language === 'ar' ? 'ar-EG' : 'en-US')}
                                    </td>
                                    <td className="p-4 font-bold text-slate-800 dark:text-white">{notif.title}</td>
                                    <td className="p-4">
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${notif.type === 'error' ? 'bg-rose-100 text-rose-600' :
                                            notif.type === 'warning' ? 'bg-amber-100 text-amber-600' :
                                                'bg-blue-100 text-blue-600'
                                            }`}>
                                            {t(`super_admin.notifications.${notif.type}`) || notif.type}
                                        </span>
                                    </td>
                                    <td className="p-4 text-sm">
                                        {notif.is_global ? '🌍 ' + t('super_admin.notifications.all_clinics') : '🏥 ' + t('super_admin.notifications.specific_clinic')}
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
                                    <td colSpan="5" className="p-10 text-center text-slate-500">{t('super_admin.notifications.no_notifications')}</td>
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


export default NotificationsManager;


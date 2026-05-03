import { useState, useEffect } from 'react';
import { MessageSquare, Send, Smartphone, AlertCircle, CheckCircle2, Mail, Clock } from 'lucide-react';
import { api, submitFeedback } from '../api';
import { useTranslation } from 'react-i18next';
export default function Support() {
    const { t, i18n } = useTranslation();
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [form, setForm] = useState({ subject: '', message: '', priority: 'normal' });
    const [error, setError] = useState('');
    const [supportInfo, setSupportInfo] = useState({
        phone: '+20 120 130 1415',
        whatsapp: '201201301415',
        email: 'support@smartdentalclinicapp.com',
        working_hours: '9:00 AM - 10:00 PM'
    });
    useEffect(() => {
        const fetchSettings = async () => {
            try {
                // We use the public global-settings endpoint
                const { data } = await api.get('/api/v1/global-settings');
                if (data) {
                    setSupportInfo({
                        phone: data.support_phone || '+20 120 130 1415',
                        whatsapp: data.support_whatsapp || '201201301415',
                        email: data.support_email || 'support@smartdentalclinicapp.com',
                        working_hours: data.support_working_hours || (i18n.language === 'ar' ? '9:00 ص - 10:00 م' : '9:00 AM - 10:00 PM')
                    });
                }
            } catch (err) {
                console.error("Failed to fetch support info", err);
            }
        };
        fetchSettings();
    }, [i18n.language]);
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.message) return;
        setLoading(true);
        setError('');
        try {
            await submitFeedback(form);
            setSuccess(true);
            setForm({ subject: '', message: '', priority: 'normal' });
            setTimeout(() => {
                setSuccess(false);
            }, 5000);
        } catch (err) {
            setError(t('static.support.error_send'));
        } finally {
            setLoading(false);
        }
    };
    return (
        <div className="space-y-6 animate-fade-in pb-12">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-black text-slate-800 dark:text-white">{t('static.support.title')}</h1>
                    <p className="text-slate-500 mt-1">{t('static.support.subtitle')}</p>
                </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Contact Information Cards */}
                <div className="space-y-6">
                    <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-white/5">
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                            <Smartphone size={20} className="text-indigo-500" />
                            {t('static.support.contact_direct')}
                        </h3>
                        <div className="space-y-4">
                            <a href={`https://wa.me/${supportInfo.whatsapp}`} target="_blank" rel="noreferrer" className="flex items-center gap-3 p-4 rounded-2xl bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors">
                                <div className="p-2 bg-emerald-200 rounded-full text-emerald-700">
                                    <MessageSquare size={18} />
                                </div>
                                <div className="text-right">
                                    <p className="text-xs font-bold uppercase tracking-wider opacity-70">{t('static.support.whatsapp')}</p>
                                    <p className="font-bold text-lg ltr font-mono">{supportInfo.phone}</p>
                                </div>
                            </a>
                            <div className="flex items-center gap-3 p-4 rounded-2xl bg-indigo-50 text-indigo-700">
                                <div className="p-2 bg-indigo-200 rounded-full text-indigo-700">
                                    <Mail size={18} />
                                </div>
                                <div className="text-right min-w-0 flex-1">
                                    <p className="text-xs font-bold uppercase tracking-wider opacity-70">{t('static.support.email')}</p>
                                    <p className="font-bold font-mono text-sm truncate" title={supportInfo.email}>{supportInfo.email}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="bg-gradient-to-br from-cyan-600 to-indigo-600 rounded-3xl p-6 text-white shadow-xl shadow-indigo-500/20">
                        <Clock size={32} className="mb-4 opacity-80" />
                        <h3 className="text-xl font-bold mb-2">{t('static.support.working_hours')}</h3>
                        <p className="opacity-90 leading-relaxed mb-4">
                            {t('static.support.working_hours_desc')} <span dir="ltr">{supportInfo.working_hours}</span>.
                        </p>
                        <div className="flex items-center gap-2 text-sm font-bold bg-white/20 p-3 rounded-xl backdrop-blur-sm">
                            <CheckCircle2 size={16} />
                            <span>{t('static.support.available_now')}</span>
                        </div>
                    </div>
                </div>
                {/* Contact Form */}
                <div className="lg:col-span-2">
                    <div className="bg-white dark:bg-slate-800 rounded-3xl shadow-lg border border-slate-100 dark:border-white/5 overflow-hidden">
                        <div className="p-8">
                            {success ? (
                                <div className="text-center py-12 animate-bounce-subtle">
                                    <div className="w-20 h-20 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
                                        <CheckCircle2 size={48} />
                                    </div>
                                    <h3 className="text-2xl font-bold mb-2 text-slate-800 dark:text-white">{t('static.support.success_title')}</h3>
                                    <p className="text-slate-500 text-lg">{t('static.support.success_msg')}</p>
                                    <button
                                        onClick={() => setSuccess(false)}
                                        className="mt-8 px-8 py-3 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl font-bold transition-colors"
                                    >
                                        {t('static.support.send_another')}
                                    </button>
                                </div>
                            ) : (
                                <form onSubmit={handleSubmit} className="space-y-8">
                                    <div className="flex items-center gap-3 mb-6">
                                        <div className="p-3 bg-indigo-100 text-indigo-600 rounded-2xl">
                                            <Send size={24} />
                                        </div>
                                        <h2 className="text-2xl font-bold text-slate-800 dark:text-white">{t('static.support.send_ticket')}</h2>
                                    </div>
                                    {error && (
                                        <div className="flex items-center gap-3 p-4 bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 rounded-2xl text-sm font-bold border border-rose-100 dark:border-rose-900/30">
                                            <AlertCircle size={18} />
                                            {error}
                                        </div>
                                    )}
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <div className="col-span-2">
                                            <label className="block text-sm font-black uppercase tracking-wider mb-3 pr-1 text-slate-500 dark:text-slate-400">{t('static.support.subject')}</label>
                                            <input
                                                type="text"
                                                required
                                                value={form.subject}
                                                onChange={(e) => setForm({ ...form, subject: e.target.value })}
                                                className="w-full px-6 py-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-white outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all font-bold text-lg placeholder:font-normal"
                                                placeholder={t('static.support.subject_placeholder')}
                                            />
                                        </div>
                                        <div className="col-span-2">
                                            <label className="block text-sm font-black uppercase tracking-wider mb-3 pr-1 text-slate-500 dark:text-slate-400">{t('static.support.message')}</label>
                                            <textarea
                                                required
                                                rows="8"
                                                value={form.message}
                                                onChange={(e) => setForm({ ...form, message: e.target.value })}
                                                className="w-full px-6 py-5 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-white outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all font-medium text-lg placeholder:font-normal resize-none"
                                                placeholder={t('static.support.message_placeholder')}
                                            />
                                        </div>
                                    </div>
                                    <div className="flex justify-end">
                                        <button
                                            type="submit"
                                            disabled={loading}
                                            className="px-8 py-4 bg-gradient-to-r from-indigo-600 to-teal-600 hover:from-indigo-700 hover:to-teal-700 text-white rounded-2xl font-bold flex items-center gap-3 shadow-xl shadow-indigo-500/20 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100 w-full md:w-auto justify-center"
                                        >
                                            {loading ? (
                                                <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                            ) : (
                                                <>
                                                    <Send size={20} />
                                                    {t('static.support.submit')}
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </form>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}


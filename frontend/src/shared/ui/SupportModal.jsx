import React, { useState } from 'react';
import { X, MessageSquare, Send, Smartphone, AlertCircle, CheckCircle2 } from 'lucide-react';
import { submitFeedback } from '@/api';

export default function SupportModal({ isOpen, onClose, isDarkMode }) {
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [form, setForm] = useState({ subject: '', message: '', priority: 'normal' });
    const [error, setError] = useState('');

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
                onClose();
            }, 3000);
        } catch (err) {
            setError('فشل إرسال الرسالة، يرجى المحاولة لاحقاً.');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in" dir="rtl">
            <div className={`relative w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-[2.5rem] shadow-2xl border ${isDarkMode ? 'bg-slate-900 border-white/10' : 'bg-white border-slate-200'}`}>

                {/* Header */}
                <div className="p-8 pb-4 flex justify-between items-center sticky top-0 z-10 bg-inherit backdrop-blur-md">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-indigo-500 rounded-2xl shadow-lg shadow-indigo-500/20 text-white">
                            <MessageSquare size={32} />
                        </div>
                        <div>
                            <h2 className={`text-3xl font-black ${isDarkMode ? 'text-white' : 'text-slate-800'}`}>تواصل معنا</h2>
                            <p className="text-slate-500 text-base font-medium">نحن هنا لمساعدتك في أي وقت</p>
                        </div>
                    </div>
                    <button onClick={onClose} className={`p-2 rounded-full transition-colors ${isDarkMode ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-500'}`}>
                        <X size={28} />
                    </button>
                </div>

                <div className="p-8 pt-4">
                    {success ? (
                        <div className="text-center py-12 animate-bounce-subtle">
                            <div className="w-20 h-20 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
                                <CheckCircle2 size={48} />
                            </div>
                            <h3 className={`text-xl font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-slate-800'}`}>تم الإرسال بنجاح!</h3>
                            <p className="text-slate-500">سوف يقوم فريق التطوير بمراجعة رسالتك والرد عليك في أقرب وقت.</p>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-8">

                            {error && (
                                <div className="flex items-center gap-3 p-4 bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 rounded-2xl text-sm font-bold border border-rose-100 dark:border-rose-900/30">
                                    <AlertCircle size={18} />
                                    {error}
                                </div>
                            )}

                            <div>
                                <label className={`block text-sm font-black uppercase tracking-wider mb-3 pr-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>الموضوع</label>
                                <input
                                    type="text"
                                    required
                                    value={form.subject}
                                    onChange={(e) => setForm({ ...form, subject: e.target.value })}
                                    className={`w-full px-6 py-4 rounded-2xl border outline-none transition-all font-bold text-lg ${isDarkMode ? 'bg-slate-800 border-white/5 text-white focus:border-indigo-500' : 'bg-slate-50 border-slate-200 text-slate-800 focus:border-indigo-500'}`}
                                    placeholder="مثلاً: مشكلة في الحجوزات"
                                />
                            </div>

                            <div>
                                <label className={`block text-sm font-black uppercase tracking-wider mb-3 pr-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>رسالتك</label>
                                <textarea
                                    required
                                    rows="10"
                                    value={form.message}
                                    onChange={(e) => setForm({ ...form, message: e.target.value })}
                                    className={`w-full px-6 py-5 rounded-2xl border outline-none transition-all font-medium text-lg ${isDarkMode ? 'bg-slate-800 border-white/5 text-white focus:border-indigo-500' : 'bg-slate-50 border-slate-200 text-slate-800 focus:border-indigo-500'}`}
                                    placeholder="اشرح لنا المشكلة أو الاقتراح بالتفصيل..."
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-4 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white rounded-2xl font-bold flex items-center justify-center gap-3 shadow-xl shadow-indigo-500/20 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50"
                            >
                                {loading ? (
                                    <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <>
                                        <Send size={20} />
                                        إرسال الرسالة
                                    </>
                                )}
                            </button>

                            <div className="relative py-2">
                                <div className="absolute inset-0 flex items-center">
                                    <div className={`w-full border-t ${isDarkMode ? 'border-white/5' : 'border-slate-100'}`} />
                                </div>
                                <div className="relative flex justify-center text-xs uppercase">
                                    <span className={`px-4 font-black ${isDarkMode ? 'bg-slate-900 text-slate-500' : 'bg-white text-slate-400'}`}>أو تواصل فوراً</span>
                                </div>
                            </div>

                            <a
                                href="https://wa.me/201201301415" // Replace with actual WhatsApp number
                                target="_blank"
                                rel="noopener noreferrer"
                                className="w-full py-4 bg-emerald-500 hover:bg-emerald-600 text-white rounded-2xl font-bold flex items-center justify-center gap-3 shadow-xl shadow-emerald-500/20 transition-all hover:scale-[1.02] active:scale-95"
                            >
                                <Smartphone size={20} />
                                تواصل عبر واتساب
                            </a>
                        </form>
                    )}
                </div>
            </div>
        </div>
    );
}

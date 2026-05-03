import React, { useState } from 'react';
import { Plus, Calendar, User, FileText, CheckCircle2, Clock } from 'lucide-react';
import Button from '../Button';
import { format } from 'date-fns';
import { ar } from 'date-fns/locale';

export const MultiSessionPanel = ({ sessions = [], onAddSession, isLoading }) => {
    const [isAdding, setIsAdding] = useState(false);
    const [newSessionData, setNewSessionData] = useState({
        notes: '',
        next_session_date: '',
        status: 'completed'
    });

    const handleSubmit = async () => {
        if (!newSessionData.notes) return;
        
        const success = await onAddSession(newSessionData);
        if (success) {
            setIsAdding(false);
            setNewSessionData({ notes: '', next_session_date: '', status: 'completed' });
        }
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Clock size={14} className="text-blue-500" />
                    سجل الجلسات والزيارات (Multi-Session)
                </label>
                
                {!isAdding && (
                    <button
                        onClick={() => setIsAdding(true)}
                        className="text-[10px] font-bold text-blue-600 bg-blue-50 px-3 py-1 rounded-full hover:bg-blue-100 transition-colors flex items-center gap-1"
                    >
                        <Plus size={12} />
                        إضافة جلسة جديدة
                    </button>
                )}
            </div>

            {isAdding && (
                <div className="bg-blue-50/50 border-2 border-dashed border-blue-200 rounded-2xl p-4 space-y-3 animate-in fade-in slide-in-from-top-2">
                    <textarea
                        autoFocus
                        value={newSessionData.notes}
                        onChange={(e) => setNewSessionData({...newSessionData, notes: e.target.value})}
                        className="w-full p-3 bg-white border-0 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 min-h-[80px]"
                        placeholder="ماذا تم في هذه الجلسة؟"
                    />
                    <div className="flex flex-wrap gap-3">
                        <div className="flex-1 min-w-[150px]">
                            <label className="text-[10px] font-bold text-slate-500 mb-1 block">موعد الجلسة القادمة (اختياري)</label>
                            <input
                                type="date"
                                value={newSessionData.next_session_date}
                                onChange={(e) => setNewSessionData({...newSessionData, next_session_date: e.target.value})}
                                className="w-full p-2 bg-white border-0 rounded-lg text-xs"
                            />
                        </div>
                        <div className="flex items-end gap-2">
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setIsAdding(false)}
                            >
                                إلغاء
                            </Button>
                            <Button
                                size="sm"
                                onClick={handleSubmit}
                                isLoading={isLoading}
                                disabled={!newSessionData.notes}
                            >
                                حفظ الجلسة
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            <div className="space-y-3">
                {sessions.length === 0 ? (
                    <div className="text-center py-8 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
                        <Clock size={32} className="mx-auto text-slate-300 mb-2 opacity-50" />
                        <p className="text-xs text-slate-400 font-medium tracking-wide">لا يوجد جلسات مسجلة بعد</p>
                    </div>
                ) : (
                    sessions.map((session, index) => (
                        <div key={session.id || index} className="group relative bg-white border border-slate-100 rounded-2xl p-4 hover:border-blue-200 hover:shadow-sm transition-all duration-300">
                            <div className="flex items-start justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    <div className="w-6 h-6 rounded-full bg-blue-50 flex items-center justify-center text-[10px] font-bold text-blue-600">
                                        #{sessions.length - index}
                                    </div>
                                    <span className="text-[11px] font-bold text-slate-400">
                                        {format(new Date(session.created_at), 'PPP', { locale: ar })}
                                    </span>
                                </div>
                                <CheckCircle2 size={14} className="text-green-500" />
                            </div>
                            
                            <p className="text-sm text-slate-600 leading-relaxed pr-8">
                                {session.notes}
                            </p>

                            {session.next_session_date && (
                                <div className="mt-3 pt-3 border-t border-slate-50 flex items-center gap-2 text-[10px] font-bold text-blue-600 bg-blue-50/50 -mx-4 px-4 rounded-b-xl">
                                    <Calendar size={12} />
                                    الموعد القادم: {format(new Date(session.next_session_date), 'PPP', { locale: ar })}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Calendar, CreditCard, CheckCircle2, Clock } from 'lucide-react';

const PatientTimeline = ({ history = [], payments = [], t }) => {
    // Merge and sort events
    const events = useMemo(() => {
        const items = [];
        
        history.forEach(h => {
            items.push({
                date: new Date(h.date),
                type: 'treatment',
                title: h.procedure_name || t('patients.history.treatment'),
                subtitle: h.notes,
                icon: CheckCircle2,
                color: 'text-emerald-500',
                bg: 'bg-emerald-500/10'
            });
        });
        
        payments.forEach(p => {
            items.push({
                date: new Date(p.date),
                type: 'payment',
                title: t('billing.payment_received', 'تم استلام دفعة'),
                subtitle: `${p.amount} EGP`,
                icon: CreditCard,
                color: 'text-blue-500',
                bg: 'bg-blue-500/10'
            });
        });
        
        return items.sort((a, b) => b.date - a.date);
    }, [history, payments, t]);

    if (events.length === 0) {
        return (
            <div className="py-20 text-center">
                 <div className="w-16 h-16 bg-slate-50 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4 shadow-inner">
                     <Clock className="text-slate-300" size={32} />
                 </div>
                 <p className="text-slate-500 font-bold">{t('patients.history.no_data', 'لا يوجد سجلات حتى الآن')}</p>
            </div>
        );
    }

    return (
        <div className="p-4 md:p-8 space-y-10 relative">
            {/* Vertical Line */}
            <div className="absolute top-0 bottom-0 left-[35px] md:left-[51px] w-1 bg-gradient-to-b from-slate-100 via-slate-200 to-transparent dark:from-slate-800 dark:via-slate-800 dark:to-transparent" />
            
            {events.map((event, idx) => (
                <motion.div 
                    key={idx}
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: idx * 0.05 }}
                    className="flex gap-6 md:gap-8 relative"
                >
                    {/* Icon Container */}
                    <div className={`relative z-10 w-10 h-10 md:w-12 md:h-12 rounded-2xl ${event.bg} ${event.color} flex items-center justify-center border-4 border-white dark:border-slate-900 shadow-xl group hover:scale-110 transition-transform`}>
                        <event.icon size={20} className="group-hover:rotate-12 transition-transform" />
                    </div>
                    
                    {/* Content Card */}
                    <div className="flex-1 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm p-5 md:p-6 rounded-[2rem] border border-slate-100 dark:border-white/5 shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-3">
                            <h4 className="font-black text-slate-800 dark:text-slate-100 text-sm md:text-base tracking-tight leading-none">
                                {event.title}
                            </h4>
                            <div className="px-3 py-1 bg-slate-100 dark:bg-slate-900 rounded-lg text-[10px] font-black text-slate-500 uppercase tracking-widest whitespace-nowrap self-start">
                                {event.date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}
                            </div>
                        </div>
                        {event.subtitle && (
                            <p className="text-xs md:text-sm font-medium text-slate-500 dark:text-slate-400 leading-relaxed border-t border-slate-100 dark:border-white/5 pt-3 mt-3 italic">
                                {event.subtitle}
                            </p>
                        )}
                    </div>
                </motion.div>
            ))}
        </div>
    );
};

export default PatientTimeline;

import React, { useState, useMemo, Fragment } from 'react';
import { Popover, PopoverButton, PopoverPanel, Transition, Portal } from '@headlessui/react';
import { Calendar as CalendarIcon, Clock, ChevronLeft, ChevronRight, Check, ChevronDown, X } from 'lucide-react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, isSameDay, isToday, parseISO, isValid } from 'date-fns';
import { useTranslation } from 'react-i18next';

export default function DateTimePicker({ value, onChange, label, error, required, mode = 'datetime', placeholder, compact = false }) {
    const { t, i18n } = useTranslation();
    const isArabic = i18n.language === 'ar';
    
    const isDateOnly = mode === 'date';
    const isMonthOnly = mode === 'month';
    
    // Parse value safely
    const initialDate = useMemo(() => {
        if (!value) return new Date();
        let dateToParse = value;
        if (isMonthOnly && typeof value === 'string' && value.length === 7) {
            dateToParse = `${value}-01`;
        }
        const d = typeof dateToParse === 'string' ? parseISO(dateToParse) : new Date(dateToParse);
        return isValid(d) ? d : new Date();
    }, [value, isMonthOnly]);

    const [viewMode, setViewMode] = useState('days'); // 'days', 'months', 'years'
    const [viewDate, setViewDate] = useState(initialDate);
    const [selectedDate, setSelectedDate] = useState(initialDate);
    const [tempTime, setTempTime] = useState({
        hours: initialDate.getHours() % 12 || 12,
        minutes: Math.floor(initialDate.getMinutes() / 5) * 5,
        ampm: initialDate.getHours() >= 12 ? 'PM' : 'AM'
    });

    const days = useMemo(() => {
        const start = startOfWeek(startOfMonth(viewDate));
        const end = endOfMonth(viewDate);
        // Ensure we show 6 weeks to keep height consistent
        const daysInMonth = eachDayOfInterval({ start, end: endOfWeek(end) });
        return daysInMonth;
    }, [viewDate]);

    const years = useMemo(() => {
        const currentYear = new Date().getFullYear();
        const startYear = currentYear - 80;
        const endYear = currentYear + 20;
        const yearsArray = [];
        for (let i = startYear; i <= endYear; i++) {
            yearsArray.push(i);
        }
        return yearsArray;
    }, []);

    const handleConfirm = (close) => {
        let finalDate = new Date(selectedDate);
        if (!isDateOnly && !isMonthOnly) {
            let h = tempTime.hours === 12 ? 0 : tempTime.hours;
            if (tempTime.ampm === 'PM') h += 12;
            finalDate.setHours(h, tempTime.minutes, 0, 0);
            onChange({ target: { value: finalDate.toISOString() } });
        } else if (isMonthOnly) {
            onChange({ target: { value: format(finalDate, 'yyyy-MM') } });
        } else {
            onChange({ target: { value: format(finalDate, 'yyyy-MM-dd') } });
        }
        if (close) close();
    };

    const handleDateClick = (day, close) => {
        setSelectedDate(day);
        if (isDateOnly || isMonthOnly) {
            handleConfirm(close);
        }
    };

    const handleToday = (close) => {
        const now = new Date();
        setSelectedDate(now);
        setViewDate(now);
        if (isDateOnly || isMonthOnly) {
            handleConfirm(close);
        }
    };

    const handleMonthSelect = (month) => {
        const newDate = new Date(viewDate.setMonth(month));
        setViewDate(new Date(newDate));
        if (isMonthOnly) {
            setSelectedDate(new Date(newDate));
        } else {
            setViewMode('days');
        }
    };

    const handleYearSelect = (year) => {
        const newDate = new Date(viewDate.setFullYear(year));
        setViewDate(new Date(newDate));
        setViewMode('months');
    };

    return (
        <div className={`w-full ${compact ? '' : 'space-y-1.5'}`}>
            {!compact && label && (
                <label className="block text-sm font-bold text-text-primary">
                    {label}
                    {required && <span className="text-red-500 ml-1">*</span>}
                </label>
            )}
            
            <Popover className="relative">
                {({ open, close }) => (
                    <>
                        <PopoverButton className={`w-full flex items-center justify-between ${compact ? 'px-3 py-1.5' : 'px-4 py-3'} bg-surface border-2 ${error ? 'border-red-300' : 'border-border'} rounded-2xl text-sm font-bold text-text-primary hover:border-primary/40 hover:bg-slate-50 dark:hover:bg-slate-800 transition-all shadow-sm outline-none focus:ring-4 focus:ring-primary/10`}>
                            <div className="flex items-center gap-2.5">
                                <div className={`p-1.5 rounded-lg ${open ? 'bg-primary text-white' : 'bg-primary/10 text-primary'} transition-colors`}>
                                    {isDateOnly || isMonthOnly ? <CalendarIcon size={compact ? 12 : 14} /> : <Clock size={compact ? 12 : 14} />}
                                </div>
                                <span dir="ltr" className={compact ? 'text-xs' : 'text-sm'}>
                                    {!value && placeholder ? (
                                        <span className="text-slate-400 font-medium">{placeholder}</span>
                                    ) : (
                                        isMonthOnly 
                                            ? format(initialDate, 'MMMM yyyy')
                                            : isDateOnly 
                                            ? format(initialDate, 'yyyy-MM-dd') 
                                            : format(initialDate, 'yyyy-MM-dd hh:mm a')
                                    )}
                                </span>
                            </div>
                            <ChevronDown className={`h-4 w-4 text-slate-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
                        </PopoverButton>

                        <Portal>
                            <Transition
                                as={Fragment}
                                enter="transition ease-out duration-200"
                                enterFrom="opacity-0 translate-y-1 scale-95"
                                enterTo="opacity-100 translate-y-0 scale-100"
                                leave="transition ease-in duration-150"
                                leaveFrom="opacity-100 translate-y-0 scale-100"
                                leaveTo="opacity-0 translate-y-1 scale-95"
                                afterLeave={() => setViewMode('days')}
                            >
                                <PopoverPanel 
                                    anchor="bottom"
                                    className="z-[9999] mt-2 bg-white dark:bg-slate-900 rounded-[2.5rem] shadow-[0_20px_50px_rgba(0,0,0,0.3)] ring-1 ring-black/5 overflow-hidden border border-slate-200 dark:border-white/10 md:fixed md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:mt-0"
                                >
                                    <div className={`flex flex-col md:flex-row ${isDateOnly || isMonthOnly ? 'w-[320px]' : 'w-[320px] md:w-[600px]'} max-h-[90vh] overflow-hidden`}>
                                        
                                        {/* Calendar Column */}
                                        <div className="p-6 flex-1 flex flex-col min-h-[400px]">
                                            <div className="flex items-center justify-between mb-6">
                                                <button 
                                                    type="button"
                                                    onClick={() => setViewDate(subMonths(viewDate, viewMode === 'years' ? 120 : (viewMode === 'months' ? 12 : 1)))} 
                                                    className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-2xl text-slate-500 transition-colors"
                                                >
                                                    <ChevronLeft size={20} />
                                                </button>
                                                
                                                <button 
                                                    type="button"
                                                    onClick={() => setViewMode(viewMode === 'days' ? 'months' : (viewMode === 'months' ? 'years' : 'days'))}
                                                    className="px-4 py-2 hover:bg-primary/10 rounded-2xl transition-all"
                                                >
                                                    <h3 className="font-black text-lg text-text-primary tracking-tight flex items-center gap-2">
                                                        {viewMode === 'years' ? (
                                                            `${years[0]} - ${years[years.length - 1]}`
                                                        ) : viewMode === 'months' ? (
                                                            format(viewDate, 'yyyy')
                                                        ) : (
                                                            <>
                                                                {format(viewDate, 'MMMM')}
                                                                <span className="text-primary">{format(viewDate, 'yyyy')}</span>
                                                            </>
                                                        )}
                                                        <ChevronDown size={14} className="text-primary opacity-50" />
                                                    </h3>
                                                </button>

                                                <button 
                                                    type="button"
                                                    onClick={() => setViewDate(addMonths(viewDate, viewMode === 'years' ? 120 : (viewMode === 'months' ? 12 : 1)))} 
                                                    className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-2xl text-slate-500 transition-colors"
                                                >
                                                    <ChevronRight size={20} />
                                                </button>
                                            </div>

                                            <div className="flex-1 overflow-y-auto">
                                                {viewMode === 'years' ? (
                                                    <div className="grid grid-cols-4 gap-2">
                                                        {years.map(y => (
                                                            <button
                                                                key={y}
                                                                type="button"
                                                                onClick={() => handleYearSelect(y)}
                                                                className={`py-3 rounded-xl text-sm font-bold transition-all ${viewDate.getFullYear() === y ? 'bg-primary text-white shadow-lg' : 'hover:bg-primary/10 text-text-primary'}`}
                                                            >
                                                                {y}
                                                            </button>
                                                        ))}
                                                    </div>
                                                ) : viewMode === 'months' ? (
                                                    <div className="grid grid-cols-3 gap-3">
                                                        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(m => {
                                                            const monthDate = new Date(viewDate.getFullYear(), m, 1);
                                                            const isSelected = isSameMonth(monthDate, selectedDate);
                                                            return (
                                                                <button
                                                                    key={m}
                                                                    type="button"
                                                                    onClick={() => handleMonthSelect(m)}
                                                                    className={`py-6 rounded-2xl text-sm font-bold transition-all ${isSelected ? 'bg-primary text-white shadow-xl shadow-primary/30' : 'text-text-primary hover:bg-primary/10'}`}
                                                                >
                                                                    {format(monthDate, 'MMMM')}
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                ) : (
                                                    <>
                                                        <div className="grid grid-cols-7 gap-1 mb-3">
                                                            {(isArabic ? ['ح', 'ن', 'ث', 'ر', 'خ', 'ج', 'س'] : ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']).map((d, i) => (
                                                                <span key={i} className="text-[10px] font-black text-slate-400 text-center uppercase tracking-wider">
                                                                    {d}
                                                                </span>
                                                            ))}
                                                        </div>
                                                        
                                                        <div className="grid grid-cols-7 gap-2">
                                                            {days.map((day, idx) => {
                                                                const isSelected = isSameDay(day, selectedDate);
                                                                const currentMonth = isSameMonth(day, viewDate);
                                                                const today = isToday(day);
                                                                
                                                                return (
                                                                    <button
                                                                        key={idx}
                                                                        type="button"
                                                                        onClick={() => handleDateClick(day, close)}
                                                                        className={`
                                                                            aspect-square flex items-center justify-center rounded-2xl text-sm font-black transition-all relative
                                                                            ${isSelected ? 'bg-primary text-white shadow-2xl shadow-primary/40 scale-110 z-10' : 
                                                                              currentMonth ? 'text-text-primary hover:bg-primary/10' : 'text-slate-300 dark:text-slate-700 opacity-40'}
                                                                        `}
                                                                    >
                                                                        {format(day, 'd')}
                                                                        {today && !isSelected && (
                                                                            <div className="absolute top-1 right-1 w-1.5 h-1.5 bg-primary rounded-full" />
                                                                        )}
                                                                    </button>
                                                                );
                                                            })}
                                                        </div>
                                                    </>
                                                )}
                                            </div>

                                            <div className="mt-8 flex items-center justify-between gap-4 sticky bottom-0 bg-white dark:bg-slate-900 pt-2">
                                                <button
                                                    type="button"
                                                    onClick={() => handleToday(close)}
                                                    className="flex-1 py-3 px-4 rounded-2xl bg-slate-100 dark:bg-slate-800 text-text-primary text-xs font-black hover:bg-slate-200 transition-colors uppercase tracking-widest"
                                                >
                                                    {t('common.today', 'Today')}
                                                </button>
                                                {!isDateOnly && !isMonthOnly && (
                                                    <button
                                                        type="button"
                                                        onClick={() => handleConfirm(close)}
                                                        className="flex-1 py-3 px-4 rounded-2xl bg-primary text-white text-xs font-black hover:bg-primary-dark shadow-lg shadow-primary/30 transition-all uppercase tracking-widest flex items-center justify-center gap-2"
                                                    >
                                                        <Check size={14} />
                                                        {t('common.confirm', 'Confirm')}
                                                    </button>
                                                )}
                                            </div>
                                        </div>

                                        {/* Time Column */}
                                        {!isDateOnly && !isMonthOnly && (
                                            <div className="bg-slate-50 dark:bg-black/40 p-6 w-full md:w-[280px] border-t md:border-t-0 md:border-s border-border/50 overflow-y-auto">
                                                <div className="flex items-center gap-2.5 text-primary mb-6">
                                                    <div className="p-1.5 bg-primary/10 rounded-lg">
                                                        <Clock size={16} />
                                                    </div>
                                                    <span className="text-xs font-black uppercase tracking-[0.2em]">{t('common.time', 'Time')}</span>
                                                </div>

                                                <div className="space-y-6">
                                                    <div>
                                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 block">{t('common.hour', 'Hour')}</label>
                                                        <div className="grid grid-cols-4 gap-2">
                                                            {[12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(h => (
                                                                <button
                                                                    key={h}
                                                                    type="button"
                                                                    onClick={() => setTempTime(t => ({ ...t, hours: h }))}
                                                                    className={`py-3 rounded-xl text-xs font-black transition-all ${tempTime.hours === h ? 'bg-primary text-white shadow-xl' : 'bg-white dark:bg-slate-800 text-text-primary border border-border/50'}`}
                                                                >
                                                                    {h}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    </div>

                                                    <div>
                                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 block">{t('common.minute', 'Minutes')}</label>
                                                        <div className="grid grid-cols-4 gap-2">
                                                            {[0, 15, 30, 45].map(m => (
                                                                <button
                                                                    key={m}
                                                                    type="button"
                                                                    onClick={() => setTempTime(t => ({ ...t, minutes: m }))}
                                                                    className={`py-3 rounded-xl text-xs font-black transition-all ${tempTime.minutes === m ? 'bg-primary text-white shadow-xl' : 'bg-white dark:bg-slate-800 text-text-primary border border-border/50'}`}
                                                                >
                                                                    {m.toString().padStart(2, '0')}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    </div>

                                                    <div className="flex gap-2 p-1.5 bg-white dark:bg-slate-800 rounded-2xl border-2 border-border/50 shadow-inner">
                                                        {['AM', 'PM'].map(p => (
                                                            <button
                                                                key={p}
                                                                type="button"
                                                                onClick={() => setTempTime(t => ({ ...t, ampm: p }))}
                                                                className={`flex-1 py-3 rounded-xl text-xs font-black transition-all ${tempTime.ampm === p ? 'bg-primary text-white shadow-lg' : 'text-slate-400 hover:text-text-primary'}`}
                                                            >
                                                                {p}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </PopoverPanel>
                            </Transition>
                        </Portal>
                    </>
                )}
            </Popover>
            {!compact && error && <p className="text-xs font-bold text-red-500 mt-1">{error}</p>}
        </div>
    );
}


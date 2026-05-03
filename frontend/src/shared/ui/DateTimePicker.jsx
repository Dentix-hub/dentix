import React, { useState, useMemo } from 'react';
import { Popover, PopoverButton, PopoverPanel, Transition } from '@headlessui/react';
import { Calendar as CalendarIcon, Clock, ChevronLeft, ChevronRight, Check, ChevronDown } from 'lucide-react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, isSameDay, addDays, setHours, setMinutes, isToday } from 'date-fns';
import { useTranslation } from 'react-i18next';
import { Fragment } from 'react';

export default function DateTimePicker({ value, onChange, label, error, required, mode = 'datetime', placeholder, compact = false }) {
    const { t, i18n } = useTranslation();
    const isArabic = i18n.language === 'ar';
    
    const isDateOnly = mode === 'date';
    const isMonthOnly = mode === 'month';
    
    // Parse initial value or use now
    const selectedDate = useMemo(() => {
        if (!value) return new Date();
        // Handle YYYY-MM format for month mode
        const dateStr = isMonthOnly && typeof value === 'string' && value.length === 7 ? `${value}-01` : value;
        const d = new Date(dateStr);
        return isNaN(d.getTime()) ? new Date() : d;
    }, [value, isMonthOnly]);

    const [viewDate, setViewDate] = useState(selectedDate);
    const [tempTime, setTempTime] = useState({
        hours: selectedDate.getHours() % 12 || 12,
        minutes: Math.floor(selectedDate.getMinutes() / 5) * 5,
        ampm: selectedDate.getHours() >= 12 ? 'PM' : 'AM'
    });

    const days = useMemo(() => {
        const start = startOfWeek(startOfMonth(viewDate));
        const end = endOfWeek(endOfMonth(viewDate));
        return eachDayOfInterval({ start, end });
    }, [viewDate]);

    const handleDateSelect = (date, close) => {
        const newDate = new Date(date);
        
        if (isMonthOnly) {
            onChange({ target: { value: format(newDate, 'yyyy-MM') } });
            if (close) close();
        } else if (isDateOnly) {
            newDate.setHours(0, 0, 0, 0);
            onChange({ target: { value: format(newDate, 'yyyy-MM-dd') } });
            if (close) close();
        } else {
            let h = tempTime.hours === 12 ? 0 : tempTime.hours;
            if (tempTime.ampm === 'PM') h += 12;
            newDate.setHours(h, tempTime.minutes, 0, 0);
            onChange({ target: { value: newDate.toISOString().substring(0, 19) } });
        }
    };

    const handleTimeChange = (type, val) => {
        const newTime = { ...tempTime, [type]: val };
        setTempTime(newTime);
        
        const newDate = new Date(selectedDate);
        let h = newTime.hours === 12 ? 0 : newTime.hours;
        if (newTime.ampm === 'PM') h += 12;
        newDate.setHours(h, newTime.minutes, 0, 0);
        onChange({ target: { value: newDate.toISOString().substring(0, 19) } });
    };

    const handleToday = (close) => {
        const now = new Date();
        setViewDate(now);
        handleDateSelect(now, close);
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
                        <PopoverButton className={`w-full flex items-center justify-between ${compact ? 'px-2 py-1' : 'px-4 py-3'} bg-surface border ${error ? 'border-red-300' : 'border-border'} rounded-xl text-sm font-bold text-text-primary hover:bg-slate-50 dark:hover:bg-slate-800 transition-all shadow-sm outline-none focus:ring-2 focus:ring-primary/20`}>
                            <div className="flex items-center gap-2">
                                <CalendarIcon className={`${compact ? 'h-3 w-3' : 'h-4 w-4'} text-primary`} />
                                <span dir="ltr" className={compact ? 'text-xs' : ''}>
                                    {!value && placeholder ? (
                                        <span className="text-slate-400 font-medium">{placeholder}</span>
                                    ) : (
                                        isMonthOnly 
                                            ? format(selectedDate, 'MMMM yyyy')
                                            : isDateOnly 
                                            ? format(selectedDate, 'yyyy-MM-dd') 
                                            : format(selectedDate, 'yyyy-MM-dd HH:mm')
                                    )}
                                </span>
                            </div>
                            {isDateOnly || isMonthOnly ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <Clock className="h-4 w-4 text-slate-400" />}
                        </PopoverButton>

                        <Transition
                            as={Fragment}
                            enter="transition ease-out duration-200"
                            enterFrom="opacity-0 translate-y-1"
                            enterTo="opacity-100 translate-y-0"
                            leave="transition ease-in duration-150"
                            leaveFrom="opacity-100 translate-y-0"
                            leaveTo="opacity-0 translate-y-1"
                        >
                            <PopoverPanel className={`absolute z-[110] mt-2 ${isDateOnly || isMonthOnly ? 'w-72' : 'w-80 md:w-[450px]'} bg-white dark:bg-slate-900 rounded-[2rem] shadow-2xl ring-1 ring-black/5 overflow-hidden border border-border/50 backdrop-blur-xl`}>
                                <div className="flex flex-col md:flex-row h-full">
                                    {/* Calendar Section */}
                                    <div className={`p-5 flex-1 ${!isDateOnly && !isMonthOnly ? 'border-b md:border-b-0 md:border-e border-border/50' : ''}`}>
                                        <div className="flex items-center justify-between mb-4">
                                            <button 
                                                type="button"
                                                onClick={() => setViewDate(subMonths(viewDate, isMonthOnly ? 12 : 1))} 
                                                className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500"
                                            >
                                                <ChevronLeft size={16} />
                                            </button>
                                            <h3 className="font-black text-xs text-text-primary capitalize tracking-tight">
                                                {isMonthOnly ? format(viewDate, 'yyyy') : format(viewDate, 'MMMM yyyy')}
                                            </h3>
                                            <button 
                                                type="button"
                                                onClick={() => setViewDate(addMonths(viewDate, isMonthOnly ? 12 : 1))} 
                                                className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500"
                                            >
                                                <ChevronRight size={16} />
                                            </button>
                                        </div>
                                        
                                        {isMonthOnly ? (
                                            <div className="grid grid-cols-3 gap-2">
                                                {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(m => {
                                                    const monthDate = new Date(viewDate.getFullYear(), m, 1);
                                                    const isSelected = isSameMonth(monthDate, selectedDate);
                                                    return (
                                                        <button
                                                            key={m}
                                                            type="button"
                                                            onClick={() => handleDateSelect(monthDate, close)}
                                                            className={`py-3 rounded-xl text-xs font-bold transition-all ${isSelected ? 'bg-primary text-white shadow-lg' : 'text-text-primary hover:bg-primary/10'}`}
                                                        >
                                                            {format(monthDate, 'MMM')}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        ) : (
                                            <>
                                                <div className="grid grid-cols-7 gap-1 mb-2">
                                                    {(isArabic ? ['أ', 'إ', 'ث', 'أ', 'خ', 'ج', 'س'] : ['S', 'M', 'T', 'W', 'T', 'F', 'S']).map((d, i) => (
                                                        <span key={i} className="text-[9px] font-black text-slate-400 text-center py-1">
                                                            {d}
                                                        </span>
                                                    ))}
                                                </div>
                                                
                                                <div className="grid grid-cols-7 gap-1">
                                                    {days.map((day, idx) => {
                                                        const isSelected = isSameDay(day, selectedDate);
                                                        const currentMonth = isSameMonth(day, viewDate);
                                                        const today = isToday(day);
                                                        
                                                        return (
                                                            <button
                                                                key={idx}
                                                                type="button"
                                                                onClick={() => handleDateSelect(day, close)}
                                                                className={`
                                                                    h-8 w-8 md:h-9 md:w-9 flex items-center justify-center rounded-xl text-xs font-bold transition-all relative
                                                                    ${isSelected ? 'bg-primary text-white shadow-lg shadow-primary/30 scale-110 z-10' : 
                                                                      currentMonth ? 'text-text-primary hover:bg-primary/10' : 'text-slate-300 dark:text-slate-700'}
                                                                `}
                                                            >
                                                                {format(day, 'd')}
                                                                {today && !isSelected && (
                                                                    <div className="absolute bottom-1 w-1 h-1 bg-primary rounded-full" />
                                                                )}
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            </>
                                        )}

                                        <div className="mt-4 pt-4 border-t border-border/50 flex justify-center">
                                            <button
                                                type="button"
                                                onClick={() => handleToday(close)}
                                                className="text-[10px] font-black text-primary bg-primary/5 px-4 py-1.5 rounded-full hover:bg-primary/10 transition-colors uppercase tracking-widest"
                                            >
                                                {t('common.today', 'Today')}
                                            </button>
                                        </div>
                                    </div>

                                    {/* Time Section */}
                                    {!isDateOnly && !isMonthOnly && (
                                        <div className="bg-slate-50/50 dark:bg-black/20 p-5 w-full md:w-40 flex flex-col gap-4">
                                            <div className="flex items-center gap-2 text-primary mb-1">
                                                <Clock size={16} />
                                                <span className="text-[10px] font-black uppercase tracking-widest">{t('common.time', 'Time')}</span>
                                            </div>
                                            
                                            <div className="flex md:flex-col gap-3 h-full overflow-y-auto pr-1 custom-scrollbar">
                                                <div className="flex-1 space-y-2">
                                                    <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{t('common.hour', 'Hour')}</label>
                                                    <div className="grid grid-cols-4 md:grid-cols-2 gap-1">
                                                        {[12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(h => (
                                                            <button
                                                                key={h}
                                                                type="button"
                                                                onClick={() => handleTimeChange('hours', h)}
                                                                className={`py-1.5 rounded-lg text-[10px] font-bold transition-all ${tempTime.hours === h ? 'bg-primary text-white shadow-md' : 'bg-white dark:bg-slate-800 text-text-primary border border-transparent'}`}
                                                            >
                                                                {h}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>

                                                <div className="flex-1 space-y-2">
                                                    <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{t('common.minute', 'Min')}</label>
                                                    <div className="grid grid-cols-4 md:grid-cols-2 gap-1">
                                                        {[0, 15, 30, 45].map(m => (
                                                            <button
                                                                key={m}
                                                                type="button"
                                                                onClick={() => handleTimeChange('minutes', m)}
                                                                className={`py-1.5 rounded-lg text-[10px] font-bold transition-all ${tempTime.minutes === m ? 'bg-primary text-white shadow-md' : 'bg-white dark:bg-slate-800 text-text-primary border border-transparent'}`}
                                                            >
                                                                {m.toString().padStart(2, '0')}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>

                                                <div className="flex gap-1 p-1 bg-white dark:bg-slate-800 rounded-xl border border-border mt-auto shadow-sm">
                                                    {['AM', 'PM'].map(p => (
                                                        <button
                                                            key={p}
                                                            type="button"
                                                            onClick={() => handleTimeChange('ampm', p)}
                                                            className={`flex-1 py-1 rounded-lg text-[9px] font-black transition-all ${tempTime.ampm === p ? 'bg-primary text-white shadow-sm' : 'text-slate-400 hover:text-text-primary'}`}
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
                    </>
                )}
            </Popover>
            {!compact && error && <p className="text-xs font-bold text-red-500 mt-1">{error}</p>}
        </div>
    );
}


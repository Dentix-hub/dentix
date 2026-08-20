import { useEffect, useMemo, useRef, useState } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { Calendar as CalendarIcon, Clock, ChevronLeft, ChevronRight, Check, ChevronDown, X } from 'lucide-react';
import {
    format,
    addMonths,
    subMonths,
    startOfMonth,
    endOfMonth,
    startOfWeek,
    endOfWeek,
    eachDayOfInterval,
    isSameMonth,
    isSameDay,
    isToday,
    parseISO,
    isValid
} from 'date-fns';
import { useTranslation } from 'react-i18next';

function parsePickerValue(value, isMonthOnly) {
    if (!value) return new Date();
    let dateToParse = value;
    if (isMonthOnly && typeof value === 'string' && value.length === 7) {
        dateToParse = `${value}-01`;
    }
    const parsed = typeof dateToParse === 'string' ? parseISO(dateToParse) : new Date(dateToParse);
    return isValid(parsed) ? parsed : new Date();
}

export default function DateTimePicker({
    value,
    onChange,
    label,
    error,
    required,
    mode = 'datetime',
    placeholder,
    compact = false
}) {
    const { t, i18n } = useTranslation();
    const isArabic = i18n.language === 'ar';
    const isDateOnly = mode === 'date';
    const isMonthOnly = mode === 'month';
    const initialDate = useMemo(() => parsePickerValue(value, isMonthOnly), [value, isMonthOnly]);

    const [isOpen, setIsOpen] = useState(false);
    const [viewMode, setViewMode] = useState(isMonthOnly ? 'months' : 'days');
    const [viewDate, setViewDate] = useState(initialDate);
    const [selectedDate, setSelectedDate] = useState(initialDate);
    const [tempTime, setTempTime] = useState({
        hours: initialDate.getHours() % 12 || 12,
        minutes: Math.floor(initialDate.getMinutes() / 5) * 5,
        ampm: initialDate.getHours() >= 12 ? 'PM' : 'AM'
    });
    const activeYearRef = useRef(null);

    useEffect(() => {
        if (!isOpen) return;
        setViewDate(initialDate);
        setSelectedDate(initialDate);
        setTempTime({
            hours: initialDate.getHours() % 12 || 12,
            minutes: Math.floor(initialDate.getMinutes() / 5) * 5,
            ampm: initialDate.getHours() >= 12 ? 'PM' : 'AM'
        });
        setViewMode(isMonthOnly ? 'months' : 'days');
    }, [isOpen, initialDate, isMonthOnly]);

    useEffect(() => {
        if (viewMode === 'years' && activeYearRef.current) {
            activeYearRef.current.scrollIntoView({ block: 'center', behavior: 'auto' });
        }
    }, [viewMode]);

    const days = useMemo(() => {
        const start = startOfWeek(startOfMonth(viewDate));
        const end = endOfWeek(endOfMonth(viewDate));
        return eachDayOfInterval({ start, end });
    }, [viewDate]);

    const years = useMemo(() => {
        const currentYear = new Date().getFullYear();
        return Array.from({ length: 101 }, (_, index) => currentYear - 80 + index);
    }, []);

    const emitDate = (date) => {
        if (isMonthOnly) {
            onChange({ target: { value: format(date, 'yyyy-MM') } });
            return;
        }
        if (isDateOnly) {
            onChange({ target: { value: format(date, 'yyyy-MM-dd') } });
            return;
        }
        let hour = tempTime.hours === 12 ? 0 : tempTime.hours;
        if (tempTime.ampm === 'PM') hour += 12;
        const finalDate = new Date(date);
        finalDate.setHours(hour, tempTime.minutes, 0, 0);
        onChange({ target: { value: finalDate.toISOString() } });
    };

    const handleConfirm = () => {
        emitDate(selectedDate);
        setIsOpen(false);
    };

    const handleDateClick = (day) => {
        setSelectedDate(day);
        if (isDateOnly || isMonthOnly) {
            emitDate(day);
            setIsOpen(false);
        }
    };

    const handleToday = () => {
        const now = new Date();
        setSelectedDate(now);
        setViewDate(now);
        if (isDateOnly || isMonthOnly) {
            emitDate(now);
            setIsOpen(false);
        }
    };

    const handleMonthSelect = (month) => {
        const newDate = new Date(viewDate);
        newDate.setMonth(month);
        setViewDate(newDate);
        if (isMonthOnly) {
            setSelectedDate(newDate);
            emitDate(newDate);
            setIsOpen(false);
        } else {
            setViewMode('days');
        }
    };

    const handleYearSelect = (year) => {
        const newDate = new Date(viewDate);
        newDate.setFullYear(year);
        setViewDate(newDate);
        setViewMode('months');
    };

    const moveViewBackward = () => {
        setViewDate(current => subMonths(current, viewMode === 'years' ? 120 : viewMode === 'months' ? 12 : 1));
    };

    const moveViewForward = () => {
        setViewDate(current => addMonths(current, viewMode === 'years' ? 120 : viewMode === 'months' ? 12 : 1));
    };

    const cycleViewMode = () => {
        setViewMode(current => current === 'days' ? 'months' : current === 'months' ? 'years' : 'days');
    };

    const displayValue = !value && placeholder
        ? placeholder
        : isMonthOnly
            ? format(initialDate, 'MMMM yyyy')
            : isDateOnly
                ? format(initialDate, 'yyyy-MM-dd')
                : format(initialDate, 'yyyy-MM-dd hh:mm a');

    return (
        <div className={`w-full min-w-0 ${compact ? '' : 'space-y-1.5'}`}>
            {!compact && label && (
                <label className="block text-sm font-bold text-text-primary">
                    {label}
                    {required && <span className="ms-1 text-red-500">*</span>}
                </label>
            )}

            <button
                type="button"
                onClick={() => setIsOpen(true)}
                className={`flex min-h-11 w-full min-w-0 items-center justify-between gap-2 rounded-2xl border-2 bg-surface text-sm font-bold text-text-primary shadow-sm outline-none transition-all hover:border-primary/40 hover:bg-slate-50 focus:ring-4 focus:ring-primary/10 dark:hover:bg-slate-800 ${compact ? 'px-3 py-1.5' : 'px-3 py-2.5 sm:px-4 sm:py-3'} ${error ? 'border-red-300' : 'border-border'}`}
                aria-haspopup="dialog"
                aria-expanded={isOpen}
            >
                <span className="flex min-w-0 items-center gap-2.5">
                    <span className={`shrink-0 rounded-lg p-1.5 transition-colors ${isOpen ? 'bg-primary text-white' : 'bg-primary/10 text-primary'}`}>
                        {isDateOnly || isMonthOnly ? <CalendarIcon size={compact ? 12 : 14} aria-hidden="true" /> : <Clock size={compact ? 12 : 14} aria-hidden="true" />}
                    </span>
                    <span dir="ltr" className={`min-w-0 truncate ${!value && placeholder ? 'font-medium text-slate-500' : ''} ${compact ? 'text-xs' : 'text-sm'}`}>
                        {displayValue}
                    </span>
                </span>
                <ChevronDown className={`h-4 w-4 shrink-0 text-slate-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
            </button>

            <DialogPrimitive.Root open={isOpen} onOpenChange={setIsOpen}>
                <DialogPrimitive.Portal>
                    <DialogPrimitive.Overlay className="fixed inset-0 z-[9998] bg-backdrop backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in data-[state=closed]:fade-out motion-reduce:animate-none motion-reduce:backdrop-blur-none" />
                    <DialogPrimitive.Content
                        aria-describedby={undefined}
                        className="fixed inset-x-0 bottom-0 z-[9999] mx-auto flex max-h-[calc(100dvh-0.5rem)] w-full max-w-2xl flex-col overflow-hidden rounded-t-overlay border border-b-0 border-border bg-surface-elevated text-start align-middle shadow-high outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:slide-in-from-bottom-6 data-[state=closed]:slide-out-to-bottom-6 duration-emphasized motion-reduce:animate-none sm:bottom-auto sm:left-1/2 sm:top-1/2 sm:mx-0 sm:max-h-[calc(100dvh-2rem)] sm:w-[calc(100%-2rem)] sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-overlay sm:border-b sm:data-[state=open]:zoom-in-95 sm:data-[state=closed]:zoom-out-95"
                    >
                        <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-border px-3 py-2.5 sm:px-4">
                            <DialogPrimitive.Title className="min-w-0 truncate text-sm font-bold text-text-primary sm:text-base">
                                {label || t('common.date_time', isDateOnly || isMonthOnly ? 'Date' : 'Date & time')}
                            </DialogPrimitive.Title>
                            <button
                                type="button"
                                onClick={() => setIsOpen(false)}
                                className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-text-muted transition-colors hover:bg-surface-subtle hover:text-text-primary"
                                aria-label={t('common.close', 'Close')}
                            >
                                <X size={20} aria-hidden="true" />
                            </button>
                        </div>

                                    <div className={`min-h-0 flex-1 overflow-y-auto overscroll-contain ${isDateOnly || isMonthOnly ? '' : 'md:grid md:grid-cols-[minmax(0,1fr)_17.5rem]'}`}>
                                        <section className="flex min-w-0 flex-col p-3 sm:p-4 md:p-5">
                                            <div className="mb-3 flex min-w-0 items-center justify-between gap-1 sm:mb-5 sm:gap-2">
                                                <button
                                                    type="button"
                                                    onClick={moveViewBackward}
                                                    className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-slate-500 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                                                    aria-label={t('common.previous', 'Previous')}
                                                >
                                                    <ChevronLeft size={20} className="rtl:rotate-180" aria-hidden="true" />
                                                </button>

                                                <button
                                                    type="button"
                                                    onClick={cycleViewMode}
                                                    className="min-h-11 min-w-0 rounded-xl px-2 py-2 transition-colors hover:bg-primary/10 sm:px-4"
                                                >
                                                    <span className="flex min-w-0 items-center justify-center gap-1.5 text-sm font-bold text-text-primary sm:text-lg">
                                                        <span className="min-w-0 truncate">
                                                            {viewMode === 'years'
                                                                ? `${years[0]} - ${years[years.length - 1]}`
                                                                : viewMode === 'months'
                                                                    ? format(viewDate, 'yyyy')
                                                                    : `${format(viewDate, 'MMMM')} ${format(viewDate, 'yyyy')}`}
                                                        </span>
                                                        <ChevronDown size={14} className="shrink-0 text-primary opacity-60" aria-hidden="true" />
                                                    </span>
                                                </button>

                                                <button
                                                    type="button"
                                                    onClick={moveViewForward}
                                                    className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-slate-500 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                                                    aria-label={t('common.next', 'Next')}
                                                >
                                                    <ChevronRight size={20} className="rtl:rotate-180" aria-hidden="true" />
                                                </button>
                                            </div>

                                            <div className="min-h-0 flex-1">
                                                {viewMode === 'years' ? (
                                                    <div className="grid max-h-[45dvh] grid-cols-3 gap-2 overflow-y-auto overscroll-contain pe-1 min-[360px]:grid-cols-4 sm:max-h-[24rem]">
                                                        {years.map(year => (
                                                            <button
                                                                key={year}
                                                                ref={viewDate.getFullYear() === year ? activeYearRef : null}
                                                                type="button"
                                                                onClick={() => handleYearSelect(year)}
                                                                className={`min-h-11 rounded-xl px-1 py-2 text-sm font-bold transition-colors ${viewDate.getFullYear() === year ? 'bg-primary text-white shadow-medium' : 'text-text-primary hover:bg-primary/10'}`}
                                                            >
                                                                {year}
                                                            </button>
                                                        ))}
                                                    </div>
                                                ) : viewMode === 'months' ? (
                                                    <div className="grid grid-cols-3 gap-2 sm:gap-3">
                                                        {Array.from({ length: 12 }, (_, month) => month).map(month => {
                                                            const monthDate = new Date(viewDate.getFullYear(), month, 1);
                                                            const isSelectedMonth = isSameMonth(monthDate, selectedDate);
                                                            return (
                                                                <button
                                                                    key={month}
                                                                    type="button"
                                                                    onClick={() => handleMonthSelect(month)}
                                                                    className={`min-h-12 rounded-xl px-1 py-3 text-xs font-bold transition-colors sm:min-h-14 sm:text-sm ${isSelectedMonth ? 'bg-primary text-white shadow-medium' : 'text-text-primary hover:bg-primary/10'}`}
                                                                >
                                                                    {format(monthDate, 'MMM')}
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                ) : (
                                                    <>
                                                        <div className="mb-2 grid grid-cols-7 gap-1">
                                                            {(isArabic ? ['ح', 'ن', 'ث', 'ر', 'خ', 'ج', 'س'] : ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']).map((dayLabel, index) => (
                                                                <span key={index} className="py-1 text-center text-[10px] font-bold uppercase tracking-wide text-slate-500">
                                                                    {dayLabel}
                                                                </span>
                                                            ))}
                                                        </div>
                                                        <div className="grid grid-cols-7 gap-1 sm:gap-1.5">
                                                            {days.map(day => {
                                                                const isSelectedDay = isSameDay(day, selectedDate);
                                                                const inCurrentMonth = isSameMonth(day, viewDate);
                                                                const today = isToday(day);
                                                                return (
                                                                    <button
                                                                        key={day.toISOString()}
                                                                        type="button"
                                                                        onClick={() => handleDateClick(day)}
                                                                        className={`relative flex aspect-square min-h-9 min-w-0 items-center justify-center rounded-xl text-xs font-bold transition-colors sm:min-h-10 sm:text-sm ${isSelectedDay ? 'bg-primary text-white shadow-medium' : inCurrentMonth ? 'text-text-primary hover:bg-primary/10' : 'text-slate-400 opacity-45'}`}
                                                                        aria-pressed={isSelectedDay}
                                                                    >
                                                                        {format(day, 'd')}
                                                                        {today && !isSelectedDay && <span className="absolute end-1 top-1 h-1.5 w-1.5 rounded-full bg-primary" />}
                                                                    </button>
                                                                );
                                                            })}
                                                        </div>
                                                    </>
                                                )}
                                            </div>

                                            <div className="sticky bottom-0 mt-4 flex gap-2 border-t border-border bg-surface-elevated pt-3 sm:mt-6 sm:gap-3">
                                                <button
                                                    type="button"
                                                    onClick={handleToday}
                                                    className="min-h-11 flex-1 rounded-xl bg-surface-subtle px-3 py-2 text-xs font-bold text-text-primary transition-colors hover:bg-surface-hover"
                                                >
                                                    {t('common.today', 'Today')}
                                                </button>
                                                {!isDateOnly && !isMonthOnly && (
                                                    <button
                                                        type="button"
                                                        onClick={handleConfirm}
                                                        className="flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-3 py-2 text-xs font-bold text-white shadow-medium transition-colors hover:bg-primary-hover"
                                                    >
                                                        <Check size={16} aria-hidden="true" />
                                                        {t('common.confirm', 'Confirm')}
                                                    </button>
                                                )}
                                            </div>
                                        </section>

                                        {!isDateOnly && !isMonthOnly && (
                                            <section className="min-w-0 border-t border-border bg-surface-subtle p-3 sm:p-4 md:border-s md:border-t-0 md:p-5">
                                                <div className="mb-4 flex items-center gap-2 text-primary">
                                                    <span className="rounded-lg bg-primary/10 p-1.5"><Clock size={16} aria-hidden="true" /></span>
                                                    <span className="text-xs font-bold uppercase tracking-[0.15em]">{t('common.time', 'Time')}</span>
                                                </div>

                                                <div className="space-y-4">
                                                    <div>
                                                        <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('common.hour', 'Hour')}</label>
                                                        <div className="grid grid-cols-6 gap-1.5 md:grid-cols-4 md:gap-2">
                                                            {[12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(hour => (
                                                                <button
                                                                    key={hour}
                                                                    type="button"
                                                                    onClick={() => setTempTime(current => ({ ...current, hours: hour }))}
                                                                    className={`min-h-11 rounded-xl text-xs font-bold transition-colors ${tempTime.hours === hour ? 'bg-primary text-white shadow-medium' : 'border border-border bg-surface-elevated text-text-primary hover:bg-surface-hover'}`}
                                                                >
                                                                    {hour}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    </div>

                                                    <div>
                                                        <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('common.minute', 'Minutes')}</label>
                                                        <div className="grid grid-cols-4 gap-2">
                                                            {[0, 15, 30, 45].map(minute => (
                                                                <button
                                                                    key={minute}
                                                                    type="button"
                                                                    onClick={() => setTempTime(current => ({ ...current, minutes: minute }))}
                                                                    className={`min-h-11 rounded-xl text-xs font-bold transition-colors ${tempTime.minutes === minute ? 'bg-primary text-white shadow-medium' : 'border border-border bg-surface-elevated text-text-primary hover:bg-surface-hover'}`}
                                                                >
                                                                    {minute.toString().padStart(2, '0')}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-2 rounded-xl border border-border bg-surface-elevated p-1.5">
                                                        {['AM', 'PM'].map(period => (
                                                            <button
                                                                key={period}
                                                                type="button"
                                                                onClick={() => setTempTime(current => ({ ...current, ampm: period }))}
                                                                className={`min-h-11 rounded-lg text-xs font-bold transition-colors ${tempTime.ampm === period ? 'bg-primary text-white shadow-low' : 'text-slate-500 hover:bg-surface-hover hover:text-text-primary'}`}
                                                            >
                                                                {period}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            </section>
                                        )}
                                    </div>
                    </DialogPrimitive.Content>
                </DialogPrimitive.Portal>
            </DialogPrimitive.Root>

            {!compact && error && <p className="mt-1 text-xs font-bold text-red-500">{error}</p>}
        </div>
    );
}

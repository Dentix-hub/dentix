import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Calendar as CalendarIcon, ChevronDown, Check } from 'lucide-react';
import { DATE_PRESETS, getPresetDates, formatRangeLabel } from '../utils/datePresets';

/**
 * Date Range Picker for Finance V2.
 * Synchronizes with URL search params `from` and `to`.
 */
export default function DateRangePicker({ className = '' }) {
    const [searchParams, setSearchParams] = useSearchParams();
    const { t, i18n } = useTranslation();
    const isArabic = i18n.language === 'ar';

    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    // Initial state derived from searchParams or default 'this_month'
    const fromParam = searchParams.get('from');
    const toParam = searchParams.get('to');
    const presetParam = searchParams.get('preset') || (fromParam && toParam ? 'custom' : 'this_month');

    const defaultDates = getPresetDates('this_month');
    const currentFrom = fromParam || defaultDates.from;
    const currentTo = toParam || defaultDates.to;

    const [customFrom, setCustomFrom] = useState(currentFrom);
    const [customTo, setCustomTo] = useState(currentTo);

    // Close dropdown on outside click
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelectPreset = (presetId) => {
        if (presetId === 'custom') {
            // Keep open so user can adjust inputs
            return;
        }
        const { from, to } = getPresetDates(presetId);
        const newParams = new URLSearchParams(searchParams);
        newParams.set('from', from);
        newParams.set('to', to);
        newParams.set('preset', presetId);
        setSearchParams(newParams);
        setCustomFrom(from);
        setCustomTo(to);
        setIsOpen(false);
    };

    const handleApplyCustom = (e) => {
        e.preventDefault();
        if (customFrom && customTo) {
            const newParams = new URLSearchParams(searchParams);
            newParams.set('from', customFrom);
            newParams.set('to', customTo);
            newParams.set('preset', 'custom');
            setSearchParams(newParams);
            setIsOpen(false);
        }
    };

    const displayLabel = formatRangeLabel(currentFrom, currentTo, isArabic ? 'ar' : 'en');
    const activePreset = DATE_PRESETS.find((p) => p.id === presetParam);
    const presetName = isArabic ? activePreset?.labelAr : activePreset?.labelEn;

    return (
        <div className={`relative inline-block text-start ${className}`} ref={dropdownRef}>
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-border bg-card hover:bg-muted text-text-primary transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                aria-expanded={isOpen}
                aria-haspopup="true"
            >
                <CalendarIcon className="w-4 h-4 text-primary flex-shrink-0" />
                <span className="font-semibold text-text-secondary">
                    {presetName ? `${presetName}:` : ''}
                </span>
                <span className="text-text-primary font-mono text-xs sm:text-sm font-bold">
                    {displayLabel}
                </span>
                <ChevronDown className={`w-4 h-4 text-text-secondary transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div
                    className="absolute end-0 mt-2 w-72 sm:w-80 rounded-xl bg-card border border-border shadow-xl z-50 p-3 space-y-3 animate-in fade-in zoom-in-95 duration-100"
                    role="menu"
                >
                    <div className="text-xs font-bold text-text-secondary uppercase tracking-wider px-1">
                        {t('finance.date_range.presets', 'الفترات المجهزة')}
                    </div>

                    <div className="grid grid-cols-2 gap-1.5">
                        {DATE_PRESETS.filter((p) => p.id !== 'custom').map((preset) => {
                            const isSelected = presetParam === preset.id;
                            return (
                                <button
                                    key={preset.id}
                                    type="button"
                                    onClick={() => handleSelectPreset(preset.id)}
                                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors text-start ${
                                        isSelected
                                            ? 'bg-primary text-white shadow-sm'
                                            : 'hover:bg-muted text-text-primary'
                                    }`}
                                >
                                    <span>{isArabic ? preset.labelAr : preset.labelEn}</span>
                                    {isSelected && <Check className="w-3.5 h-3.5" />}
                                </button>
                            );
                        })}
                    </div>

                    <div className="border-t border-border pt-3 space-y-2">
                        <div className="text-xs font-bold text-text-secondary uppercase tracking-wider px-1">
                            {t('finance.date_range.custom_range', 'نطاق مخصص')}
                        </div>

                        <form onSubmit={handleApplyCustom} className="space-y-2">
                            <div className="grid grid-cols-2 gap-2">
                                <div>
                                    <label className="block text-[11px] font-medium text-text-secondary mb-1">
                                        {t('finance.date_range.from', 'من')}
                                    </label>
                                    <input
                                        type="date"
                                        value={customFrom}
                                        onChange={(e) => setCustomFrom(e.target.value)}
                                        className="w-full text-xs font-mono px-2 py-1.5 rounded-md border border-border bg-background text-text-primary focus:ring-1 focus:ring-primary focus:outline-none"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-[11px] font-medium text-text-secondary mb-1">
                                        {t('finance.date_range.to', 'إلى')}
                                    </label>
                                    <input
                                        type="date"
                                        value={customTo}
                                        onChange={(e) => setCustomTo(e.target.value)}
                                        className="w-full text-xs font-mono px-2 py-1.5 rounded-md border border-border bg-background text-text-primary focus:ring-1 focus:ring-primary focus:outline-none"
                                        required
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                className="w-full py-1.5 px-3 text-xs font-bold text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors shadow-sm"
                            >
                                {t('finance.date_range.apply', 'تطبيق الفلتر')}
                            </button>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

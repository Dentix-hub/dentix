import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Calendar as CalendarIcon, ChevronDown, Check } from 'lucide-react';
import DentixBottomSheet from '@/shared/ui/DentixBottomSheet';
import DentixPopover from '@/shared/ui/DentixPopover';
import { DATE_PRESETS, getPresetDates, formatRangeLabel } from '../utils/datePresets';

/**
 * Date Range Picker for Finance V2.
 * Synchronizes with URL search params `from` and `to`.
 *
 * Compact screens use the canonical bottom sheet so the controls are never
 * clipped by page overflow or the application sidebar. Larger screens use the
 * canonical anchored/ported popover and align from the logical start edge so
 * it opens toward the content area in both LTR and RTL layouts.
 */
export default function DateRangePicker({ className = '' }) {
    const [searchParams, setSearchParams] = useSearchParams();
    const { t, i18n } = useTranslation();
    const isArabic = (i18n.resolvedLanguage || i18n.language || '').toLowerCase().startsWith('ar');
    const [isMobileOpen, setIsMobileOpen] = useState(false);

    // Initial/current state derived from searchParams or default 'this_month'.
    const fromParam = searchParams.get('from');
    const toParam = searchParams.get('to');
    const presetParam = searchParams.get('preset') || (fromParam && toParam ? 'custom' : 'this_month');

    const defaultDates = getPresetDates('this_month');
    const currentFrom = fromParam || defaultDates.from;
    const currentTo = toParam || defaultDates.to;

    const [customFrom, setCustomFrom] = useState(currentFrom);
    const [customTo, setCustomTo] = useState(currentTo);

    useEffect(() => {
        setCustomFrom(currentFrom);
        setCustomTo(currentTo);
    }, [currentFrom, currentTo]);

    const handleSelectPreset = (presetId, close) => {
        if (presetId === 'custom') return;

        const { from, to } = getPresetDates(presetId);
        const newParams = new URLSearchParams(searchParams);
        newParams.set('from', from);
        newParams.set('to', to);
        newParams.set('preset', presetId);
        newParams.set('page', '1');
        setSearchParams(newParams);
        setCustomFrom(from);
        setCustomTo(to);
        close?.();
    };

    const handleApplyCustom = (event, close) => {
        event.preventDefault();
        if (!customFrom || !customTo) return;

        const newParams = new URLSearchParams(searchParams);
        newParams.set('from', customFrom);
        newParams.set('to', customTo);
        newParams.set('preset', 'custom');
        newParams.set('page', '1');
        setSearchParams(newParams);
        close?.();
    };

    const displayLabel = formatRangeLabel(currentFrom, currentTo, isArabic ? 'ar' : 'en');
    const activePreset = DATE_PRESETS.find((preset) => preset.id === presetParam);
    const presetName = isArabic ? activePreset?.labelAr : activePreset?.labelEn;

    const trigger = (mobile = false) => (
        <button
            type="button"
            onClick={mobile ? () => setIsMobileOpen(true) : undefined}
            className={`group inline-flex min-w-0 items-center gap-2 rounded-control border border-border bg-card px-3 py-2 text-sm font-medium text-text-primary shadow-sm transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${mobile ? 'w-full justify-between' : 'max-w-full'}`}
        >
            <CalendarIcon className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
            <span className="min-w-0 flex-1 text-start">
                {presetName && (
                    <span className="me-1 font-semibold text-text-secondary">
                        {presetName}:
                    </span>
                )}
                <span className="font-mono text-xs font-bold text-text-primary sm:text-sm">
                    {displayLabel}
                </span>
            </span>
            <ChevronDown
                className="h-4 w-4 shrink-0 text-text-secondary transition-transform group-data-[open]:rotate-180"
                aria-hidden="true"
            />
        </button>
    );

    const renderControls = (close) => (
        <div className="space-y-3">
            <div className="px-1 text-xs font-bold uppercase tracking-wider text-text-secondary">
                {t('finance.date_range.presets', isArabic ? 'الفترات المجهزة' : 'Presets')}
            </div>

            <div className="grid grid-cols-2 gap-1.5">
                {DATE_PRESETS.filter((preset) => preset.id !== 'custom').map((preset) => {
                    const isSelected = presetParam === preset.id;
                    return (
                        <button
                            key={preset.id}
                            type="button"
                            onClick={() => handleSelectPreset(preset.id, close)}
                            className={`flex min-h-9 items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-start text-xs font-semibold transition-colors ${
                                isSelected
                                    ? 'bg-primary text-white shadow-sm'
                                    : 'text-text-primary hover:bg-muted'
                            }`}
                        >
                            <span>{isArabic ? preset.labelAr : preset.labelEn}</span>
                            {isSelected && <Check className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
                        </button>
                    );
                })}
            </div>

            <div className="space-y-2 border-t border-border pt-3">
                <div className="px-1 text-xs font-bold uppercase tracking-wider text-text-secondary">
                    {t('finance.date_range.custom_range', isArabic ? 'نطاق مخصص' : 'Custom range')}
                </div>

                <form onSubmit={(event) => handleApplyCustom(event, close)} className="space-y-3">
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <div>
                            <label className="mb-1 block text-[11px] font-medium text-text-secondary">
                                {t('finance.date_range.from', isArabic ? 'من' : 'From')}
                            </label>
                            <input
                                type="date"
                                value={customFrom}
                                onChange={(event) => setCustomFrom(event.target.value)}
                                className="w-full rounded-md border border-border bg-input px-2 py-2 font-mono text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                                required
                            />
                        </div>
                        <div>
                            <label className="mb-1 block text-[11px] font-medium text-text-secondary">
                                {t('finance.date_range.to', isArabic ? 'إلى' : 'To')}
                            </label>
                            <input
                                type="date"
                                value={customTo}
                                onChange={(event) => setCustomTo(event.target.value)}
                                className="w-full rounded-md border border-border bg-input px-2 py-2 font-mono text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="w-full rounded-lg bg-primary px-3 py-2 text-xs font-bold text-white shadow-sm transition-colors hover:bg-primary/90"
                    >
                        {t('finance.date_range.apply', isArabic ? 'تطبيق الفلتر' : 'Apply filter')}
                    </button>
                </form>
            </div>
        </div>
    );

    return (
        <div className={`min-w-0 ${className}`}>
            <div className="sm:hidden">
                {trigger(true)}
                <DentixBottomSheet
                    open={isMobileOpen}
                    onOpenChange={setIsMobileOpen}
                    title={t('finance.date_range.title', isArabic ? 'اختيار الفترة' : 'Select date range')}
                    closeLabel={t('common.close', isArabic ? 'إغلاق' : 'Close')}
                    className="max-w-xl"
                >
                    {renderControls(() => setIsMobileOpen(false))}
                </DentixBottomSheet>
            </div>

            <div className="hidden sm:inline-block max-w-full">
                <DentixPopover
                    trigger={trigger(false)}
                    anchor="bottom start"
                    gap={8}
                    padding={12}
                    rootClassName="inline-block max-w-full"
                    className="max-h-[calc(100dvh-1rem)] w-80 max-w-[calc(100vw-1rem)] overflow-y-auto p-3"
                >
                    {({ close }) => renderControls(close)}
                </DentixPopover>
            </div>
        </div>
    );
}

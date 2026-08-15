import { useTranslation } from 'react-i18next';
import { ChevronLeft, ChevronRight, Calendar, RotateCcw } from 'lucide-react';
import { getCurrentMonthStr } from '../hooks/usePayroll';

/**
 * Month-based time control specifically designed for monthly Payroll workflows (§16 MASTER_SPEC).
 */
export default function MonthPicker({ month, onChange }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const currentMonth = getCurrentMonthStr();

    // Parse current value
    const [yearStr, monStr] = (month || currentMonth).split('-');
    const year = parseInt(yearStr, 10);
    const mon = parseInt(monStr, 10);

    const dateObj = new Date(year, mon - 1, 1);
    const formattedMonth = dateObj.toLocaleDateString(isRtl ? 'ar-EG' : 'en-US', {
        month: 'long',
        year: 'numeric',
    });

    const handlePrev = () => {
        let prevYear = year;
        let prevMon = mon - 1;
        if (prevMon < 1) {
            prevMon = 12;
            prevYear -= 1;
        }
        onChange(`${prevYear}-${String(prevMon).padStart(2, '0')}`);
    };

    const handleNext = () => {
        let nextYear = year;
        let nextMon = mon + 1;
        if (nextMon > 12) {
            nextMon = 1;
            nextYear += 1;
        }
        onChange(`${nextYear}-${String(nextMon).padStart(2, '0')}`);
    };

    const isCurrent = month === currentMonth;

    return (
        <div className="inline-flex items-center gap-2 bg-card border border-border rounded-xl p-1.5 shadow-xs">
            <button
                type="button"
                onClick={handlePrev}
                className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-muted transition-colors"
                title={t('common.prev_month', 'الشهر السابق')}
            >
                {isRtl ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>

            <div className="flex items-center gap-2 px-3 py-1 bg-muted/40 rounded-lg">
                <Calendar className="w-4 h-4 text-primary" />
                <span className="text-xs sm:text-sm font-bold text-text-primary">
                    {formattedMonth}
                </span>
            </div>

            <button
                type="button"
                onClick={handleNext}
                className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-muted transition-colors"
                title={t('common.next_month', 'الشهر التالي')}
            >
                {isRtl ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>

            {!isCurrent && (
                <button
                    type="button"
                    onClick={() => onChange(currentMonth)}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-bold text-primary hover:bg-primary/10 rounded-lg transition-colors ms-1 border border-primary/20"
                >
                    <RotateCcw className="w-3 h-3" />
                    <span>{t('finance.payroll.current_month', 'الشهر الحالي')}</span>
                </button>
            )}
        </div>
    );
}

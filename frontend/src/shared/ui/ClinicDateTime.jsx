import { useEffect, useMemo, useState } from 'react';
import { CalendarDays, Clock3 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { DEFAULT_TENANT_TIMEZONE } from '@/utils/dateTime';

function getSafeTimeZone(timeZone) {
    const candidate = timeZone || DEFAULT_TENANT_TIMEZONE;
    try {
        new Intl.DateTimeFormat('en', { timeZone: candidate }).format(new Date());
        return candidate;
    } catch {
        return DEFAULT_TENANT_TIMEZONE;
    }
}

const ClinicDateTime = ({ timeZone }) => {
    const { i18n } = useTranslation();
    const [now, setNow] = useState(() => new Date());
    const safeTimeZone = useMemo(() => getSafeTimeZone(timeZone), [timeZone]);

    useEffect(() => {
        setNow(new Date());
        const timer = window.setInterval(() => setNow(new Date()), 1000);
        return () => window.clearInterval(timer);
    }, [safeTimeZone]);

    const isArabic = (i18n.resolvedLanguage || i18n.language || '').toLowerCase().startsWith('ar');
    const locale = isArabic ? 'ar-EG' : 'en-GB';

    const timeText = new Intl.DateTimeFormat(locale, {
        timeZone: safeTimeZone,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: isArabic,
    }).format(now);

    const dateText = new Intl.DateTimeFormat(locale, {
        timeZone: safeTimeZone,
        weekday: 'short',
        day: 'numeric',
        month: 'short',
    }).format(now);

    return (
        <time
            dateTime={now.toISOString()}
            title={safeTimeZone}
            aria-label={`${dateText} ${timeText}`}
            className="hidden xl:flex shrink-0 min-w-[10rem] flex-col justify-center rounded-xl border border-border/60 bg-background/70 px-3 py-1.5 text-text-primary"
        >
            <span className="flex items-center gap-2 text-sm font-bold leading-5">
                <Clock3 size={15} className="text-primary shrink-0" aria-hidden="true" />
                <span dir="ltr">{timeText}</span>
            </span>
            <span className="mt-0.5 flex items-center gap-2 text-[11px] font-medium leading-4 text-text-secondary whitespace-nowrap">
                <CalendarDays size={14} className="shrink-0" aria-hidden="true" />
                <span>{dateText}</span>
            </span>
        </time>
    );
};

export default ClinicDateTime;

import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Sparkles, Check } from 'lucide-react';
import { DentixTooltip } from '@/shared/ui';
import { useOnboarding } from '../hooks/useOnboarding';

const OnboardingTooltip = memo(function OnboardingTooltip({
    tipKey,
    content,
    children,
    side = 'top',
    align = 'center',
}) {
    const { t } = useTranslation();
    const { isTipSeen, markTipSeen, status } = useOnboarding();

    // If onboarding is disabled or tip already seen, render regular children
    if (!status?.enabled || isTipSeen(tipKey)) {
        return children;
    }

    const handleDismiss = (e) => {
        e?.stopPropagation?.();
        markTipSeen(tipKey);
    };

    const tooltipBody = (
        <div className="max-w-xs p-2 text-start space-y-2">
            <div className="flex items-center gap-1.5 font-bold text-primary text-xs">
                <Sparkles className="w-3.5 h-3.5 shrink-0" />
                <span>{t('onboarding.tip_badge', 'تلميح مفيد')}</span>
            </div>
            <p className="text-xs text-text-primary leading-relaxed font-normal">{content}</p>
            <div className="pt-1 flex justify-end">
                <button
                    type="button"
                    onClick={handleDismiss}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-bold rounded-lg bg-primary hover:bg-primary-hover text-white transition-colors"
                >
                    <Check className="w-3 h-3" />
                    <span>{t('onboarding.tip_understood', 'فهمت')}</span>
                </button>
            </div>
        </div>
    );

    return (
        <DentixTooltip content={tooltipBody} side={side} align={align}>
            <div className="relative inline-flex items-center">
                {children}
                <span className="absolute -top-1 -end-1 flex h-2.5 w-2.5" title={t('onboarding.new_tip', 'تلميح جديد')}>
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary" />
                </span>
            </div>
        </DentixTooltip>
    );
});

export default OnboardingTooltip;

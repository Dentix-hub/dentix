import { useState, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
    CheckCircle2,
    Circle,
    ChevronDown,
    ChevronUp,
    X,
    Sparkles,
    ArrowLeft,
    ArrowRight,
    Palette,
    RotateCcw,
} from 'lucide-react';
import { useOnboarding } from '../hooks/useOnboarding';

const OnboardingChecklistWidget = memo(function OnboardingChecklistWidget() {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const isRtl = i18n.language === 'ar';
    const ArrowIcon = isRtl ? ArrowLeft : ArrowRight;

    const { status, isLoading, dismiss, restore } = useOnboarding();
    const [collapsed, setCollapsed] = useState(false);

    if (isLoading || !status?.enabled || !status?.steps || status.steps.length === 0) {
        return null;
    }

    const { progress, sections, dismissed } = status;
    const isCompleted = progress.percentage === 100;

    if (dismissed) {
        return (
            <div className="flex items-center justify-between p-3.5 bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/80 rounded-2xl text-xs text-text-muted mb-6">
                <div className="flex items-center gap-2 font-medium">
                    <Sparkles className="text-primary w-4 h-4" />
                    <span>{t('onboarding.dismissed_notice', 'قائمة البداية السريعة مخفية')}</span>
                    <span className="font-bold text-text-primary">
                        ({progress.completed}/{progress.total} - {progress.percentage}%)
                    </span>
                </div>
                <button
                    type="button"
                    onClick={() => restore()}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-white dark:bg-slate-700 hover:bg-slate-100 dark:hover:bg-slate-600 text-text-primary font-bold rounded-xl border border-slate-200 dark:border-slate-600 shadow-xs transition-colors"
                >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>{t('onboarding.restore', 'إظهار الدليل')}</span>
                </button>
            </div>
        );
    }

    return (
        <section
            aria-label={t('onboarding.widget_title', 'دليل البداية السريعة')}
            className="mb-6 rounded-3xl bg-surface border border-slate-200/90 dark:border-slate-800 shadow-sm overflow-hidden"
            dir={isRtl ? 'rtl' : 'ltr'}
        >
            {/* Header */}
            <div className="p-4 sm:p-5 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border-b border-slate-100 dark:border-slate-800/80">
                <div className="flex items-start sm:items-center justify-between gap-3">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="inline-flex items-center justify-center w-7 h-7 rounded-xl bg-primary text-white shadow-xs">
                                <Sparkles className="w-4 h-4" />
                            </span>
                            <h3 className="text-base sm:text-lg font-bold text-text-primary truncate">
                                {isCompleted
                                    ? t('onboarding.all_completed_title', 'أحسنت! اكتملت جميع خطوات الإعداد')
                                    : t('onboarding.widget_title', 'دليل البداية السريعة')}
                            </h3>
                        </div>
                        <p className="text-xs sm:text-sm text-text-muted">
                            {isCompleted
                                ? t('onboarding.all_completed_desc', 'عيادتك جاهزة بالكامل للعمل اليومي المتقدم')
                                : t('onboarding.widget_subtitle', 'أكمل هذه الخطوات السريعة لتجهيز عيادتك والبدء بكفاءة')}
                        </p>
                    </div>

                    <div className="flex items-center gap-1">
                        <button
                            type="button"
                            onClick={() => setCollapsed(!collapsed)}
                            className="p-2 text-text-muted hover:text-text-primary hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
                            aria-label={collapsed ? t('onboarding.expand', 'توسيع') : t('onboarding.collapse', 'طي')}
                        >
                            {collapsed ? <ChevronDown className="w-5 h-5" /> : <ChevronUp className="w-5 h-5" />}
                        </button>
                        <button
                            type="button"
                            onClick={() => dismiss(true)}
                            className="p-2 text-text-muted hover:text-rose-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
                            aria-label={t('onboarding.dismiss', 'إخفاء القائمة')}
                            title={t('onboarding.dismiss', 'إخفاء القائمة')}
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Progress bar */}
                <div className="mt-3 sm:mt-4">
                    <div className="flex items-center justify-between text-xs font-semibold text-text-muted mb-1.5">
                        <span>
                            {t('onboarding.progress_label', 'مستوى الإنجاز')}:{' '}
                            <strong className="text-text-primary font-bold">
                                {progress.completed} {t('onboarding.of', 'من')} {progress.total} {t('onboarding.steps', 'خطوات')}
                            </strong>
                        </span>
                        <span className="font-bold text-primary">{progress.percentage}%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-200 dark:bg-slate-700/80 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-primary transition-all duration-500 rounded-full"
                            style={{ width: `${progress.percentage}%` }}
                        />
                    </div>
                </div>
            </div>

            {/* Steps Body */}
            {!collapsed && (
                <div className="p-4 sm:p-5 space-y-6">
                    {sections.map((section) => (
                        <div key={section.id} className="space-y-3">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted px-1 flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-primary" />
                                {section.title}
                            </h4>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {section.steps.map((step) => {
                                    const isDone = step.done;
                                    const isHighlighted = step.highlight && !isDone;

                                    return (
                                        <div
                                            key={step.id}
                                            className={`relative p-3.5 sm:p-4 rounded-2xl border transition-all ${
                                                isHighlighted
                                                    ? 'bg-amber-500/5 dark:bg-amber-500/10 border-amber-300 dark:border-amber-600/60 shadow-xs'
                                                    : isDone
                                                    ? 'bg-slate-50/70 dark:bg-slate-800/40 border-slate-200/60 dark:border-slate-800'
                                                    : 'bg-white dark:bg-slate-800/90 border-slate-200 dark:border-slate-700 hover:border-primary/50 shadow-xs'
                                            }`}
                                        >
                                            <div className="flex items-start gap-3">
                                                <div className="mt-0.5 shrink-0">
                                                    {isDone ? (
                                                        <CheckCircle2 className="w-5 h-5 text-emerald-500 dark:text-emerald-400" />
                                                    ) : (
                                                        <Circle className="w-5 h-5 text-slate-300 dark:text-slate-600" />
                                                    )}
                                                </div>

                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                                                        <span className="text-[11px] font-mono font-bold px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-700 text-text-muted">
                                                            {step.key}
                                                        </span>
                                                        <span
                                                            className={`text-sm font-bold truncate ${
                                                                isDone
                                                                    ? 'text-text-muted line-through'
                                                                    : 'text-text-primary'
                                                            }`}
                                                        >
                                                            {step.title}
                                                        </span>
                                                        {isHighlighted && (
                                                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-300">
                                                                <Palette className="w-3 h-3" />
                                                                {t('onboarding.highlight_badge', 'مهم للمخطط')}
                                                            </span>
                                                        )}
                                                    </div>

                                                    <p className="text-xs text-text-muted mb-2 leading-relaxed">
                                                        {step.description}
                                                    </p>

                                                    {/* Sub-steps for D5 */}
                                                    {step.sub_steps && step.sub_steps.length > 0 && (
                                                        <div className="my-2 p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800 space-y-1.5">
                                                            {step.sub_steps.map((sub, idx) => (
                                                                <div
                                                                    key={sub.key}
                                                                    className="flex items-center gap-2 text-xs"
                                                                >
                                                                    {sub.done ? (
                                                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                                                                    ) : (
                                                                        <Circle className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600 shrink-0" />
                                                                    )}
                                                                    <span
                                                                        className={
                                                                            sub.done
                                                                                ? 'text-text-muted line-through'
                                                                                : 'text-text-primary font-medium'
                                                                        }
                                                                    >
                                                                        {idx + 1}. {sub.title}
                                                                    </span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}

                                                    {/* Action link */}
                                                    {!isDone && (
                                                        <button
                                                            type="button"
                                                            onClick={() => navigate(step.link)}
                                                            className="inline-flex items-center gap-1 text-xs font-bold text-primary hover:text-primary-hover hover:underline pt-1"
                                                        >
                                                            <span>{t('onboarding.go_to_step', 'الانتقال للخطوة')}</span>
                                                            <ArrowIcon className="w-3.5 h-3.5" />
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </section>
    );
});

export default OnboardingChecklistWidget;

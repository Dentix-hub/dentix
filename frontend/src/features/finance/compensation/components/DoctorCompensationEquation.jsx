import { useTranslation } from 'react-i18next';
import { Calculator, ArrowRight, Plus, Equal, Minus, Percent } from 'lucide-react';
import Money from '../../components/Money';
import ScopeBadge from '../../components/ScopeBadge';

/**
 * Visual compensation equation explaining doctor entitlement derivation (§15 MASTER_SPEC).
 */
export default function DoctorCompensationEquation({
    collected = 0,
    labCost = 0,
    commissionPercent = 0,
    fixedSalary = 0,
    totalDue = 0,
}) {
    const { t } = useTranslation();

    const commissionBase = Math.max(0, collected - labCost);
    const commissionAmount = Number(((commissionBase * (commissionPercent / 100)) || 0).toFixed(2));

    return (
        <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-text-primary font-bold text-xs">
                    <Calculator className="w-4 h-4 text-primary" />
                    <span>{t('finance.compensation.equation_title', 'معادلة احتساب مستحقات الطبيب للفترة')}</span>
                </div>
                <ScopeBadge scope="period" />
            </div>

            {/* Visual Formula Grid */}
            <div className="grid grid-cols-1 md:grid-cols-7 gap-3 items-center">
                {/* 1. Collected */}
                <div className="p-3 rounded-xl border border-border bg-muted/20 space-y-1 text-center">
                    <span className="text-[10px] font-bold text-text-secondary block">
                        {t('finance.metrics.collected', 'المحصل')}
                    </span>
                    <Money amount={collected} size="sm" colored />
                </div>

                {/* Operator: Minus */}
                <div className="flex justify-center text-text-secondary">
                    <Minus className="w-4 h-4" />
                </div>

                {/* 2. Lab Costs */}
                <div className="p-3 rounded-xl border border-border bg-muted/20 space-y-1 text-center">
                    <span className="text-[10px] font-bold text-text-secondary block">
                        {t('finance.expenses.lab_total', 'تكاليف المعمل')}
                    </span>
                    <Money amount={labCost} size="sm" colored />
                </div>

                {/* Operator: Equals / Multiplied */}
                <div className="flex justify-center text-text-secondary">
                    <Equal className="w-4 h-4" />
                </div>

                {/* 3. Commission Base & Rate */}
                <div className="p-3 rounded-xl border border-primary/20 bg-primary/5 space-y-1 text-center">
                    <span className="text-[10px] font-bold text-primary block">
                        {t('finance.compensation.commission_calc', 'العمولة')} ({commissionPercent}%)
                    </span>
                    <Money amount={commissionAmount} size="sm" />
                </div>

                {/* Operator: Plus */}
                <div className="flex justify-center text-text-secondary">
                    <Plus className="w-4 h-4" />
                </div>

                {/* 4. Fixed Salary */}
                <div className="p-3 rounded-xl border border-border bg-muted/20 space-y-1 text-center">
                    <span className="text-[10px] font-bold text-text-secondary block">
                        {t('finance.compensation.fixed_salary', 'الراتب الثابت')}
                    </span>
                    <Money amount={fixedSalary} size="sm" />
                </div>
            </div>

            {/* Result Total Due */}
            <div className="pt-3 border-t border-border flex items-center justify-between">
                <span className="text-xs font-bold text-text-secondary">
                    {t('finance.compensation.total_entitlement', 'إجمالي المستحقات النهائية للطبيب')}
                </span>
                <div className="flex items-center gap-2">
                    <Money amount={totalDue} size="xl" colored />
                </div>
            </div>
        </div>
    );
}

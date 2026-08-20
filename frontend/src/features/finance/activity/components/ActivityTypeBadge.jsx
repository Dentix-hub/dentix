import { useTranslation } from 'react-i18next';
import {
    DollarSign,
    Receipt,
    FlaskConical,
    Users,
} from 'lucide-react';

/**
 * Accessible, semantic badge for financial event types (§17 MASTER_SPEC, `FIN-ACT-005`).
 */
export default function ActivityTypeBadge({ sourceType, direction }) {
    const { t } = useTranslation();

    const config = {
        payment: {
            label: t('finance.activity.type_payment', 'دفعة مريض'),
            icon: DollarSign,
            className: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
        },
        expense: {
            label: t('finance.activity.type_expense', 'مصروف عيادة'),
            icon: Receipt,
            className: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
        },
        lab: {
            label: t('finance.activity.type_lab', 'معمل أسنان'),
            icon: FlaskConical,
            className: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20',
        },
        salary: {
            label: t('finance.activity.type_salary', 'راتب موظف'),
            icon: Users,
            className: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
        },
    };

    const current = config[sourceType] || {
        label: sourceType,
        icon: DollarSign,
        className: 'bg-muted text-text-secondary border-border',
    };

    const Icon = current.icon;
    const isInflow = direction === 'inflow';

    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${current.className}`}>
            <Icon className="w-3 h-3" />
            <span>{current.label}</span>
            <span className="text-[10px] opacity-75 font-mono">
                ({isInflow ? '+' : '−'})
            </span>
        </span>
    );
}

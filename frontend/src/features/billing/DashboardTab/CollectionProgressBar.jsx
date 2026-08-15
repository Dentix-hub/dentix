import { ReceiptText } from 'lucide-react';
import { Card } from '@/shared/ui';
import { useTranslation } from 'react-i18next';

export default function CollectionProgressBar({ comprehensiveStats, formatCurrency }) {
    const { t } = useTranslation();

    const totalRevenue = comprehensiveStats?.income?.total_revenue || 0;
    const totalCollected = comprehensiveStats?.income?.total_collected || 0;
    const collectionRate = totalRevenue > 0 ? Math.min(100, Math.round((totalCollected / totalRevenue) * 100)) : 0;

    return (
        <Card className="p-5">
            <div className="flex flex-col md:flex-row md:items-center gap-5">
                <div className="flex items-center gap-3 min-w-fit">
                    <div className="p-3 rounded-2xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400">
                        <ReceiptText size={22} />
                    </div>
                    <div>
                        <h3 className="font-black text-text-primary">{t('billing.summary.collection_progress', 'Collection progress')}</h3>
                        <p className="text-sm text-text-secondary">{t('billing.summary.collection_progress_hint', 'Collected cash compared with invoices issued in this period.')}</p>
                    </div>
                </div>
                <div className="flex-1">
                    <div className="flex justify-between gap-4 text-sm font-bold mb-2">
                        <span className="text-text-secondary">{formatCurrency(totalCollected)} / {formatCurrency(totalRevenue)}</span>
                        <span className="text-emerald-600 dark:text-emerald-400">{collectionRate}%</span>
                    </div>
                    <div className="h-3 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-600 transition-all duration-500" style={{ width: `${collectionRate}%` }} />
                    </div>
                </div>
            </div>
        </Card>
    );
}

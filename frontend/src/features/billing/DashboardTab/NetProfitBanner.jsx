import { useTranslation } from 'react-i18next';

export default function NetProfitBanner({ comprehensiveStats, formatCurrency }) {
    const { t } = useTranslation();
    const netProfit = comprehensiveStats?.net_profit || 0;

    return (
        <div className={`p-8 rounded-2xl text-center ${netProfit >= 0 ? 'bg-gradient-to-br from-emerald-500 to-emerald-600' : 'bg-gradient-to-br from-red-500 to-red-600'} text-white shadow-xl`}>
            <p className="text-white/80 font-bold mb-2">{t('billing.summary.net_profit_after')}</p>
            <p className="text-5xl font-bold">{formatCurrency(netProfit)}</p>
            <p className="text-sm text-white/60 mt-3">{t('billing.summary.net_profit_equation')}</p>
        </div>
    );
}

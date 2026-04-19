import { Banknote } from 'lucide-react';
import { Card, EmptyState } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
const PaymentsTab = ({ payments, navigate }) => {
    const { t } = useTranslation();
    return (
        <Card className="overflow-hidden">
            <div className="p-6 border-b border-border flex items-center gap-4 bg-surface">
                <div className="w-1.5 h-8 bg-primary rounded-full"></div>
                <h3 className="font-black text-xl text-text-primary">{t('billing.payments.title')}</h3>
            </div>
            <div className="overflow-x-auto">
                {payments.length > 0 ? (
                    <table className="w-full text-right align-middle text-sm">
                        <thead className="bg-surface-hover text-text-secondary font-bold text-xs uppercase tracking-widest border-b border-border">
                            <tr>
                                <th className="p-4">{t('billing.payments.patient')}</th>
                                <th className="p-4">{t('billing.payments.date')}</th>
                                <th className="p-4">{t('billing.payments.amount')}</th>
                                <th className="p-4">{t('billing.payments.notes')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {payments.map(pay => (
                                <tr key={pay.id} className="hover:bg-surface-hover transition-all group">
                                    <td className="p-4">
                                        <button onClick={() => navigate(`/patients/${pay.patient_id}`)} className="flex flex-col items-start hover:opacity-80 transition-opacity text-right">
                                            <span className="font-black text-primary hover:underline">{pay.patient_name || '---'}</span>
                                            <span className="text-xs text-text-secondary font-bold">#{pay.patient_id}</span>
                                        </button>
                                    </td>
                                    <td className="p-4 text-text-secondary font-bold" dir="ltr">
                                        {new Date(pay.date).toLocaleString('ar-EG', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                    </td>
                                    <td className="p-4">
                                        <span className="font-black text-lg text-success">{pay.amount}</span>
                                    </td>
                                    <td className="p-4 text-text-secondary font-medium">{pay.notes || '---'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                ) : (
                    <EmptyState
                        icon={Banknote}
                        title={t('billing.payments.no_data')}
                        description={t('billing.payments.no_data_desc')}
                    />
                )}
            </div>
        </Card>
    );
};
export default PaymentsTab;

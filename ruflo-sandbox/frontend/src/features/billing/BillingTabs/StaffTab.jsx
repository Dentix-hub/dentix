import { Briefcase } from 'lucide-react';
import { Card, EmptyState, Button } from '@/shared/ui';

import { useTranslation } from 'react-i18next';

const StaffTab = ({ staff, roleLabels, openStaffProfile }) => {
    const { t } = useTranslation();
    return (
        <Card className="overflow-hidden">
            <div className="p-6 border-b border-border flex items-center gap-4 bg-surface">
                <div className="w-1.5 h-8 bg-teal-500 rounded-full"></div>
                <h3 className="font-black text-xl text-text-primary">{t('billing.staff.title')}</h3>
            </div>
            <div className="overflow-x-auto">
                {staff.length > 0 ? (
                    <table className="w-full text-right text-sm">
                        <thead className="bg-surface-hover text-text-secondary font-bold text-xs uppercase border-b border-border">
                            <tr>
                                <th className="p-4">{t('billing.staff.employee')}</th>
                                <th className="p-4">{t('billing.staff.role')}</th>
                                <th className="p-4">{t('billing.staff.fixed_salary')}</th>
                                <th className="p-4">{t('billing.staff.per_appointment')}</th>
                                <th className="p-4 w-10"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {staff.map(s => (
                                <tr key={s.id} className="hover:bg-surface-hover transition-all">
                                    <td className="p-4 font-bold text-text-primary">{s.username}</td>
                                    <td className="p-4">
                                        <span className="px-3 py-1 bg-surface-hover rounded-lg text-xs font-bold text-text-secondary">{roleLabels[s.role] || s.role}</span>
                                    </td>
                                    <td className="p-4 font-bold text-text-primary">{(s.fixed_salary || 0).toLocaleString()}</td>
                                    <td className="p-4 font-bold text-text-primary">{(s.per_appointment_fee || 0).toLocaleString()}</td>
                                    <td className="p-4">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => openStaffProfile(s)}
                                            className="text-text-secondary hover:text-teal-500"
                                        >
                                            <Briefcase size={16} />
                                        </Button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                ) : (
                    <EmptyState
                        icon={Briefcase}
                        title={t('billing.staff.no_employees')}
                        description={t('billing.staff.no_employees_desc')}
                    />
                )}
            </div>
        </Card>
    );
};

export default StaffTab;

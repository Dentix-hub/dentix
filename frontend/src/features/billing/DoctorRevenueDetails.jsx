import { useState, useEffect } from 'react';
import logger from '@/utils/logger';
import { DollarSign, Calendar } from 'lucide-react';
import { Button, Input, SkeletonBox, Badge, Modal, toast } from '@/shared/ui';
import { getDoctorDetails, updateStaffCompensation } from '@/api';
import { useTranslation } from 'react-i18next';

export default function DoctorRevenueDetails({ isOpen = true, doctor, startDate, endDate, onClose, onUpdate }) {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState('treatments');
    const [details, setDetails] = useState(null);
    const [loading, setLoading] = useState(true);

    // Edit Form State
    const [commission, setCommission] = useState(0);
    const [salary, setSalary] = useState(0);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (doctor) {
            setCommission(doctor.commission_percent || 0);
            setSalary(doctor.fixed_salary || 0);
            loadDetails();
        }
    }, [doctor, startDate, endDate]);

    const loadDetails = async () => {
        if (!doctor?.doctor_id) return;
        setLoading(true);
        try {
            const res = await getDoctorDetails(doctor.doctor_id, startDate, endDate);
            setDetails(res.data);
        } catch (err) {
            logger.error(err);
            toast.error(t('billing.alerts.load_fail'));
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await updateStaffCompensation(doctor.doctor_id, commission, salary);
            toast.success(t('billing.alerts.save_success'));
            if (onUpdate) onUpdate(doctor.doctor_id, commission, salary);
            onClose();
        } catch (err) {
            toast.error(t('billing.alerts.save_fail'));
        } finally {
            setSaving(false);
        }
    };

    const calculateTotal = (netRev) => {
        const commValue = netRev * (commission / 100);
        return commValue + salary;
    };

    const netRevenue = details ? (
        (details.treatments?.reduce((sum, tr) => sum + tr.net, 0) || 0) -
        (details.lab_orders?.reduce((sum, l) => sum + l.cost, 0) || 0)
    ) : 0;

    if (!doctor) return null;

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-base">
                        {doctor.doctor_name?.charAt(0)}
                    </div>
                    <div>
                        <span className="font-bold text-slate-800 dark:text-white me-2">{doctor.doctor_name}</span>
                        <Badge variant="outline" className="text-xs font-normal">
                            {new Date(startDate).toLocaleDateString()} - {new Date(endDate).toLocaleDateString()}
                        </Badge>
                    </div>
                </div>
            }
            size="xl"
        >
            <div className="flex flex-col space-y-6">
                {/* Tabs */}
                <div className="flex border-b border-slate-200 dark:border-slate-800 gap-4 shrink-0">
                    <button
                        onClick={() => setActiveTab('treatments')}
                        className={`pb-3 px-4 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'treatments'
                            ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                            : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                    >
                        <Calendar size={18} />
                        {t('billing.doctor_revenue.tabs.treatments')}
                    </button>
                    <button
                        onClick={() => setActiveTab('settings')}
                        className={`pb-3 px-4 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'settings'
                            ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                            : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                    >
                        <DollarSign size={18} />
                        {t('billing.doctor_revenue.tabs.settings')}
                    </button>
                </div>

                {/* Content Area */}
                {loading ? (
                    <div className="space-y-4 py-4">
                        <SkeletonBox className="h-20 w-full rounded-xl" />
                        <SkeletonBox className="h-64 w-full rounded-xl" />
                    </div>
                ) : (
                    <>
                        {/* TAB: TREATMENTS */}
                        {activeTab === 'treatments' && (
                            <div className="space-y-6">
                                {/* Stats Cards */}
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <div className="bg-emerald-50 dark:bg-emerald-900/20 p-4 rounded-xl border border-emerald-100 dark:border-emerald-900/30">
                                        <div className="text-emerald-600 dark:text-emerald-400 font-bold text-xs mb-1">{t('billing.doctor_revenue.stats.total_revenue')}</div>
                                        <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">
                                            {(details?.treatments?.reduce((sum, tr) => sum + tr.net, 0) || 0).toLocaleString()}
                                        </div>
                                    </div>
                                    <div className="bg-rose-50 dark:bg-rose-900/20 p-4 rounded-xl border border-rose-100 dark:border-rose-900/30">
                                        <div className="text-rose-600 dark:text-rose-400 font-bold text-xs mb-1">{t('billing.doctor_revenue.stats.lab_discounts')}</div>
                                        <div className="text-2xl font-bold text-rose-700 dark:text-rose-300">
                                            {(details?.lab_orders?.reduce((sum, l) => sum + l.cost, 0) || 0).toLocaleString()}
                                        </div>
                                    </div>
                                    <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
                                        <div className="text-slate-500 font-bold text-xs mb-1">{t('billing.doctor_revenue.stats.net_profit')}</div>
                                        <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                            {netRevenue.toLocaleString()}
                                        </div>
                                    </div>
                                </div>

                                {/* Table */}
                                <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
                                    <div className="p-4 border-b border-slate-100 dark:border-slate-800 font-bold text-slate-700 dark:text-slate-200">
                                        {t('billing.doctor_revenue.tabs.treatments')}
                                    </div>
                                    <div className="overflow-x-auto max-h-[300px]">
                                        <table className="w-full text-sm text-right">
                                            <thead className="bg-slate-50 dark:bg-slate-900/50 text-slate-500 sticky top-0">
                                                <tr>
                                                    <th className="p-3">{t('billing.doctor_revenue.table.date')}</th>
                                                    <th className="p-3">{t('billing.doctor_revenue.table.patient')}</th>
                                                    <th className="p-3">{t('billing.doctor_revenue.table.procedure')}</th>
                                                    <th className="p-3">{t('billing.doctor_revenue.table.discount')}</th>
                                                    <th className="p-3">{t('billing.doctor_revenue.table.net')}</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                                {details?.treatments?.map(tr => (
                                                    <tr key={tr.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                                                        <td className="p-3 text-slate-500 font-mono">{new Date(tr.date).toLocaleDateString()}</td>
                                                        <td className="p-3 font-bold">{tr.patient_name}</td>
                                                        <td className="p-3">{tr.procedure}</td>
                                                        <td className="p-3 text-red-500">{tr.discount > 0 ? `-${tr.discount}` : '-'}</td>
                                                        <td className="p-3 font-bold text-emerald-600 dark:text-emerald-400">{tr.net.toLocaleString()}</td>
                                                    </tr>
                                                ))}
                                                {!details?.treatments?.length && (
                                                    <tr><td colSpan="5" className="p-8 text-center text-slate-500">{t('common.no_data')}</td></tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                {/* Footer Net Due summary */}
                                <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 flex flex-col md:flex-row justify-between items-center gap-4">
                                    <div className="text-slate-500 text-xs">
                                        <span className="font-bold text-slate-800 dark:text-slate-200">{t('billing.doctor_revenue.footer.equation')}:</span> ({t('billing.doctor_revenue.table.collected')} {(doctor.collected || 0).toLocaleString()} - {t('billing.doctor_revenue.table.lab_cost')} {(doctor.lab_cost || 0).toLocaleString()}) × {commission}% + {t('billing.doctor_revenue.settings.fixed_salary')} {salary}
                                    </div>
                                    <div className="text-right">
                                        <div className="text-xs text-slate-500">{t('billing.doctor_revenue.footer.net_due')}</div>
                                        <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                                            {calculateTotal((doctor.collected || 0) - (doctor.lab_cost || 0)).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* TAB: SETTINGS */}
                        {activeTab === 'settings' && (
                            <div className="max-w-md mx-auto py-4 space-y-6">
                                <div className="bg-indigo-600 p-6 rounded-2xl text-center text-white shadow-lg">
                                    <DollarSign size={40} className="mx-auto mb-2 opacity-80" />
                                    <h3 className="text-xl font-bold">{t('billing.doctor_revenue.settings.title')}</h3>
                                    <p className="opacity-80 text-xs mt-1">{t('billing.doctor_revenue.settings.subtitle')}</p>
                                </div>
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-1">{t('billing.doctor_revenue.settings.commission_rate')}</label>
                                        <div className="relative">
                                            <Input
                                                type="number"
                                                value={commission}
                                                onChange={e => setCommission(parseFloat(e.target.value) || 0)}
                                                className="ps-12 text-lg font-bold h-12"
                                            />
                                            <div className="absolute start-4 top-1/2 -translate-y-1/2 text-slate-500 font-bold">%</div>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-1">{t('billing.doctor_revenue.settings.fixed_salary')}</label>
                                        <Input
                                            type="number"
                                            value={salary}
                                            onChange={e => setSalary(parseFloat(e.target.value) || 0)}
                                            className="text-lg font-bold h-12"
                                        />
                                    </div>
                                    <Button
                                        onClick={handleSave}
                                        className="w-full bg-indigo-600 hover:bg-indigo-700 h-12 text-base shadow-lg shadow-indigo-500/30 mt-4"
                                        disabled={saving}
                                    >
                                        {saving ? t('billing.alerts.saving') : t('billing.doctor_revenue.settings.save_changes')}
                                    </Button>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </Modal>
    );
}

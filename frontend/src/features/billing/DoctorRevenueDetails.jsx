import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, DollarSign, Calendar, Save } from 'lucide-react';
import { Button, Input, Skeleton, Badge } from '@/shared/ui';
import { getDoctorDetails, updateStaffCompensation } from '@/api';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';

export default function DoctorRevenueDetails({ doctor, startDate, endDate, onClose, onUpdate }) {
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
    }, [doctor]);

    useEffect(() => {
        // Prevent background scrolling when open
        document.body.style.overflow = 'hidden';
        return () => { document.body.style.overflow = ''; }
    }, []);

    const loadDetails = async () => {
        setLoading(true);
        try {
            const res = await getDoctorDetails(doctor.doctor_id, startDate, endDate);
            setDetails(res.data);
        } catch (err) {
            console.error(err);
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

    const calculateTotal = (netRevenue) => {
        const commValue = netRevenue * (commission / 100);
        return commValue + salary;
    };

    const netRevenue = details ? (
        (details.treatments?.reduce((sum, t) => sum + t.net, 0) || 0) -
        (details.lab_orders?.reduce((sum, l) => sum + l.cost, 0) || 0)
    ) : 0;

    return createPortal(
        <div className="fixed inset-0 z-[99999] flex items-center justify-center p-0 md:p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
            {/* Main Card Container - Fixed Dimensions */}
            <div className="bg-white dark:bg-slate-900 w-full md:w-[95vw] md:max-w-6xl h-[100vh] md:h-[90vh] md:rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-slate-200 dark:border-slate-800 relative">

                {/* 1. Header (Fixed) */}
                <div className="flex justify-between items-center p-4 border-b border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 z-10 shrink-0">
                    <div>
                        <h2 className="text-xl font-black text-slate-800 dark:text-white flex items-center gap-2">
                            <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-lg">
                                {doctor.doctor_name.charAt(0)}
                            </div>
                            {doctor.doctor_name}
                            <Badge variant="outline" className="text-xs font-normal">
                                {new Date(startDate).toLocaleDateString()} - {new Date(endDate).toLocaleDateString()}
                            </Badge>
                        </h2>
                    </div>
                    <button onClick={onClose} className="p-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-full transition-colors">
                        <X size={24} className="text-slate-500" />
                    </button>
                </div>

                {/* 2. Tabs (Fixed) */}
                <div className="flex border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 px-4 pt-4 gap-4 shrink-0">
                    <button
                        onClick={() => setActiveTab('treatments')}
                        className={`pb-3 px-4 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'treatments'
                            ? 'border-indigo-600 text-indigo-600'
                            : 'border-transparent text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        <Calendar size={18} />
                        {t('billing.doctor_revenue.tabs.treatments')}
                    </button>
                    <button
                        onClick={() => setActiveTab('settings')}
                        className={`pb-3 px-4 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'settings'
                            ? 'border-indigo-600 text-indigo-600'
                            : 'border-transparent text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        <DollarSign size={18} />
                        {t('billing.doctor_revenue.tabs.settings')}
                    </button>
                </div>

                {/* 3. Content Area (Scrollable) */}
                <div className="flex-1 overflow-y-auto bg-slate-50/30 dark:bg-black/20 p-6 relative">
                    {loading ? (
                        <div className="space-y-4">
                            <Skeleton.Box className="h-20 w-full" />
                            <Skeleton.Box className="h-64 w-full" />
                        </div>
                    ) : (
                        <>
                            {/* TAB: TREATMENTS */}
                            {activeTab === 'treatments' && (
                                <div className="space-y-8 pb-24">
                                    {/* Stats Cards */}
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        <div className="bg-emerald-50 dark:bg-emerald-900/20 p-4 rounded-xl border border-emerald-100 dark:border-emerald-900/30">
                                            <div className="text-emerald-600 font-bold text-xs mb-1">{t('billing.doctor_revenue.stats.total_revenue')}</div>
                                            <div className="text-2xl font-black text-emerald-700 dark:text-emerald-400">
                                                {(details?.treatments?.reduce((sum, t) => sum + t.net, 0) || 0).toLocaleString()}
                                            </div>
                                        </div>
                                        <div className="bg-rose-50 dark:bg-rose-900/20 p-4 rounded-xl border border-rose-100 dark:border-rose-900/30">
                                            <div className="text-rose-600 font-bold text-xs mb-1">{t('billing.doctor_revenue.stats.lab_discounts')}</div>
                                            <div className="text-2xl font-black text-rose-700 dark:text-rose-400">
                                                {(details?.lab_orders?.reduce((sum, l) => sum + l.cost, 0) || 0).toLocaleString()}
                                            </div>
                                        </div>
                                        <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
                                            <div className="text-slate-500 font-bold text-xs mb-1">{t('billing.doctor_revenue.stats.net_profit')}</div>
                                            <div className="text-2xl font-black text-slate-800 dark:text-white">
                                                {netRevenue.toLocaleString()}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Tables */}
                                    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
                                        <div className="p-4 border-b border-slate-100 dark:border-slate-800 font-bold text-slate-700 dark:text-slate-200">
                                            {t('billing.doctor_revenue.tabs.treatments')}
                                        </div>
                                        <table className="w-full text-sm text-right">
                                            <thead className="bg-slate-50 dark:bg-slate-900/50 text-slate-500">
                                                <tr>
                                                    <th className="p-3">{t('billing.doctor_revenue.table.date')}</th>
                                                    <th className="p-3">{t('billing.doctor_revenue.table.patient')}</th>
                                                    <th className="p-3">{t('billing.doctor_revenue.table.procedure')}</th>
                                                    <th className="p-3">{t('billing.doctor_revenue.table.discount')}</th>
                                                    <th className="p-3">{t('billing.doctor_revenue.table.net')}</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                                {details?.treatments?.map(t => (
                                                    <tr key={t.id} className="hover:bg-slate-50 transition-colors">
                                                        <td className="p-3 text-slate-500 font-mono">{new Date(t.date).toLocaleDateString()}</td>
                                                        <td className="p-3 font-bold">{t.patient_name}</td>
                                                        <td className="p-3">{t.procedure}</td>
                                                        <td className="p-3 text-red-500">{t.discount > 0 ? `-${t.discount}` : '-'}</td>
                                                        <td className="p-3 font-bold text-emerald-600">{t.net.toLocaleString()}</td>
                                                    </tr>
                                                ))}
                                                {!details?.treatments?.length && (
                                                    <tr><td colSpan="5" className="p-8 text-center text-slate-400">{t('common.no_data')}</td></tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {/* TAB: SETTINGS */}
                            {activeTab === 'settings' && (
                                <div className="max-w-xl mx-auto mt-10">
                                    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg border border-indigo-100 dark:border-indigo-900/50 overflow-hidden">
                                        <div className="bg-indigo-600 p-6 text-center text-white">
                                            <DollarSign size={48} className="mx-auto mb-4 opacity-50" />
                                            <h3 className="text-2xl font-bold">{t('billing.doctor_revenue.settings.title')}</h3>
                                            <p className="opacity-80 text-sm mt-2">{t('billing.doctor_revenue.settings.subtitle')}</p>
                                        </div>

                                        <div className="p-8 space-y-6">
                                            <div>
                                                <label className="block text-sm font-bold text-slate-700 mb-2">{t('billing.doctor_revenue.settings.commission_rate')}</label>
                                                <div className="relative">
                                                    <Input
                                                        type="number"
                                                        value={commission}
                                                        onChange={e => setCommission(parseFloat(e.target.value) || 0)}
                                                        className="pl-12 text-lg font-bold h-12"
                                                    />
                                                    <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-bold">%</div>
                                                </div>
                                            </div>

                                            <div>
                                                <label className="block text-sm font-bold text-slate-700 mb-2">{t('billing.doctor_revenue.settings.fixed_salary')}</label>
                                                <div className="relative">
                                                    <Input
                                                        type="number"
                                                        value={salary}
                                                        onChange={e => setSalary(parseFloat(e.target.value) || 0)}
                                                        className="pl-12 text-lg font-bold h-12"
                                                    />
                                                    <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-bold"></div>
                                                </div>
                                            </div>

                                            <Button
                                                onClick={handleSave}
                                                className="w-full bg-indigo-600 hover:bg-indigo-700 h-12 text-lg shadow-lg shadow-indigo-500/30"
                                                disabled={saving}
                                            >
                                                {saving ? t('billing.alerts.saving') : t('billing.doctor_revenue.settings.save_changes')}
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* 4. Footer (Fixed Total) - Only visible in Treatments tab */}
                {activeTab === 'treatments' && !loading && (
                    <div className="border-t border-slate-200 dark:border-slate-800 p-4 bg-white dark:bg-slate-900 z-10 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] shrink-0">
                        <div className="flex justify-between items-center max-w-4xl mx-auto">
                            <div className="text-slate-500 text-sm">
                                <span className="font-bold text-slate-800 dark:text-slate-200">{t('billing.doctor_revenue.footer.equation')}:</span> ({t('billing.doctor_revenue.table.collected')} {(doctor.collected || 0).toLocaleString()} - {t('billing.doctor_revenue.table.lab_cost')} {(doctor.lab_cost || 0).toLocaleString()}) × {commission}% + {t('billing.doctor_revenue.settings.fixed_salary')} {salary}
                            </div>
                            <div className="flex items-center gap-4">
                                <div className="text-right">
                                    <div className="text-xs text-slate-500">{t('billing.doctor_revenue.footer.net_due')}</div>
                                    <div className="text-3xl font-black text-indigo-600">
                                        {calculateTotal(
                                            (doctor.collected || 0) - (doctor.lab_cost || 0)
                                        ).toLocaleString()}
                                        <span className="text-sm font-normal text-slate-400 mr-1"></span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

            </div>
        </div>,
        document.body
    );
}

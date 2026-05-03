import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Calendar, Calculator } from 'lucide-react';
import { getDoctorRevenue, getDoctorDetails, updateStaffCompensation } from '@/api';
import { Button, Card, SkeletonBox, EmptyState, toast, DateTimePicker } from '@/shared/ui';
import DoctorRevenueDetails from './DoctorRevenueDetails';
import { useTranslation } from 'react-i18next';
export default function DoctorRevenue() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const today = new Date();
    const oneMonthAgo = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate()).toISOString().split('T')[0];
    const currentDay = today.toISOString().split('T')[0];
    const [startDate, setStartDate] = useState(oneMonthAgo);
    const [endDate, setEndDate] = useState(currentDay);
    const [doctors, setDoctors] = useState([]);
    const [loading, setLoading] = useState(false);
    // Modal State
    const [detailsModalOpen, setDetailsModalOpen] = useState(false);
    const [activeModalTab, setActiveModalTab] = useState('treatments');
    const [doctorDetails, setDoctorDetails] = useState(null);
    const [detailsLoading, setDetailsLoading] = useState(false);
    const [selectedDoctorData, setSelectedDoctorData] = useState(null);
    // Editable compensation
    const [editCommission, setEditCommission] = useState(0);
    const [editSalary, setEditSalary] = useState(0);
    const [saving, setSaving] = useState(false);
    useEffect(() => {
        loadData();
    }, [startDate, endDate]);
    const loadData = async () => {
        setLoading(true);
        try {
            const res = await getDoctorRevenue(startDate, endDate);
            setDoctors((res.data.doctors || []).filter(d => d.doctor_name !== 'غير محدد'));
        } catch (err) {
            console.error(err);
            toast.error(t('billing.alerts.doctors_load_fail'));
        } finally {
            setLoading(false);
        }
    };
    const calculateTotal = (netRevenue, commissionPercent, fixedSalary) => {
        const commissionVal = netRevenue * (commissionPercent / 100);
        return commissionVal + fixedSalary;
    };
    const openDetails = async (doc) => {
        setSelectedDoctorData(doc);
        setEditCommission(doc.commission_percent || 0);
        setEditSalary(doc.fixed_salary || 0);
        setActiveModalTab('treatments');
        setDetailsModalOpen(true);
        setDetailsLoading(true);
        try {
            const res = await getDoctorDetails(doc.doctor_id, startDate, endDate);
            setDoctorDetails(res.data);
        } catch (err) {
            console.error(err);
            toast.error(t('billing.alerts.doctor_details_load_fail'));
        } finally {
            setDetailsLoading(false);
        }
    };
    const saveCompensation = async () => {
        if (!selectedDoctorData) return;
        setSaving(true);
        const toastId = toast.loading(t('billing.alerts.saving'));
        try {
            await updateStaffCompensation(selectedDoctorData.doctor_id, editCommission, editSalary);
            setDoctors(prev => prev.map(d =>
                d.doctor_id === selectedDoctorData.doctor_id
                    ? { ...d, commission_percent: editCommission, fixed_salary: editSalary }
                    : d
            ));
            setDetailsModalOpen(false);
            toast.success(t('billing.alerts.save_success'), { id: toastId });
        } catch (err) {
            console.error(err);
            toast.error(t('billing.alerts.save_fail'), { id: toastId });
        } finally {
            setSaving(false);
        }
    };
    return (
        <Card className="overflow-hidden">
            <div className="p-6 border-b border-border flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface">
                <div className="flex items-center gap-4">
                    <div className="w-1.5 h-8 bg-primary rounded-full"></div>
                    <div>
                        <h3 className="font-black text-xl text-text-primary">{t('billing.doctor_revenue.title')}</h3>
                        <p className="text-text-secondary text-sm">{t('billing.doctor_revenue.subtitle')}</p>
                    </div>
                </div>
                <div className="flex items-center gap-3 bg-background p-2 rounded-xl border border-border">
                    <div className="flex items-center gap-2 px-2">
                        <Calendar size={14} className="text-text-secondary" />
                        <span className="text-xs font-bold text-text-secondary">{t('common.date_range')}:</span>
                        <div className="w-32">
                            <DateTimePicker
                                mode="date"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                compact
                            />
                        </div>
                        <span className="text-text-secondary">-</span>
                        <div className="w-32">
                            <DateTimePicker
                                mode="date"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                compact
                            />
                        </div>
                    </div>
                    <Button size="sm" onClick={loadData} disabled={loading}>
                        <Calculator size={14} />
                    </Button>
                </div>
            </div>
            <div className="overflow-x-auto">
                {loading ? (
                    <div className="p-6 space-y-4">
                        {[1, 2, 3].map(i => <SkeletonBox key={i} className="h-16 w-full rounded-xl" />)}
                    </div>
                ) : (
                    <table className="w-full text-right text-sm">
                        <thead className="bg-surface-hover text-text-secondary font-bold text-xs uppercase border-b border-border">
                            <tr>
                                <th className="p-4">{t('billing.doctor_revenue.table.doctor')}</th>
                                <th className="p-4">{t('billing.doctor_revenue.table.gross_total')}</th>
                                <th className="p-4 text-blue-600">{t('billing.doctor_revenue.table.collected')}</th>
                                <th className="p-4 text-orange-500">{t('billing.doctor_revenue.table.patient_discount')}</th>
                                <th className="p-4 text-rose-500">{t('billing.doctor_revenue.table.lab_cost')}</th>
                                <th className="p-4 text-emerald-600">{t('billing.doctor_revenue.table.net_profit')}</th>
                                <th className="p-4 text-teal-600">{t('billing.doctor_revenue.table.doctor_dues')}</th>
                                <th className="p-4 w-10"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {doctors.length > 0 ? (
                                doctors.map(doc => {
                                    const netRevenue = doc.net_revenue || (doc.revenue - (doc.lab_cost || 0));
                                    const labCost = doc.lab_cost || 0;
                                    // Use COLLECTED amount for commission base, not total revenue
                                    const commissionBase = (doc.collected || 0) - labCost;
                                    const totalDue = calculateTotal(commissionBase, doc.commission_percent || 0, doc.fixed_salary || 0);
                                    return (
                                        <tr key={doc.doctor_id} className="hover:bg-surface-hover transition-colors group">
                                            <td className="p-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                                                        {doc.doctor_name.charAt(0).toUpperCase()}
                                                    </div>
                                                    <div>
                                                        <div className="font-bold text-text-primary">{doc.doctor_name}</div>
                                                        <div className="text-xs text-text-secondary">{doc.treatments} {t('common.cases')} • {t('billing.doctor_revenue.table.commission')} {doc.commission_percent || 0}%</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="p-4 font-bold text-text-secondary">{(doc.gross_cost || doc.revenue).toLocaleString()}</td>
                                            <td className="p-4 font-bold text-blue-600">{(doc.collected || 0).toLocaleString()}</td>
                                            <td className="p-4 font-bold text-orange-500">
                                                {(doc.patient_discount || 0) > 0 ? `-${doc.patient_discount.toLocaleString()}` : '-'}
                                            </td>
                                            <td className="p-4 font-bold text-rose-500">
                                                {labCost > 0 ? `-${labCost.toLocaleString()}` : '-'}
                                            </td>
                                            <td className="p-4 font-black text-emerald-600 bg-emerald-50 dark:bg-emerald-900/10 rounded-lg">{netRevenue.toLocaleString()}</td>
                                            <td className="p-4">
                                                <div className="font-black text-lg text-primary">
                                                    {totalDue.toLocaleString()}
                                                </div>
                                            </td>
                                            <td className="p-4">
                                                <Button variant="ghost" size="sm" onClick={() => openDetails(doc)}>
                                                    <User size={16} />
                                                </Button>
                                            </td>
                                        </tr>
                                    );
                                })
                            ) : (
                                <tr>
                                    <td colSpan="8">
                                        <EmptyState
                                            icon={Calculator}
                                            title={t('common.no_data')}
                                            description={t('billing.doctor_revenue.no_revenue')}
                                        />
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                )}
            </div>
            {detailsModalOpen && selectedDoctorData && (
                <DoctorRevenueDetails
                    doctor={selectedDoctorData}
                    startDate={startDate}
                    endDate={endDate}
                    onClose={() => setDetailsModalOpen(false)}
                    onUpdate={(doctorId, commission, salary) => {
                        setDoctors(prev => prev.map(d =>
                            d.doctor_id === doctorId
                                ? { ...d, commission_percent: commission, fixed_salary: salary }
                                : d
                        ));
                    }}
                />
            )}
        </Card>
    );
}


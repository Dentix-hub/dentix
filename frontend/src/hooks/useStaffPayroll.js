import { useState, useCallback, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
    getStaffRevenue,
    updateStaffCompensation,
    getSalariesStatus,
    recordSalaryPayment,
    deleteSalaryPayment,
    updateHireDate
} from '@/api';
import { toast } from '@/shared/ui';
import logger from '@/utils/logger';
import { useTranslation } from 'react-i18next';

export function useStaffPayroll() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();

    const today = new Date();
    const oneMonthAgo = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate()).toISOString().split('T')[0];
    const currentDay = today.toISOString().split('T')[0];

    // Staff List Query
    const { data: staffData, isLoading: staffLoading } = useQuery({
        queryKey: ['staff_list', oneMonthAgo, currentDay],
        queryFn: async () => {
            const res = await getStaffRevenue(oneMonthAgo, currentDay);
            return res.data?.staff || [];
        }
    });

    // Salaries State
    const [salaryMonth, setSalaryMonth] = useState(today.toISOString().slice(0, 7));
    const [salariesData, setSalariesData] = useState([]);
    const [salariesLoading, setSalariesLoading] = useState(false);

    // Modal State
    const [staffModalOpen, setStaffModalOpen] = useState(false);
    const [selectedStaff, setSelectedStaff] = useState(null);
    const [editStaffSalary, setEditStaffSalary] = useState(0);
    const [editStaffPerAppointment, setEditStaffPerAppointment] = useState(0);
    const [savingStaff, setSavingStaff] = useState(false);

    const loadSalaries = useCallback(async () => {
        setSalariesLoading(true);
        try {
            const res = await getSalariesStatus(salaryMonth);
            setSalariesData(res.data?.employees || []);
        } catch (err) {
            logger.error(err);
            toast.error(t('billing.alerts.salaries_load_fail'));
        } finally {
            setSalariesLoading(false);
        }
    }, [salaryMonth, t]);

    useEffect(() => {
        loadSalaries();
    }, [salaryMonth, loadSalaries]);

    const openStaffProfile = useCallback((staffMember) => {
        setSelectedStaff(staffMember);
        setEditStaffSalary(staffMember.fixed_salary || 0);
        setEditStaffPerAppointment(staffMember.per_appointment_fee || 0);
        setStaffModalOpen(true);
    }, []);

    const closeStaffModal = useCallback(() => {
        setStaffModalOpen(false);
        setSelectedStaff(null);
    }, []);

    const saveStaffCompensation = useCallback(async () => {
        if (!selectedStaff) return;
        setSavingStaff(true);
        try {
            await updateStaffCompensation(selectedStaff.id, 0, editStaffSalary, editStaffPerAppointment);
            queryClient.invalidateQueries({ queryKey: ['staff_list'] });
            setStaffModalOpen(false);
            toast.success(t('billing.alerts.save_success'));
        } catch (err) {
            logger.error(err);
            toast.error(t('billing.alerts.save_fail'));
        } finally {
            setSavingStaff(false);
        }
    }, [selectedStaff, editStaffSalary, editStaffPerAppointment, queryClient, t]);

    const handlePaySalary = async (employee, isPartial = false) => {
        const amount = isPartial ? employee.prorated_salary : employee.base_salary;
        if (!confirm(`${t('billing.alerts.pay_confirm_prefix')} ${amount} ${t('billing.alerts.pay_confirm_suffix')} ${employee.username}?`)) return;
        try {
            await recordSalaryPayment(employee.id, salaryMonth, amount, isPartial, isPartial ? employee.days_worked : null, null);
            toast.success(t('billing.alerts.pay_success'));
            loadSalaries();
        } catch (err) {
            logger.error(err);
            toast.error(err.response?.data?.error || t('billing.alerts.pay_fail'));
        }
    };

    const handleDeleteSalaryPayment = async (paymentId) => {
        if (!confirm(t('billing.alerts.cancel_pay_confirm'))) return;
        try {
            await deleteSalaryPayment(paymentId);
            toast.success(t('billing.alerts.cancel_pay_success', 'Payment cancelled'));
            loadSalaries();
        } catch (err) {
            logger.error(err);
            toast.error(t('billing.alerts.cancel_pay_fail', 'Failed to cancel payment'));
        }
    };

    const updateEmployeeHireDate = async (userId, date) => {
        try {
            await updateHireDate(userId, date);
            toast.success(t('billing.alerts.hire_date_success'));
            loadSalaries();
        } catch (err) {
            logger.error(err);
            toast.error(t('billing.alerts.hire_date_fail'));
        }
    };

    return {
        staff: staffData || [],
        staffLoading,
        salariesData,
        salariesLoading,
        salaryMonth,
        setSalaryMonth,
        loadSalaries,
        staffModalOpen,
        openStaffProfile,
        closeStaffModal,
        selectedStaff,
        editStaffSalary,
        setEditStaffSalary,
        editStaffPerAppointment,
        setEditStaffPerAppointment,
        saveStaffCompensation,
        savingStaff,
        handlePaySalary,
        handleDeleteSalaryPayment,
        updateEmployeeHireDate
    };
}

export default useStaffPayroll;

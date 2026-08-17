import { useState, useMemo } from 'react';
import { TabGroup } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
import useStaffPayroll from '@/hooks/useStaffPayroll';
import StaffDirectory from './StaffDirectory';
import SalaryPayroll from './SalaryPayroll';
import StaffCompensationModal from './StaffCompensationModal';

export default function StaffSalariesTab() {
    const { t } = useTranslation();
    const [activeSubTab, setActiveSubTab] = useState('directory');

    const {
        staff,
        staffLoading,
        salariesData,
        salariesLoading,
        salaryMonth,
        setSalaryMonth,
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
    } = useStaffPayroll();

    const roleLabels = useMemo(() => ({
        assistant: t('billing.roles.assistant'),
        receptionist: t('billing.roles.receptionist'),
        accountant: t('billing.roles.accountant'),
        nurse: t('billing.roles.nurse')
    }), [t]);

    const subTabs = useMemo(() => [
        { id: 'directory', label: t('billing.tabs.staff', 'Staff Directory') },
        { id: 'payroll', label: t('billing.subtabs.salaries', 'Salary Payroll') }
    ], [t]);

    return (
        <div className="space-y-6">
            <TabGroup
                variant="underline"
                tabs={subTabs}
                activeTab={activeSubTab}
                onChange={setActiveSubTab}
            />

            {activeSubTab === 'directory' ? (
                <StaffDirectory
                    staff={staff}
                    staffLoading={staffLoading}
                    roleLabels={roleLabels}
                    openStaffProfile={openStaffProfile}
                />
            ) : (
                <SalaryPayroll
                    salaryMonth={salaryMonth}
                    setSalaryMonth={setSalaryMonth}
                    salariesData={salariesData}
                    salariesLoading={salariesLoading}
                    updateEmployeeHireDate={updateEmployeeHireDate}
                    roleLabels={roleLabels}
                    handlePaySalary={handlePaySalary}
                    handleDeleteSalaryPayment={handleDeleteSalaryPayment}
                />
            )}

            <StaffCompensationModal
                isOpen={staffModalOpen}
                onClose={closeStaffModal}
                selectedStaff={selectedStaff}
                roleLabels={roleLabels}
                editStaffSalary={editStaffSalary}
                setEditStaffSalary={setEditStaffSalary}
                editStaffPerAppointment={editStaffPerAppointment}
                setEditStaffPerAppointment={setEditStaffPerAppointment}
                saveStaffCompensation={saveStaffCompensation}
                savingStaff={savingStaff}
            />
        </div>
    );
}

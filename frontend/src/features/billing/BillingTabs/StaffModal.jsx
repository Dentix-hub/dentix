import React from 'react';
import { Briefcase, Save } from 'lucide-react';
import { Button, Input, Modal } from '@/shared/ui';

import { useTranslation } from 'react-i18next';

const StaffModal = ({ isOpen, onClose, selectedStaff, roleLabels, editStaffSalary, setEditStaffSalary, editStaffPerAppointment, setEditStaffPerAppointment, saveStaffCompensation, savingStaff }) => {
    const { t } = useTranslation();
    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`${t('billing.staff.modal_title')} ${selectedStaff?.username}`}
            size="md"
        >
            <div className="space-y-4">
                <div className="p-4 bg-purple-50 dark:bg-purple-500/10 rounded-xl border border-purple-100 dark:border-purple-500/20">
                    <p className="text-sm text-purple-600 dark:text-purple-400 mb-2 flex items-center gap-2">
                        <Briefcase size={16} />
                        {t('billing.staff.role')}: <span className="font-bold">{roleLabels[selectedStaff?.role] || selectedStaff?.role}</span>
                    </p>
                </div>

                <Input
                    label={`${t('billing.staff.fixed_salary')}`}
                    type="number"
                    value={editStaffSalary}
                    onChange={e => setEditStaffSalary(parseFloat(e.target.value) || 0)}
                />

                <div>
                    <Input
                        label={`${t('billing.staff.modal_per_appointment_input')}`}
                        type="number"
                        value={editStaffPerAppointment}
                        onChange={e => setEditStaffPerAppointment(parseFloat(e.target.value) || 0)}
                    />
                    <p className="text-xs text-text-secondary mt-1">{t('billing.staff.per_appointment_desc')}</p>
                </div>

                <div className="flex justify-end gap-3 mt-6">
                    <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
                    <Button onClick={saveStaffCompensation} disabled={savingStaff}>
                        <Save size={16} className="mr-2" />
                        {savingStaff ? t('common.loading') : t('common.save')}
                    </Button>
                </div>
            </div>
        </Modal>
    );
};

export default StaffModal;

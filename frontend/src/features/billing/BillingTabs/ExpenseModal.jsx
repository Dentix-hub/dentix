import React from 'react';
import { Button, Input, Modal } from '@/shared/ui';

import { useTranslation } from 'react-i18next';

const ExpenseModal = ({ isOpen, onClose, newExpense, setNewExpense, handleCreateExpense }) => {
    const { t } = useTranslation();
    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={t('billing.expenses.modal_title')}
            size="md"
        >
            <div className="space-y-4">
                <Input
                    label={t('billing.expenses.item')}
                    value={newExpense.item_name}
                    onChange={e => setNewExpense({ ...newExpense, item_name: e.target.value })}
                    placeholder={t('billing.expenses.placeholder')}
                />

                <div className="grid grid-cols-2 gap-4">
                    <Input
                        label={t('billing.expenses.cost')}
                        type="number"
                        value={newExpense.cost}
                        onChange={e => setNewExpense({ ...newExpense, cost: e.target.value })}
                    />

                    <div>
                        <label className="block text-sm font-bold text-text-primary mb-1">{t('billing.expenses.category')}</label>
                        <select
                            value={newExpense.category}
                            onChange={e => setNewExpense({ ...newExpense, category: e.target.value })}
                            className="w-full p-3 bg-surface border border-border rounded-xl outline-none focus:border-primary transition-colors text-text-primary"
                        >
                            <option value="General">{t('billing.expenses.categories.general')}</option>
                            <option value="Materials">{t('billing.expenses.categories.materials')}</option>
                            <option value="Salaries">{t('billing.expenses.categories.salaries')}</option>
                            <option value="Rent">{t('billing.expenses.categories.rent')}</option>
                            <option value="Utilities">{t('billing.expenses.categories.utilities')}</option>
                            <option value="Maintenance">{t('billing.expenses.categories.maintenance')}</option>
                        </select>
                    </div>
                </div>

                <Input
                    label={t('billing.expenses.date')}
                    type="date"
                    value={newExpense.date}
                    onChange={e => setNewExpense({ ...newExpense, date: e.target.value })}
                />

                <div className="flex justify-end gap-3 mt-6">
                    <Button variant="ghost" onClick={onClose}>{t('common.cancel')}</Button>
                    <Button onClick={handleCreateExpense}>{t('common.save')}</Button>
                </div>
            </div>
        </Modal>
    );
};

export default ExpenseModal;

import { useState } from 'react';
import Button from '../Button';
import Input from '../Input';
import Modal from '../Modal';
import DateTimePicker from '../DateTimePicker';

export default function PaymentModal({ isOpen, onClose, onAdd }) {
    const [payment, setPayment] = useState({
        amount: '',
        notes: '',
        date: new Date().toISOString().split('T')[0],
    });

    const handleSave = () => {
        // Preserve the existing backend contract: date-only UI becomes local midnight.
        const submissionData = {
            ...payment,
            date: payment.date ? `${payment.date}T00:00:00` : new Date().toISOString(),
        };
        onAdd(submissionData);
        setPayment({
            amount: '',
            notes: '',
            date: new Date().toISOString().split('T')[0],
        });
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="إضافة دفعة مالية"
            maxWidth="max-w-md"
        >
            <div className="space-y-4">
                <Input
                    label="المبلغ المدفوع"
                    value={payment.amount}
                    onChange={(event) => setPayment({ ...payment, amount: event.target.value })}
                    placeholder="المبلغ المدفوع"
                    type="number"
                    inputMode="decimal"
                    className="text-lg font-bold text-emerald-600"
                />

                <DateTimePicker
                    value={payment.date}
                    onChange={(event) => setPayment({ ...payment, date: event.target.value })}
                    mode="date"
                />

                <div className="space-y-1.5">
                    <label htmlFor="payment-notes" className="block text-type-label text-text-secondary">
                        ملاحظات
                    </label>
                    <textarea
                        id="payment-notes"
                        value={payment.notes}
                        onChange={(event) => setPayment({ ...payment, notes: event.target.value })}
                        placeholder="ملاحظات"
                        className="min-h-24 w-full rounded-control border border-border bg-input px-3 py-2.5 text-text-primary outline-none transition-colors duration-fast placeholder:text-text-muted focus:border-focus focus:ring-1 focus:ring-focus"
                    />
                </div>

                <div className="flex justify-end gap-3 pt-1">
                    <Button variant="ghost" onClick={onClose}>إلغاء</Button>
                    <Button onClick={handleSave}>إضافة</Button>
                </div>
            </div>
        </Modal>
    );
}

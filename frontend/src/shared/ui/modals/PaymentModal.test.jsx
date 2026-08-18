import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import PaymentModal from './PaymentModal';

vi.mock('../DateTimePicker', () => ({
    default: ({ value, onChange }) => (
        <input
            aria-label="Payment date"
            value={value}
            onChange={onChange}
        />
    ),
}));

describe('PaymentModal design-system migration', () => {
    it('preserves the existing payment payload contract', () => {
        const onAdd = vi.fn();
        render(<PaymentModal isOpen onClose={() => {}} onAdd={onAdd} />);

        fireEvent.change(screen.getByRole('spinbutton', { name: 'المبلغ المدفوع' }), {
            target: { value: '450' },
        });
        fireEvent.change(screen.getByLabelText('Payment date'), {
            target: { value: '2026-08-18' },
        });
        fireEvent.change(screen.getByRole('textbox', { name: 'ملاحظات' }), {
            target: { value: 'دفعة اختبار' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'إضافة' }));

        expect(onAdd).toHaveBeenCalledWith({
            amount: '450',
            notes: 'دفعة اختبار',
            date: '2026-08-18T00:00:00',
        });
    });

    it('uses the canonical Dentix dialog surface', () => {
        render(<PaymentModal isOpen onClose={() => {}} onAdd={() => {}} />);
        expect(screen.getByRole('dialog', { name: 'إضافة دفعة مالية' })).toHaveAttribute('data-dentix-overlay', 'dialog');
    });
});

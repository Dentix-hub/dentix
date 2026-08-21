import { fireEvent, render, screen, within } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import PaymentModal from './PaymentModal';

function ControlledPaymentModal({ onAdd }) {
    const [isOpen, setIsOpen] = useState(true);
    return (
        <PaymentModal
            isOpen={isOpen}
            onClose={() => setIsOpen(false)}
            onAdd={onAdd}
        />
    );
}

describe('PaymentModal date selection', () => {
    it('keeps the payment dialog open and submits a non-today date', async () => {
        const onAdd = vi.fn();
        const initialValue = new Date().toISOString().split('T')[0];
        const [year, month] = initialValue.split('-');
        render(<ControlledPaymentModal onAdd={onAdd} />);

        fireEvent.click(screen.getByRole('button', { name: initialValue }));

        const calendarDialog = await screen.findByRole('dialog', { name: 'Date' });
        const currentMonthDay = Array.from(within(calendarDialog).getAllByRole('button')).find(button => (
            button.getAttribute('aria-pressed') === 'false'
            && button.className.includes('text-text-primary')
            && /^\d{1,2}$/.test(button.textContent.trim())
        ));
        const selectedDate = `${year}-${month}-${currentMonthDay.textContent.trim().padStart(2, '0')}`;

        fireEvent.pointerDown(currentMonthDay);
        fireEvent.click(currentMonthDay);

        expect(screen.getByRole('dialog', { name: 'إضافة دفعة مالية' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: selectedDate })).toBeInTheDocument();

        fireEvent.change(screen.getByRole('spinbutton', { name: 'المبلغ المدفوع' }), {
            target: { value: '450' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'إضافة' }));

        expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({
            amount: '450',
            date: `${selectedDate}T00:00:00`,
        }));
    });
});

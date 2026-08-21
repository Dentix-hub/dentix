import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DateTimePicker from './DateTimePicker';

function findCalendarPanel(dialog) {
    return [dialog, ...Array.from(dialog.querySelectorAll('div'))].find((element) => {
        const classes = typeof element.className === 'string' ? element.className : '';
        return classes.includes('bg-surface-elevated') && classes.includes('overflow-hidden');
    });
}

describe('DateTimePicker popup surface regression', () => {
    it('renders the popup content on the canonical explicit opaque surface', async () => {
        render(
            <DateTimePicker
                value="2026-08-18"
                onChange={vi.fn()}
                label="Appointment date"
                mode="date"
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: /2026-08-18/i }));

        const dialog = await screen.findByRole('dialog');
        let panel;
        await waitFor(() => {
            panel = findCalendarPanel(dialog);
            expect(panel).toBeTruthy();
        });

        expect(panel.className).toContain('bg-surface-elevated');
        expect(panel.className).not.toContain('bg-surface ');
        expect(panel.className).not.toMatch(/bg-white\/\d+/);
        expect(panel.className).not.toMatch(/bg-slate-900\/\d+/);
    });

    it('selects a different day and time before confirming the datetime value', async () => {
        const onChange = vi.fn();
        render(
            <DateTimePicker
                value="2026-08-18T09:00:00"
                onChange={onChange}
                label="Appointment time"
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: /2026-08-18 09:00 AM/i }));
        const dialog = await screen.findByRole('dialog', { name: 'Appointment time' });
        const day = within(dialog).getByRole('button', { name: '2026-08-20' });
        const hour = dialog.querySelector('[data-picker-option="hour"][aria-label$=" 3"]');
        const minute = dialog.querySelector('[data-picker-option="minute"][aria-label$=" 30"]');
        const period = within(dialog).getByRole('button', { name: 'PM' });

        fireEvent.click(day);
        fireEvent.click(hour);
        fireEvent.click(minute);
        fireEvent.click(period);

        expect(day).toHaveAttribute('aria-pressed', 'true');
        expect(hour).toHaveAttribute('aria-pressed', 'true');
        expect(minute).toHaveAttribute('aria-pressed', 'true');
        expect(period).toHaveAttribute('aria-pressed', 'true');

        fireEvent.click(within(dialog).getByRole('button', { name: /Confirm/i }));

        expect(onChange).toHaveBeenCalledWith({
            target: { value: new Date(2026, 7, 20, 15, 30, 0, 0).toISOString() },
        });
        expect(screen.queryByRole('dialog', { name: 'Appointment time' })).not.toBeInTheDocument();
    });

    it('selects a different month and emits the canonical month value', async () => {
        const onChange = vi.fn();
        render(
            <DateTimePicker
                value="2026-08"
                onChange={onChange}
                label="Expiry month"
                mode="month"
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: /August 2026/i }));
        const dialog = await screen.findByRole('dialog', { name: 'Expiry month' });
        fireEvent.click(within(dialog).getByRole('button', { name: '2026-10' }));

        expect(onChange).toHaveBeenCalledWith({ target: { value: '2026-10' } });
        expect(screen.queryByRole('dialog', { name: 'Expiry month' })).not.toBeInTheDocument();
    });
});

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DateTimePicker from './DateTimePicker';

function findCalendarPanel(dialog) {
    return Array.from(dialog.querySelectorAll('div')).find((element) => {
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
});

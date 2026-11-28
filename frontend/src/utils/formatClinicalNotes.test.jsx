import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
    extractLabLinkOrderId,
    isInternalLabLinkNote,
    formatTreatmentNotesForDisplay,
} from './formatClinicalNotes';
import PatientTimeline from '@/features/patients/PatientTabs/PatientTimeline';

describe('formatClinicalNotes & PatientTimeline masking (Bug #16)', () => {
    it('extracts and formats exact singleton Link:LabOrder:<id> tokens cleanly without losing user notes', () => {
        expect(extractLabLinkOrderId('Link:LabOrder:17')).toBe('17');
        expect(isInternalLabLinkNote('Link:LabOrder:17')).toBe(true);
        expect(isInternalLabLinkNote('Regular clinical note')).toBe(false);

        const t = (key, def, opts) => (key.includes('linked_lab_order_badge') ? `مرتبط بطلب معمل #${opts?.id}` : def);
        const formatted = formatTreatmentNotesForDisplay('Link:LabOrder:17', t);
        expect(formatted).toBe('مرتبط بطلب معمل #17');
        expect(formatted).not.toContain('Link:LabOrder:');

        expect(formatTreatmentNotesForDisplay('Patient note Link:LabOrder:17', t)).toBe('Patient note');
        expect(formatTreatmentNotesForDisplay('Plain observation', t)).toBe('Plain observation');
    });

    it('renders PatientTimeline without exposing raw Link:LabOrder tokens', () => {
        const t = (key, def, opts) => (key.includes('linked_lab_order_badge') ? `مرتبط بطلب معمل #${opts?.id}` : def);
        render(
            <PatientTimeline
                t={t}
                history={[
                    {
                        id: 1,
                        date: '2026-11-28T10:00:00Z',
                        procedure: 'عمل معمل: تاج زيركون',
                        notes: 'Link:LabOrder:17',
                    },
                ]}
                payments={[]}
            />,
        );

        expect(screen.getByText('عمل معمل: تاج زيركون')).toBeInTheDocument();
        expect(screen.getByText('مرتبط بطلب معمل #17')).toBeInTheDocument();
        expect(screen.queryByText(/Link:LabOrder:/i)).not.toBeInTheDocument();
    });
});

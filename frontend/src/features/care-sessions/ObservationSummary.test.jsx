import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import ObservationSummary from './ObservationSummary';

const measurements = [
    {
        id: 1,
        work_item_id: 10,
        tooth_key: '46',
        canal_id: 'MB',
        root_id: 'mesial',
        observation_code: 'working_length',
        structured_value: { length_mm: 20, maf: '#25 / .04', reference_point: 'MB cusp' },
        notes: 'Curved canal',
    },
    {
        id: 2,
        work_item_id: 10,
        tooth_key: '46',
        canal_id: 'ML',
        root_id: 'mesial',
        observation_code: 'working_length',
        structured_value: { length_mm: 21, maf: '#30', taper: 0.06, reference_point: 'ML cusp' },
    },
];

describe('Readable canal groups', () => {
    it('groups a tooth into one table with length, file size, taper, reference, root and notes', () => {
        const historicalCopy = structuredClone(measurements);
        render(<ObservationSummary observations={measurements} />);
        expect(screen.getAllByTestId('canal-measurement-group')).toHaveLength(1);
        const table = screen.getByRole('table', { name: 'Canal measurements' });
        expect(within(table).getByRole('row', { name: /MB 20 mm #25 0.04/ })).toBeInTheDocument();
        expect(within(table).getByRole('row', { name: /ML 21 mm #30 0.06/ })).toBeInTheDocument();
        expect(table).toHaveTextContent('Reference Point: MB cusp');
        expect(table).toHaveTextContent('mesial');
        expect(table).toHaveTextContent('Curved canal');
        expect(measurements).toEqual(historicalCopy);
    });

    it('keeps independent procedures and teeth separate and respects amendment controls', () => {
        const amended = { ...measurements[0], id: 4, is_superseded: true, amendment_reason: 'Correction' };
        const onAmend = vi.fn();
        render(
            <ObservationSummary
                observations={[...measurements, { ...measurements[1], id: 3, work_item_id: 20 }, amended]}
                onAmend={onAmend}
            />,
        );
        expect(screen.getAllByTestId('canal-measurement-group')).toHaveLength(2);
        expect(within(screen.getByTestId('observation-4')).queryByRole('button')).not.toBeInTheDocument();
        fireEvent.click(
            within(screen.getByTestId('observation-2')).getByRole('button', { name: 'Amend observation' }),
        );
        expect(onAmend).toHaveBeenCalledWith(measurements[1]);
    });

    it('preserves general observations and exposes no editing action in read-only use', () => {
        render(
            <ObservationSummary
                observations={[
                    ...measurements,
                    {
                        id: 5,
                        observation_code: 'shade',
                        structured_value: { value: 'A2' },
                        notes: 'Confirmed shade',
                    },
                ]}
            />,
        );
        expect(screen.getByTestId('observation-5')).toHaveTextContent('A2');
        expect(screen.getByTestId('observation-5')).toHaveTextContent('Confirmed shade');
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
});

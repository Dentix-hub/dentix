import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import WorkingLengthEntryTable from './WorkingLengthEntryTable';

const canals = [
    { canalId: 'MB', rootId: 'mesial' },
    { canalId: 'ML', rootId: 'mesial' },
];

describe('Grouped canal documentation', () => {
    it('saves all entered canals with one action and keeps their full independent measurements', async () => {
        const onSave = vi.fn().mockResolvedValue(true);
        render(<WorkingLengthEntryTable toothKey="46" selectedCanals={canals} onSaveMeasurement={onSave} />);
        fireEvent.change(screen.getByTestId('input-length-MB'), { target: { value: '20' } });
        fireEvent.change(screen.getByTestId('input-taper-MB'), { target: { value: '0.04' } });
        fireEvent.change(screen.getByTestId('input-length-ML'), { target: { value: '21' } });
        fireEvent.change(screen.getByTestId('select-maf-ML'), { target: { value: '#30' } });
        fireEvent.change(screen.getByTestId('input-taper-ML'), { target: { value: '0.06' } });
        fireEvent.click(screen.getByRole('button', { name: 'Save canal measurements' }));
        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(2));
        expect(onSave.mock.calls.map(([measurement]) => measurement)).toEqual([
            expect.objectContaining({
                canal_id: 'MB',
                root_id: 'mesial',
                tooth_key: '46',
                length_mm: 20,
                maf: '#25',
                taper: 0.04,
            }),
            expect.objectContaining({
                canal_id: 'ML',
                root_id: 'mesial',
                tooth_key: '46',
                length_mm: 21,
                maf: '#30',
                taper: 0.06,
            }),
        ]);
    });

    it('validates every entered row before saving and leaves untouched canals optional', async () => {
        const onSave = vi.fn().mockResolvedValue(true);
        render(<WorkingLengthEntryTable toothKey="46" selectedCanals={canals} onSaveMeasurement={onSave} />);
        fireEvent.change(screen.getByTestId('input-length-MB'), { target: { value: '20' } });
        fireEvent.change(screen.getByTestId('input-taper-ML'), { target: { value: '-0.04' } });
        fireEvent.click(screen.getByTestId('save-canal-measurements'));
        expect(onSave).not.toHaveBeenCalled();
        expect(screen.getByRole('alert')).toHaveTextContent('ML');
        fireEvent.change(screen.getByTestId('input-length-ML'), { target: { value: '21' } });
        fireEvent.change(screen.getByTestId('input-taper-ML'), { target: { value: '0.06' } });
        fireEvent.click(screen.getByTestId('save-canal-measurements'));
        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(2));
    });

    it('retains failed entries and retries only canals not already saved', async () => {
        const onSave = vi
            .fn()
            .mockResolvedValueOnce(true)
            .mockResolvedValueOnce(false)
            .mockResolvedValue(true);
        render(<WorkingLengthEntryTable toothKey="46" selectedCanals={canals} onSaveMeasurement={onSave} />);
        for (const canal of ['MB', 'ML'])
            fireEvent.change(screen.getByTestId(`input-length-${canal}`), {
                target: { value: canal === 'MB' ? '20' : '21' },
            });
        fireEvent.click(screen.getByTestId('save-canal-measurements'));
        await screen.findByRole('alert');
        expect(screen.getByTestId('input-length-ML')).toHaveValue(21);
        fireEvent.click(screen.getByTestId('save-canal-measurements'));
        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(3));
        expect(onSave.mock.calls.map(([measurement]) => measurement.canal_id)).toEqual(['MB', 'ML', 'ML']);
        await waitFor(() => expect(screen.getByTestId('save-canal-measurements')).toBeDisabled());
    });

    it('does not save an untouched selected canal and prevents duplicate concurrent saves', async () => {
        let resolve;
        const onSave = vi.fn(
            () =>
                new Promise((done) => {
                    resolve = done;
                }),
        );
        render(<WorkingLengthEntryTable toothKey="46" selectedCanals={canals} onSaveMeasurement={onSave} />);
        fireEvent.change(screen.getByTestId('input-length-MB'), { target: { value: '20' } });
        fireEvent.click(screen.getByTestId('save-canal-measurements'));
        fireEvent.click(screen.getByTestId('save-canal-measurements'));
        expect(onSave).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('input-length-MB')).toBeDisabled();
        resolve(true);
        await waitFor(() => expect(screen.getByTestId('input-length-MB')).toBeEnabled());
        expect(onSave.mock.calls[0][0].canal_id).toBe('MB');
    });
});

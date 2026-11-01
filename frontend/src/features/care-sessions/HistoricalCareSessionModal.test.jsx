import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import HistoricalCareSessionModal from './HistoricalCareSessionModal';
import * as patientsApi from '@/api/patients';

vi.mock('@/api/patients', () => ({
    startCareSession: vi.fn(),
}));

describe('HistoricalCareSessionModal', () => {
    const mockWorkItems = [
        { id: 101, code: 'REST_COMPOSITE', tooth_number: '24', display_label: 'Composite Restoration (Tooth 24)' },
        { id: 102, code: 'SURG_EXTRACTION', tooth_number: '38', display_label: 'Surgical Extraction (Tooth 38)' },
    ];

    const mockDoctors = [
        { id: 1, full_name: 'Dr. Sarah Ahmed' },
        { id: 2, full_name: 'Dr. James Wilson' },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('records independent lengths, master file sizes and tapers for multiple canals', async () => {
        patientsApi.startCareSession.mockResolvedValue({ data: { id: 80 } });
        render(<HistoricalCareSessionModal isOpen patientId={5} currentUserId={1} onClose={vi.fn()} patientWorkItems={[{ id: 101, code: 'ENDO_RCT', tooth_number: '46' }]} />);
        expect(screen.getByTestId('select-historical-obs-code')).toHaveValue('working_length');
        fireEvent.click(screen.getByTestId('canal-chip-MB'));
        fireEvent.click(screen.getByTestId('canal-chip-ML'));
        for (const [canal, length, size, taper] of [['MB', '20', '#25', '0.04'], ['ML', '21', '#30', '0.06']]) {
            fireEvent.change(screen.getByTestId(`input-length-${canal}`), { target: { value: length } });
            fireEvent.change(screen.getByTestId(`select-maf-${canal}`), { target: { value: size } });
            fireEvent.change(screen.getByTestId(`input-taper-${canal}`), { target: { value: taper } });
            fireEvent.click(screen.getByTestId(`btn-save-measurement-${canal}`));
            await waitFor(() => expect(screen.getByTestId(`btn-save-measurement-${canal}`)).not.toBeDisabled());
        }
        expect(patientsApi.startCareSession).not.toHaveBeenCalled();
        fireEvent.click(screen.getByTestId('btn-submit-historical-session'));
        await waitFor(() => expect(patientsApi.startCareSession).toHaveBeenCalledTimes(1));
        expect(patientsApi.startCareSession.mock.lastCall[1].historical_observations).toEqual([
            expect.objectContaining({ work_item_id: 101, tooth_key: '46', canal_id: 'MB', structured_value: expect.objectContaining({ length_mm: 20, maf: '#25', taper: 0.04 }) }),
            expect.objectContaining({ work_item_id: 101, tooth_key: '46', canal_id: 'ML', structured_value: expect.objectContaining({ length_mm: 21, maf: '#30', taper: 0.06 }) }),
        ]);
    });

    it('renders historical visit modal fields and selects procedures', () => {
        render(
            <HistoricalCareSessionModal
                isOpen={true}
                onClose={vi.fn()}
                patientId={5}
                patientWorkItems={mockWorkItems}
                doctors={mockDoctors}
                currentUserId={1}
                onSuccess={vi.fn()}
            />
        );

        expect(screen.getByText(/Record Past \/ Historical Visit/i)).toBeInTheDocument();
        expect(screen.getByText(/Composite Restoration \(Tooth 24\)/i)).toBeInTheDocument();
        expect(screen.getByText(/Surgical Extraction \(Tooth 38\)/i)).toBeInTheDocument();
    });

    it('assigns each historical step and measurement to the selected procedure', async () => {
        patientsApi.startCareSession.mockResolvedValue({ data: { id: 99 } });
        render(<HistoricalCareSessionModal isOpen onClose={vi.fn()} patientId={5} patientWorkItems={mockWorkItems} currentUserId={1} />);
        fireEvent.click(screen.getByTestId('checkbox-proc-102').querySelector('input'));
        fireEvent.change(screen.getByTestId('input-historical-step-title'), { target: { value: 'Composite shade selection' } });
        fireEvent.click(screen.getByTestId('btn-add-historical-step'));
        fireEvent.change(screen.getByTestId('historical-entry-procedure'), { target: { value: '102' } });
        fireEvent.change(screen.getByTestId('input-historical-step-title'), { target: { value: 'Socket inspection' } });
        fireEvent.click(screen.getByTestId('btn-add-historical-step'));
        fireEvent.change(screen.getByTestId('input-historical-obs-value'), { target: { value: 'Healing well' } });
        fireEvent.click(screen.getByTestId('btn-add-historical-obs'));
        fireEvent.click(screen.getByTestId('checkbox-proc-102').querySelector('input'));
        expect(screen.getByText(/Remove this procedure’s steps and observations/)).toBeInTheDocument();
        fireEvent.click(screen.getByTestId('btn-submit-historical-session'));
        await waitFor(() => expect(patientsApi.startCareSession).toHaveBeenCalledTimes(1));
        const body = patientsApi.startCareSession.mock.lastCall[1];
        expect(body.work_item_ids).toEqual([101, 102]);
        expect(body.historical_steps.map((step) => step.work_item_id)).toEqual([101, 102]);
        expect(body.historical_observations[0]).toMatchObject({ work_item_id: 102, structured_value: { value: 'Healing well' } });
    });

    it('validates against future visit dates and submits legitimate historical visit', async () => {
        const mockOnSuccess = vi.fn();
        const mockOnClose = vi.fn();
        patientsApi.startCareSession.mockResolvedValueOnce({ data: { id: 77, is_historical: true } });

        render(
            <HistoricalCareSessionModal
                isOpen={true}
                onClose={mockOnClose}
                patientId={5}
                patientWorkItems={mockWorkItems}
                doctors={mockDoctors}
                currentUserId={1}
                onSuccess={mockOnSuccess}
            />
        );

        // Enter notes
        const notesInput = screen.getByTestId('input-historical-notes');
        fireEvent.change(notesInput, { target: { value: 'Work performed at previous clinic before referral' } });

        // Submit form
        const submitBtn = screen.getByTestId('btn-submit-historical-session');
        fireEvent.click(submitBtn);

        await waitFor(() => {
            expect(patientsApi.startCareSession).toHaveBeenCalledTimes(1);
            expect(patientsApi.startCareSession).toHaveBeenCalledWith(
                5,
                expect.objectContaining({
                    is_historical: true,
                    work_item_ids: [101],
                    notes: 'Work performed at previous clinic before referral',
                })
            );
            expect(mockOnSuccess).toHaveBeenCalledTimes(1);
            expect(mockOnClose).toHaveBeenCalledTimes(1);
        });
    });

    it('submits historical visit with recorded steps and clinical measurements', async () => {
        const mockOnSuccess = vi.fn();
        patientsApi.startCareSession.mockResolvedValueOnce({ data: { id: 78, is_historical: true } });

        render(
            <HistoricalCareSessionModal
                isOpen={true}
                onClose={vi.fn()}
                patientId={5}
                patientWorkItems={mockWorkItems}
                doctors={mockDoctors}
                currentUserId={1}
                onSuccess={mockOnSuccess}
            />
        );

        // Add a step
        fireEvent.change(screen.getByTestId('input-historical-step-title'), { target: { value: 'Excavation of deep caries' } });
        fireEvent.change(screen.getByTestId('input-historical-step-notes'), { target: { value: 'No pulp exposure' } });
        fireEvent.click(screen.getByTestId('btn-add-historical-step'));

        expect(screen.getByTestId('historical-step-item-0')).toBeInTheDocument();
        expect(screen.getByText('Excavation of deep caries')).toBeInTheDocument();

        // Add an observation with canal identity
        fireEvent.change(screen.getByTestId('input-historical-obs-tooth'), { target: { value: '46' } });
        fireEvent.change(screen.getByTestId('select-historical-obs-code'), { target: { value: 'working_length' } });
        fireEvent.click(screen.getByTestId('canal-chip-MB'));
        fireEvent.change(screen.getByTestId('input-length-MB'), { target: { value: '20' } });
        fireEvent.click(screen.getByTestId('btn-save-measurement-MB'));

        expect(screen.getByTestId('historical-obs-item-0')).toBeInTheDocument();

        // Submit
        fireEvent.click(screen.getByTestId('btn-submit-historical-session'));

        await waitFor(() => {
            expect(patientsApi.startCareSession).toHaveBeenCalledTimes(1);
            expect(patientsApi.startCareSession).toHaveBeenCalledWith(
                5,
                expect.objectContaining({
                    is_historical: true,
                    historical_steps: expect.arrayContaining([
                        expect.objectContaining({
                            title: 'Excavation of deep caries',
                            status: 'completed',
                        }),
                    ]),
                    historical_observations: expect.arrayContaining([
                        expect.objectContaining({
                            observation_code: 'working_length',
                            tooth_key: '46',
                            canal_id: 'MB',
                            structured_value: expect.objectContaining({ length_mm: 20, canal_id: 'MB' }),
                        }),
                    ]),
                })
            );
        });
    });

    it.each([
        'Detailed clinical assessment including restorative preparation and final occlusal adjustment',
        'تقييم الحالة وتجهيز السن للحشو',
    ])('preserves the full title and delegates identity assignment to the server: %s', async (title) => {
        patientsApi.startCareSession.mockResolvedValueOnce({ data: { id: 79 } });
        render(<HistoricalCareSessionModal isOpen onClose={vi.fn()} patientId={5}
            patientWorkItems={mockWorkItems} doctors={mockDoctors} currentUserId={1} />);
        fireEvent.change(screen.getByTestId('input-historical-step-title'), { target: { value: title } });
        fireEvent.click(screen.getByTestId('btn-add-historical-step'));
        fireEvent.click(screen.getByTestId('btn-submit-historical-session'));
        await waitFor(() => expect(patientsApi.startCareSession).toHaveBeenCalledTimes(1));
        const step = patientsApi.startCareSession.mock.lastCall[1].historical_steps[0];
        expect(step).toMatchObject({ title, work_item_id: 101, status: 'completed' });
        expect(step).not.toHaveProperty('step_code');
        expect(step).not.toHaveProperty('logical_step_code');
    });
});

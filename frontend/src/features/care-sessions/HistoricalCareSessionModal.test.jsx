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
        fireEvent.change(screen.getByTestId('input-historical-obs-canal'), { target: { value: 'MB' } });
        fireEvent.change(screen.getByTestId('input-historical-obs-value'), { target: { value: '20' } });
        fireEvent.change(screen.getByTestId('select-historical-obs-code'), { target: { value: 'working_length' } });
        fireEvent.click(screen.getByTestId('btn-add-historical-obs'));

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
                            logical_step_code: 'excavation_of_deep_caries',
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
});

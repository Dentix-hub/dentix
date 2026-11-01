import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CareObservationAmendmentModal from './CareObservationAmendmentModal';
import * as patientsApi from '@/api/patients';

vi.mock('@/api/patients', () => ({
    amendCareObservation: vi.fn(),
}));

describe('CareObservationAmendmentModal', () => {
    const mockObs = {
        id: 42,
        observation_code: 'canal_length',
        tooth_key: '16',
        canal_id: 'MB1',
        structured_value: { length_mm: 20.0, maf: '25' },
        notes: 'Initial measurement',
        recorded_at: '2026-10-30T10:00:00Z',
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders observation metadata and original values', () => {
        render(
            <CareObservationAmendmentModal
                isOpen={true}
                onClose={vi.fn()}
                patientId={1}
                sessionId={10}
                observation={mockObs}
                onSuccess={vi.fn()}
            />
        );

        expect(screen.getByText(/Amend Chairside Observation/i)).toBeInTheDocument();
        expect(screen.getByText(/Append-Only Clinical Audit Rule/i)).toBeInTheDocument();
        expect(screen.getByText(/ID #42/i)).toBeInTheDocument();
        expect(screen.getByText(/Length: 20 mm \| MAF: #25/i)).toBeInTheDocument();
        expect(screen.getByTestId('amend-length-input')).toHaveValue(20);
        expect(screen.getByTestId('amend-maf-input')).toHaveValue('25');
    });

    it('sends a corrected canal target while retaining the original display', async () => {
        patientsApi.amendCareObservation.mockResolvedValue({ data: { id: 43 } });
        render(<CareObservationAmendmentModal isOpen patientId={1} sessionId={10} observation={mockObs} onClose={vi.fn()} onSuccess={vi.fn()} />);
        fireEvent.change(screen.getByLabelText('Corrected Canal'), { target: { value: 'MB2' } });
        fireEvent.change(screen.getByTestId('amend-reason-input'), { target: { value: 'Correct canal identification' } });
        fireEvent.click(screen.getByTestId('confirm-amendment-button'));
        await waitFor(() => expect(patientsApi.amendCareObservation).toHaveBeenCalledWith(1, 10, 42, expect.objectContaining({ canal_id: 'MB2', tooth_key: '16' })));
        expect(mockObs.canal_id).toBe('MB1');
    });

    it('requires a mandatory amendment reason to submit', async () => {
        const mockOnSuccess = vi.fn();
        const mockOnClose = vi.fn();
        patientsApi.amendCareObservation.mockResolvedValueOnce({ data: { id: 43 } });

        render(
            <CareObservationAmendmentModal
                isOpen={true}
                onClose={mockOnClose}
                patientId={1}
                sessionId={10}
                observation={mockObs}
                onSuccess={mockOnSuccess}
            />
        );

        const submitBtn = screen.getByTestId('confirm-amendment-button');
        expect(submitBtn).toBeDisabled();

        // Change corrected length
        const lengthInput = screen.getByTestId('amend-length-input');
        fireEvent.change(lengthInput, { target: { value: '21.5' } });

        // Enter mandatory reason
        const reasonInput = screen.getByTestId('amend-reason-input');
        fireEvent.change(reasonInput, { target: { value: 'Negotiated calcified apex curvature' } });

        expect(submitBtn).not.toBeDisabled();
        fireEvent.click(submitBtn);

        await waitFor(() => {
            expect(patientsApi.amendCareObservation).toHaveBeenCalledTimes(1);
            expect(patientsApi.amendCareObservation).toHaveBeenCalledWith(
                1,
                10,
                42,
                expect.objectContaining({
                    reason: 'Negotiated calcified apex curvature',
                    observation_code: 'canal_length',
                    tooth_key: '16',
                    canal_id: 'MB1',
                    structured_value: expect.objectContaining({
                        length_mm: 21.5,
                        maf: '25',
                    }),
                })
            );
            expect(mockOnSuccess).toHaveBeenCalledTimes(1);
            expect(mockOnClose).toHaveBeenCalledTimes(1);
        });
    });
});

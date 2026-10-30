import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ContinueTreatmentCard from '@/features/care-sessions/ContinueTreatmentCard';

describe('Slice S21: Care Session Resume Engine & Continue-Treatment Card', () => {
    const mockResumableContext = {
        has_resumable: true,
        paused_session: null,
        items: [
            {
                work_item_id: 101,
                procedure_code: 'ENDO_RCT',
                tooth_key: '46',
                title: 'ENDO_RCT',
                status: 'active',
                total_steps: 6,
                completed_steps_count: 3,
                next_step_title: 'Cleaning & Shaping',
                last_session_id: 1,
                last_session_at: '2026-10-18T10:00:00Z',
                last_notes: 'Patient tolerated canal instrumentation well',
                observations: [
                    {
                        id: 1,
                        observation_code: 'working_length',
                        tooth_key: '46',
                        canal_id: 'MB',
                        root_id: 'MB',
                        structured_value: { length_mm: 20.0, reference_point: 'Incisal', maf: 25 },
                    },
                    {
                        id: 2,
                        observation_code: 'working_length',
                        tooth_key: '46',
                        canal_id: 'ML',
                        root_id: 'ML',
                        structured_value: { length_mm: 20.5, reference_point: 'Incisal', maf: 25 },
                    },
                    {
                        id: 3,
                        observation_code: 'working_length',
                        tooth_key: '46',
                        canal_id: 'D',
                        root_id: 'D',
                        structured_value: { length_mm: 21.0, reference_point: 'Cusp', maf: 30 },
                    },
                ],
            },
        ],
    };

    it('renders null when has_resumable is false', () => {
        const { container } = render(
            <ContinueTreatmentCard
                resumableContext={{ has_resumable: false, items: [] }}
                onResumeTreatment={vi.fn()}
            />
        );
        expect(container.firstChild).toBeNull();
    });

    it('renders tooth key, procedure title, and step progress for unfinished treatment (G10-M13)', () => {
        render(
            <ContinueTreatmentCard
                resumableContext={mockResumableContext}
                onResumeTreatment={vi.fn()}
            />
        );

        expect(screen.getByTestId('continue-treatment-card')).toBeInTheDocument();
        expect(screen.getByTestId('continue-card-tooth-badge')).toHaveTextContent('Tooth 46');
        expect(screen.getByText('Root Canal Treatment (RCT)')).toBeInTheDocument();
        expect(screen.getByText(/3 of 6 steps completed/)).toBeInTheDocument();
        expect(screen.getByText(/Next: Cleaning & Shaping/)).toBeInTheDocument();
    });

    it('displays recorded canal working lengths without reading old notes (G10-M10, G10-M12)', () => {
        render(
            <ContinueTreatmentCard
                resumableContext={mockResumableContext}
                onResumeTreatment={vi.fn()}
            />
        );

        const preview = screen.getByTestId('canal-measurements-preview');
        expect(preview).toBeInTheDocument();
        expect(preview).toHaveTextContent('MB: 20mm(MAF #25)');
        expect(preview).toHaveTextContent('ML: 20.5mm(MAF #25)');
        expect(preview).toHaveTextContent('D: 21mm(MAF #30)');
    });

    it('triggers onResumeTreatment callback when Resume Treatment button is clicked (G10-M13)', () => {
        const resumeSpy = vi.fn();
        render(
            <ContinueTreatmentCard
                resumableContext={mockResumableContext}
                onResumeTreatment={resumeSpy}
            />
        );

        const resumeBtn = screen.getByTestId('resume-treatment-btn');
        expect(resumeBtn).toHaveTextContent('Resume Treatment');
        fireEvent.click(resumeBtn);

        expect(resumeSpy).toHaveBeenCalledTimes(1);
        expect(resumeSpy).toHaveBeenCalledWith(
            expect.objectContaining({
                workItemId: 101,
                toothKey: '46',
                isPaused: false,
                procedureCode: 'ENDO_RCT',
            })
        );
    });

    it('handles paused session state and displays Paused Session badge', () => {
        const pausedContext = {
            has_resumable: true,
            paused_session: {
                id: 42,
                status: 'paused',
                notes: 'Temporarily paused while taking control radiograph',
                steps: [
                    { id: 1, step_order: 1, title: 'Access', status: 'completed' },
                    { id: 2, step_order: 2, title: 'Canal Measurement', status: 'pending' },
                ],
                observations: [],
            },
            items: [],
        };

        const resumeSpy = vi.fn();
        render(
            <ContinueTreatmentCard
                resumableContext={pausedContext}
                onResumeTreatment={resumeSpy}
            />
        );

        expect(screen.getByText('Paused Session')).toBeInTheDocument();
        const resumeBtn = screen.getByTestId('resume-treatment-btn');
        expect(resumeBtn).toHaveTextContent('Resume Session');

        fireEvent.click(resumeBtn);
        expect(resumeSpy).toHaveBeenCalledWith(
            expect.objectContaining({
                sessionId: 42,
                isPaused: true,
            })
        );
    });

    it('expands details to show past session notes and canal measurement cards', () => {
        render(
            <ContinueTreatmentCard
                resumableContext={mockResumableContext}
                onResumeTreatment={vi.fn()}
            />
        );

        const canalsToggle = screen.getByRole('button', { name: /Canals \(3\)/i });
        fireEvent.click(canalsToggle);

        expect(screen.getByText('Patient tolerated canal instrumentation well')).toBeInTheDocument();
        expect(screen.getByText(/Canal Observations & Measurements:/)).toBeInTheDocument();
        expect(screen.getByText('Length: 20 mm')).toBeInTheDocument();
        expect(screen.getByText('Length: 20.5 mm')).toBeInTheDocument();
        expect(screen.getByText('Length: 21 mm')).toBeInTheDocument();
    });
});

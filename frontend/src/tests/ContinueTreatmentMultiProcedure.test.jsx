import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ContinueTreatmentCard from '@/features/care-sessions/ContinueTreatmentCard';

describe('Slice S25 / Defect 3: Multi-Procedure Continuation Card', () => {
    const mockMultiResumableContext = {
        has_resumable: true,
        paused_session: null,
        items: [
            {
                work_item_id: 101,
                procedure_code: 'ENDO_RCT',
                tooth_key: '16',
                title: 'ENDO_RCT',
                status: 'active',
                total_steps: 6,
                completed_steps_count: 2,
                next_step_title: 'Working Length',
                last_session_id: 1,
                observations: [
                    {
                        id: 11,
                        observation_code: 'working_length',
                        tooth_key: '16',
                        canal_id: 'MB1',
                        structured_value: { length_mm: 20.0, maf: 25 },
                    },
                ],
            },
            {
                work_item_id: 102,
                procedure_code: 'SURG_EXTRACT',
                tooth_key: '26',
                title: 'SURG_EXTRACT',
                status: 'active',
                total_steps: 4,
                completed_steps_count: 1,
                next_step_title: 'Luxation',
                last_session_id: 1,
                observations: [],
            },
        ],
    };

    it('renders multi-procedure tabs when items.length > 1', () => {
        render(
            <ContinueTreatmentCard
                resumableContext={mockMultiResumableContext}
                onResumeTreatment={vi.fn()}
            />
        );

        expect(screen.getByTestId('multi-procedure-selector')).toBeInTheDocument();
        expect(screen.getByTestId('select-procedure-0')).toHaveTextContent(/Tooth 16/);
        expect(screen.getByTestId('select-procedure-1')).toHaveTextContent(/Tooth 26/);
        expect(screen.getByTestId('resume-all-procedures-btn')).toHaveTextContent(/Resume All \(2\)/);
    });

    it('switches between procedures and updates active card content', () => {
        render(
            <ContinueTreatmentCard
                resumableContext={mockMultiResumableContext}
                onResumeTreatment={vi.fn()}
            />
        );

        // Initially tooth 16 is displayed
        expect(screen.getByTestId('continue-card-tooth-badge')).toHaveTextContent('Tooth 16');
        expect(screen.getByTestId('canal-measurements-preview')).toHaveTextContent(/MB1.*20mm/);

        // Switch to tooth 26 procedure
        fireEvent.click(screen.getByTestId('select-procedure-1'));

        expect(screen.getByTestId('continue-card-tooth-badge')).toHaveTextContent('Tooth 26');
        expect(screen.getByRole('heading', { level: 4 })).toHaveTextContent('SURG_EXTRACT');
        expect(screen.queryByTestId('canal-measurements-preview')).not.toBeInTheDocument();
    });

    it('resumes only selected procedure when standard resume button is clicked', () => {
        const resumeSpy = vi.fn();
        render(
            <ContinueTreatmentCard
                resumableContext={mockMultiResumableContext}
                onResumeTreatment={resumeSpy}
            />
        );

        // Switch to tooth 26
        fireEvent.click(screen.getByTestId('select-procedure-1'));
        fireEvent.click(screen.getByTestId('resume-treatment-btn'));

        expect(resumeSpy).toHaveBeenCalledTimes(1);
        expect(resumeSpy).toHaveBeenCalledWith(
            expect.objectContaining({
                workItemId: 102,
                workItemIds: [102],
                toothKey: '26',
                procedureCode: 'SURG_EXTRACT',
                resumeAll: false,
            })
        );
    });

    it('resumes all procedures when Resume All is clicked', () => {
        const resumeSpy = vi.fn();
        render(
            <ContinueTreatmentCard
                resumableContext={mockMultiResumableContext}
                onResumeTreatment={resumeSpy}
            />
        );

        fireEvent.click(screen.getByTestId('resume-all-procedures-btn'));

        expect(resumeSpy).toHaveBeenCalledTimes(1);
        expect(resumeSpy).toHaveBeenCalledWith(
            expect.objectContaining({
                workItemIds: [101, 102],
                resumeAll: true,
            })
        );
    });
});

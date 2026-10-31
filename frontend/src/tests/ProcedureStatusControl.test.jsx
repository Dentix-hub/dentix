import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProcedureStatusControl from '@/features/clinical-chart/components/ProcedureStatusControl';
import * as patientsApi from '@/api/patients';

vi.mock('@/api/patients', () => ({
    updateClinicalWorkItemStatus: vi.fn(),
}));

describe('Slice S25 / Defect 7: ProcedureStatusControl', () => {
    let queryClient;

    beforeEach(() => {
        queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });
        vi.clearAllMocks();
    });

    const renderWithClient = (ui) => {
        return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
    };

    it('renders active status with In Progress badge', () => {
        renderWithClient(
            <ProcedureStatusControl
                patientId={1}
                workItemId={101}
                currentStatus="active"
            />
        );

        expect(screen.getByTestId('procedure-status-control')).toBeInTheDocument();
        expect(screen.getByText('In Progress')).toBeInTheDocument();
        expect(screen.getByText('Mark Done')).toBeInTheDocument();
    });

    it('renders completed status with Completed badge', () => {
        renderWithClient(
            <ProcedureStatusControl
                patientId={1}
                workItemId={101}
                currentStatus="completed"
            />
        );

        expect(screen.getByText('Completed')).toBeInTheDocument();
        expect(screen.getByText('Reopen')).toBeInTheDocument();
    });

    it('performs quick completion on click when active', async () => {
        patientsApi.updateClinicalWorkItemStatus.mockResolvedValueOnce({
            data: { status: 'completed', version_id: 2 },
        });

        const statusSpy = vi.fn();
        renderWithClient(
            <ProcedureStatusControl
                patientId={1}
                workItemId={101}
                currentStatus="active"
                versionId={1}
                onStatusChanged={statusSpy}
            />
        );

        fireEvent.click(screen.getByTestId('status-toggle-btn'));

        await waitFor(() => {
            expect(patientsApi.updateClinicalWorkItemStatus).toHaveBeenCalledTimes(1);
            expect(patientsApi.updateClinicalWorkItemStatus).toHaveBeenCalledWith(
                1,
                101,
                expect.objectContaining({
                    status: 'completed',
                    expected_version_id: 1,
                })
            );
            expect(statusSpy).toHaveBeenCalledWith('completed', expect.anything());
        });
    });

    it('opens reopen dialog and submits reopen correction with required reason', async () => {
        patientsApi.updateClinicalWorkItemStatus.mockResolvedValueOnce({
            data: { status: 'active', version_id: 3 },
        });

        const statusSpy = vi.fn();
        renderWithClient(
            <ProcedureStatusControl
                patientId={1}
                workItemId={101}
                currentStatus="completed"
                versionId={2}
                onStatusChanged={statusSpy}
            />
        );

        // Clicking toggle when completed opens dialog
        fireEvent.click(screen.getByTestId('status-toggle-btn'));

        expect(screen.getByTestId('reopen-procedure-form')).toBeInTheDocument();
        expect(screen.getByText(/Reopening Procedure Confirmation/i)).toBeInTheDocument();

        // Fill reason
        const reasonInput = screen.getByTestId('reopen-reason-input');
        fireEvent.change(reasonInput, { target: { value: 'Discovered accessory canal' } });

        // Submit form
        fireEvent.click(screen.getByTestId('confirm-reopen-btn'));

        await waitFor(() => {
            expect(patientsApi.updateClinicalWorkItemStatus).toHaveBeenCalledWith(
                1,
                101,
                expect.objectContaining({
                    status: 'active',
                    intent: 'reopen_correction',
                    reason: 'Discovered accessory canal',
                    expected_version_id: 2,
                })
            );
            expect(statusSpy).toHaveBeenCalledWith('active', expect.anything());
        });
    });

    it('prompts for override reason if completion is rejected with 422 outstanding steps', async () => {
        patientsApi.updateClinicalWorkItemStatus
            .mockRejectedValueOnce({
                response: {
                    status: 422,
                    data: { detail: 'Incomplete steps require override_reason to complete procedure' },
                },
            })
            .mockResolvedValueOnce({
                data: { status: 'completed', version_id: 2 },
            });

        renderWithClient(
            <ProcedureStatusControl
                patientId={1}
                workItemId={101}
                currentStatus="active"
            />
        );

        fireEvent.click(screen.getByTestId('status-toggle-btn'));

        // Dialog should open
        await waitFor(() => {
            expect(screen.getByTestId('complete-override-form')).toBeInTheDocument();
        });

        const overrideInput = screen.getByTestId('override-reason-input');
        fireEvent.change(overrideInput, { target: { value: 'Clinically indicated to bypass remaining steps' } });

        fireEvent.click(screen.getByTestId('confirm-complete-override-btn'));

        await waitFor(() => {
            expect(patientsApi.updateClinicalWorkItemStatus).toHaveBeenLastCalledWith(
                1,
                101,
                expect.objectContaining({
                    status: 'completed',
                    override_reason: 'Clinically indicated to bypass remaining steps',
                })
            );
        });
    });
});

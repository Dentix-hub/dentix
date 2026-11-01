import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TreatmentHistory from '@/features/patients/PatientTabs/TreatmentHistory';
import { useAuthStore } from '@/store/auth.store';

vi.mock('@/api/patients', () => ({
    getPatientCareSessions: vi.fn(),
    updateClinicalWorkItemStatus: vi.fn(),
}));

describe('Slice S25 / Defects 4, 6, 7: TreatmentHistory with Real Care Sessions', () => {
    let queryClient;

    beforeEach(() => {
        useAuthStore.setState({ user: { id: 1, role: 'doctor', permissions: ['clinical:write'] } });
        queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });
        vi.clearAllMocks();
    });

    const renderWithClient = (ui) => {
        return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
    };

    const mockHistory = [
        {
            id: 10,
            work_item_id: 101,
            date: '2026-10-15T09:00:00Z',
            tooth_number: 16,
            diagnosis: 'Irreversible Pulpitis',
            procedure: 'Root Canal Treatment (RCT)',
            status: 'In Progress',
            canal_count: 3,
            notes: 'Tooth tender to percussion',
        },
    ];

    const mockCareSessions = [
        {
            id: 201,
            patient_id: 1,
            status: 'completed',
            actual_visit_date: '2026-10-18T14:30:00Z',
            is_historical: false,
            notes: 'Canals located and instrumented to size 25',
            procedures: [{ work_item_id: 101 }],
            steps: [
                { id: 1, title: 'Access Opening', status: 'completed' },
                { id: 2, title: 'Canal Location', status: 'completed' },
                { id: 3, title: 'Working Length', status: 'completed' },
                { id: 4, title: 'Obturation', status: 'pending' },
            ],
            observations: [
                {
                    id: 31,
                    canal_id: 'MB1',
                    structured_value: { length_mm: 20.5, maf: 25 },
                },
                {
                    id: 32,
                    canal_id: 'DB',
                    structured_value: { length_mm: 19.5, maf: 25 },
                },
            ],
            next_visit_requests: [
                {
                    id: 501,
                    reason: 'Tooth 16: Obturation',
                    suggested_duration_minutes: 45,
                    status: 'requested',
                },
            ],
        },
    ];

    it('renders treatments table with ProcedureStatusControl (Defect 7)', () => {
        renderWithClient(
            <TreatmentHistory
                history={mockHistory}
                patientId={1}
                careSessions={mockCareSessions}
            />
        );

        expect(screen.getByTestId('treatment-history-container')).toBeInTheDocument();
        expect(screen.getByText('Root Canal Treatment (RCT)')).toBeInTheDocument();
        expect(screen.getByText('Irreversible Pulpitis')).toBeInTheDocument();

        // In Progress status control button is rendered (Defect 7)
        expect(screen.getByTestId('procedure-status-control')).toBeInTheDocument();
        expect(screen.getByText('In Progress')).toBeInTheDocument();
    });

    it('exposes expandable real care session history under procedure row (Defect 6)', () => {
        renderWithClient(
            <TreatmentHistory
                history={mockHistory}
                patientId={1}
                careSessions={mockCareSessions}
            />
        );

        // Shows Care Sessions toggle button
        const toggleBtn = screen.getByTestId('toggle-sessions-10');
        expect(toggleBtn).toBeInTheDocument();
        expect(toggleBtn).toHaveTextContent(/Care Sessions \(1\)/);

        // Click to expand
        fireEvent.click(toggleBtn);

        const breakdown = screen.getByTestId('sessions-breakdown-10');
        expect(breakdown).toBeInTheDocument();
        expect(breakdown).toHaveTextContent('Session #201');

        // Verify Defect 4: uses actual_visit_date
        expect(breakdown).toHaveTextContent(/Oct 18, 2026/);

        // Verify steps performed
        expect(breakdown).toHaveTextContent('Access Opening');
        expect(breakdown).toHaveTextContent('Working Length');

        // Verify recorded canal lengths
        expect(breakdown).toHaveTextContent(/MB1.*20.5mm/);
        expect(breakdown).toHaveTextContent(/DB.*19.5mm/);

        // Verify session notes
        expect(breakdown).toHaveTextContent('Canals located and instrumented to size 25');

        // Verify next visit request
        expect(breakdown).toHaveTextContent(/Follow-up: Tooth 16: Obturation \(45m\)/);
        expect(breakdown).toHaveTextContent(/requested/i);
    });

    it('switches to unified visits timeline view', () => {
        renderWithClient(
            <TreatmentHistory
                history={mockHistory}
                patientId={1}
                careSessions={mockCareSessions}
            />
        );

        const sessionsTab = screen.getByTestId('view-sessions-tab');
        expect(sessionsTab).toBeInTheDocument();

        fireEvent.click(sessionsTab);

        expect(screen.getByTestId('care-sessions-timeline-view')).toBeInTheDocument();
        expect(screen.getByTestId('timeline-session-201')).toBeInTheDocument();
        expect(screen.getByText(/Visit Date: Oct 18, 2026/)).toBeInTheDocument();
    });

    it('does not guess work item IDs for legacy records without work_item_id (Issue 2)', () => {
        const legacyHistory = [
            {
                id: 99,
                // work_item_id is intentionally undefined/null
                date: '2026-10-15T09:00:00Z',
                tooth_number: 16,
                diagnosis: 'Caries',
                procedure: 'Composite Filling',
                status: 'Done',
            },
        ];

        renderWithClient(
            <TreatmentHistory
                history={legacyHistory}
                patientId={1}
                careSessions={[]}
            />
        );

        // Does NOT render ProcedureStatusControl with guessed ID
        expect(screen.queryByTestId('procedure-status-control')).not.toBeInTheDocument();
        // Renders static badge
        expect(screen.getByText('Done')).toBeInTheDocument();
    });

    it('opens follow-up management modal from session next-visit request (Issue 8)', () => {
        renderWithClient(
            <TreatmentHistory
                history={mockHistory}
                patientId={1}
                careSessions={mockCareSessions}
            />
        );

        // Expand session
        fireEvent.click(screen.getByTestId('toggle-sessions-10'));

        // Click manage button on follow up request
        const manageBtn = screen.getByTestId('manage-follow-up-btn-501');
        expect(manageBtn).toBeInTheDocument();
        fireEvent.click(manageBtn);

        // Follow up modal should open
        expect(screen.getByTestId('follow-up-management-modal')).toBeInTheDocument();
    });

    it('hides clinical follow-up manage button for receptionists without CLINICAL_WRITE (Review 2 Issue 7)', () => {
        useAuthStore.setState({ user: { id: 10, role: 'receptionist', permissions: [] } });

        renderWithClient(
            <TreatmentHistory
                history={mockHistory}
                patientId={1}
                careSessions={mockCareSessions}
            />
        );

        // Expand session
        fireEvent.click(screen.getByTestId('toggle-sessions-10'));

        // Receptionist must NOT see clinical manage button
        expect(screen.queryByTestId('manage-follow-up-btn-501')).not.toBeInTheDocument();
    });

    it('shows clinical follow-up manage button for clinicians with CLINICAL_WRITE (Review 2 Issue 7)', () => {
        useAuthStore.setState({ user: { id: 2, role: 'doctor', permissions: ['clinical:write'] } });

        renderWithClient(
            <TreatmentHistory
                history={mockHistory}
                patientId={1}
                careSessions={mockCareSessions}
            />
        );

        // Expand session
        fireEvent.click(screen.getByTestId('toggle-sessions-10'));

        // Clinician must see clinical manage button
        expect(screen.getByTestId('manage-follow-up-btn-501')).toBeInTheDocument();
    });
});

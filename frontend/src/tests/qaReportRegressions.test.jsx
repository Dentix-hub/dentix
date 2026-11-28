import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const {
    mockAddCareSessionProcedure,
    mockGetLaboratories,
    mockCreatePatient,
    mockGetDoctors,
    mockGetPriceLists,
    mockGetWorkflowTemplates,
    mockToastError,
    mockToastSuccess,
} = vi.hoisted(() => ({
    mockAddCareSessionProcedure: vi.fn(),
    mockGetLaboratories: vi.fn(),
    mockCreatePatient: vi.fn(),
    mockGetDoctors: vi.fn(),
    mockGetPriceLists: vi.fn(),
    mockGetWorkflowTemplates: vi.fn(),
    mockToastError: vi.fn(),
    mockToastSuccess: vi.fn(),
}));

vi.mock('@/api', () => ({
    API_URL: '',
    getDoctors: (...args) => mockGetDoctors(...args),
    getPriceLists: (...args) => mockGetPriceLists(...args),
    createTreatment: vi.fn(),
    updateTreatment: vi.fn(),
    updateToothStatus: vi.fn(),
    createLabOrder: vi.fn(),
    getLaboratories: (...args) => mockGetLaboratories(...args),
    getPatientLabOrders: vi.fn().mockResolvedValue({ data: [] }),
    addTreatmentSession: vi.fn(),
    createLabPayment: vi.fn(),
    getSavedMedications: vi.fn().mockResolvedValue({ data: [] }),
}));

vi.mock('@/api/patients', () => ({
    addCareSessionProcedure: (...args) => mockAddCareSessionProcedure(...args),
    removeCareSessionProcedure: vi.fn(),
    addCareSessionStep: vi.fn(),
    getPatientCareSessions: vi.fn().mockResolvedValue({ data: [] }),
    getPatientClinicalWorkItems: vi.fn().mockResolvedValue({ data: [] }),
    updateClinicalWorkItemStatus: vi.fn(),
    getCareSessionDraft: vi.fn().mockResolvedValue({ data: null }),
    saveCareSessionDraft: vi.fn().mockResolvedValue({ data: { version_id: 2 } }),
    deleteCareSessionDraft: vi.fn().mockResolvedValue({}),
}));

vi.mock('@/api/labs', () => ({
    getLaboratories: (...args) => mockGetLaboratories(...args),
    dispatchLabHandoff: vi.fn(),
}));

vi.mock('@/api/workflowTemplates', () => ({
    getWorkflowTemplates: (...args) => mockGetWorkflowTemplates(...args),
    updateWorkflowTemplateStatus: vi.fn(),
}));

vi.mock('@/hooks/usePatients', () => ({
    useCreatePatient: () => ({
        isPending: false,
        mutateAsync: (...args) => mockCreatePatient(...args),
    }),
    useSearchPatients: () => ({ data: [] }),
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({ user: { id: 1, role: 'admin', username: 'admin' } }),
}));

vi.mock('@/store/auth.store', () => ({
    useAuthStore: (selector) =>
        selector({ user: { id: 1, role: 'doctor', permissions: ['clinical:write'] } }),
}));

vi.mock('@/api/admin', () => ({
    getDoctors: vi.fn().mockResolvedValue({ data: { doctors: [] } }),
}));

vi.mock('@/api/inventory', () => ({
    getStockSummary: vi.fn().mockResolvedValue({ data: [] }),
    getMaterials: vi.fn().mockResolvedValue({ data: [] }),
    getActiveSessions: vi.fn().mockResolvedValue({ data: [] }),
}));

vi.mock('@/shared/ui', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        toast: Object.assign(vi.fn(), {
            error: (...args) => mockToastError(...args),
            success: (...args) => mockToastSuccess(...args),
            info: vi.fn(),
            dismiss: vi.fn(),
        }),
    };
});

import GenericVisitWorkspace from '@/features/care-sessions/GenericVisitWorkspace';
import EditPatientModal from '@/features/patients/modals/EditPatientModal';
import PatientModal from '@/features/patients/modals/PatientModal';
import PrescriptionModal from '@/shared/ui/modals/PrescriptionModal';
import { buildAttachmentUrl } from '@/features/clinical-attachments/attachmentUtils';
import ProtectedImage from '@/features/clinical-attachments/components/ProtectedImage';
import PriceListSelector from '@/shared/ui/PriceListSelector';
import WorkflowTemplateList from '@/features/templates/WorkflowTemplateList';
import WeeklyCalendar from '@/shared/ui/WeeklyCalendar';
import TreatmentHistory from '@/features/patients/PatientTabs/TreatmentHistory';

vi.mock('@fullcalendar/react', () => ({
    default: (props) => (
        <div
            data-testid="mock-fullcalendar"
            data-locale={props.locale}
            data-has-ar-locale={String(Array.isArray(props.locales) && props.locales.some((l) => l.code === 'ar'))}
            data-today-label={props.buttonText?.today || ''}
            data-week-label={props.buttonText?.week || ''}
        />
    ),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallbackOrOpts) => {
            const translations = {
                'appointments.calendar.today': 'اليوم',
                'appointments.calendar.week': 'أسبوع',
                'appointments.calendar.month': 'شهر',
                'appointments.calendar.list': 'قائمة',
                'care_session.care_session_title': 'جلسة رعاية',
                'care_session.visit_date': 'تاريخ الزيارة',
                'care_session.historical_entry': 'توثيق تاريخي',
                'care_session.steps_tab': 'خطوات العلاج',
                'care_session.followup_prefix': 'متابعة',
                'care_session.duration_unit_short': 'د',
                'backup.image_unavailable': 'الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف',
                'backup.local_image_unavailable': 'الصورة غير متاحة حاليًا',
                'templates.col_template_procedure': 'القالب / الإجراء',
                'templates.col_version': 'الإصدار',
                'templates.col_steps': 'الخطوات',
                'templates.col_custom_fields': 'الحقول المخصصة',
                'templates.col_type': 'النوع',
                'templates.col_status': 'الحالة',
                'templates.col_actions': 'الإجراءات',
                'templates.type_system_default': 'افتراضي بالنظام',
                'templates.status_active': 'نشط',
                'templates.customize': 'تخصيص',
                'templates.none': 'لا يوجد',
                'templates.step_other': 'خطوات',
            };
            if (translations[key]) return translations[key];
            if (typeof fallbackOrOpts === 'string') return fallbackOrOpts;
            return key;
        },
        i18n: { language: 'ar' },
    }),
}));

const tPass = (k, f) => (typeof f === 'string' ? f : k);

function wrap(ui) {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('QA Report & Live Production Frontend Regressions', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGetDoctors.mockResolvedValue({ data: [] });
        mockGetLaboratories.mockResolvedValue({ data: [{ id: 1, name: 'Alpha Lab' }] });
        mockGetPriceLists.mockResolvedValue({ data: [{ id: 10, name: 'VIP', type: 'regular' }] });
        mockGetWorkflowTemplates.mockResolvedValue({
            data: [
                {
                    id: 1,
                    template_code: 'ENDO_RCT',
                    title: 'RCT Blueprint',
                    is_active: true,
                    is_customized: false,
                    version: 1,
                    definition: { steps: [{ id: 's1' }, { id: 's2' }], custom_fields: [] },
                },
            ],
        });
    });

    it('QA-02: GenericVisitWorkspace excludes legacy_fallback items and renders 422 array errors without crashing', async () => {
        const legacyItem = { id: 'legacy-2', kind: 'procedure', code: 'REST_COMPOSITE', status: 'active', provenance: 'legacy_fallback' };
        const nativeItem = { id: 12, kind: 'procedure', code: 'ENDO_RCT', status: 'active', provenance: 'native' };
        mockAddCareSessionProcedure.mockRejectedValueOnce({
            response: {
                status: 422,
                data: {
                    detail: [{ type: 'int_parsing', loc: ['path', 'work_item_id'], msg: 'Input should be a valid integer' }],
                },
            },
        });

        wrap(
            <GenericVisitWorkspace
                isOpen
                session={{ id: 2, patient_id: 2, status: 'in_progress', procedures: [], steps: [], observations: [] }}
                patient={{ id: 2, name: 'Test' }}
                patientWorkItems={[legacyItem, nativeItem]}
                onClose={vi.fn()}
                onOpenFinishSheet={vi.fn()}
                t={tPass}
            />
        );

        fireEvent.click(screen.getByTestId('btn-add-proc-to-visit'));
        const dropdown = screen.getByTestId('dropdown-available-procedures');
        expect(dropdown).not.toHaveTextContent('REST_COMPOSITE');
        expect(dropdown).toHaveTextContent('ENDO_RCT');

        fireEvent.click(screen.getByText('ENDO_RCT'));
        await waitFor(() => {
            expect(screen.getByTestId('workspace-error-banner')).toHaveTextContent('Input should be a valid integer');
        });
    });

    it('QA-06: unlinked GenericVisitWorkspace disables procedure notes and next action with notice', () => {
        wrap(
            <GenericVisitWorkspace
                isOpen
                session={{ id: 2, patient_id: 2, status: 'in_progress', procedures: [], steps: [], observations: [] }}
                patient={{ id: 2, name: 'Test' }}
                patientWorkItems={[]}
                onClose={vi.fn()}
                onOpenFinishSheet={vi.fn()}
                t={tPass}
            />
        );

        expect(screen.getByTestId('workspace-notes-unlinked-notice')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-proc-notes-input')).toBeDisabled();
        expect(screen.getByTestId('workspace-proc-next-action-input')).toBeDisabled();
    });

    it('QA-08 & QA-09: EditPatientModal edits medical_history and PatientModal deduplicates rapid double-submit', async () => {
        const onSaveEdit = vi.fn();
        wrap(
            <EditPatientModal
                isOpen
                onClose={vi.fn()}
                onSave={onSaveEdit}
                initialData={{ id: 5, name: 'Ali', medical_history: 'سكري' }}
            />
        );

        const medInput = screen.getByLabelText('patients.form.medical_history');
        expect(medInput).toHaveValue('سكري');
        fireEvent.change(medInput, { target: { value: 'سكري، حساسية' } });
        fireEvent.click(screen.getByRole('button', { name: 'common.save' }));
        expect(onSaveEdit).toHaveBeenCalledWith(expect.objectContaining({ medical_history: 'سكري، حساسية' }));

        let resolveCreate;
        mockCreatePatient.mockImplementationOnce(
            () => new Promise((resolve) => { resolveCreate = resolve; })
        );
        wrap(<PatientModal isOpen onClose={vi.fn()} onSuccess={vi.fn()} />);

        const nameInput = screen.getByPlaceholderText('patients.form.name_placeholder');
        fireEvent.change(nameInput, { target: { value: 'Sara Mohamed' } });
        const form = nameInput.closest('form');
        fireEvent.submit(form);
        fireEvent.submit(form);
        expect(mockCreatePatient).toHaveBeenCalledTimes(1);
        await act(async () => {
            resolveCreate({ data: { id: 99 } });
        });
    });

    it('QA-14: PrescriptionModal blocks empty prescription and strips blank rows before printing', () => {
        const onPrint = vi.fn();
        render(<PrescriptionModal isOpen onClose={vi.fn()} onPrint={onPrint} />);

        fireEvent.click(screen.getByRole('button', { name: 'طباعة وحفظ' }));
        expect(onPrint).not.toHaveBeenCalled();
        expect(screen.getByTestId('rx-validation-error')).toBeInTheDocument();

        const nameInput = screen.getByPlaceholderText('الدواء');
        fireEvent.change(nameInput, { target: { value: 'Amoxicillin' } });
        fireEvent.click(screen.getByRole('button', { name: 'طباعة وحفظ' }));
        expect(onPrint).toHaveBeenCalledWith({
            drugs: [{ name: 'Amoxicillin', dose: '' }],
            notes: '',
        });
    });

    it('QA-16 / LIVE-02: buildAttachmentUrl maps local paths to /api/v1/upload/file and ProtectedImage differentiates local vs Drive errors', () => {
        expect(buildAttachmentUrl('tenant_2/abc.png')).toBe('/api/v1/upload/file/tenant_2/abc.png');
        expect(buildAttachmentUrl('/api/v1/upload/drive/uuid/content')).toBe('/api/v1/upload/drive/uuid/content');

        const { rerender } = render(<ProtectedImage filePath="tenant_2/abc.png" alt="Local" />);
        fireEvent.error(screen.getByAltText('Local'));
        expect(screen.getByRole('img', { name: 'الصورة غير متاحة حاليًا' })).toBeInTheDocument();

        rerender(<ProtectedImage filePath="/api/v1/upload/drive/uuid/content" alt="Drive" />);
        fireEvent.error(screen.getByAltText('Drive'));
        expect(screen.getByRole('img', { name: 'الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف' })).toBeInTheDocument();
    });

    it('QA-17 & QA-20 / LIVE-04,05,07: PriceListSelector loads without getToken() and WorkflowTemplateList unwraps and localizes table', async () => {
        wrap(<PriceListSelector value="" onChange={vi.fn()} />);
        await waitFor(() => expect(screen.getByText('VIP')).toBeInTheDocument());

        wrap(<WorkflowTemplateList />);
        await waitFor(() => expect(screen.getByText('RCT Blueprint')).toBeInTheDocument());
        expect(screen.getByText('القالب / الإجراء')).toBeInTheDocument();
        expect(screen.getByText('افتراضي بالنظام')).toBeInTheDocument();
        expect(screen.getByText('نشط')).toBeInTheDocument();
        expect(screen.getByText('تخصيص')).toBeInTheDocument();
    });

    it('QA-19 / LIVE-07: WeeklyCalendar configures Arabic locale/labels and TreatmentHistory localizes timeline & hides disabled notice while loading', () => {
        render(<WeeklyCalendar appointments={[]} />);
        const cal = screen.getByTestId('mock-fullcalendar');
        expect(cal).toHaveAttribute('data-locale', 'ar');
        expect(cal).toHaveAttribute('data-has-ar-locale', 'true');
        expect(cal).toHaveAttribute('data-today-label', 'اليوم');
        expect(cal).toHaveAttribute('data-week-label', 'أسبوع');

        const { rerender } = wrap(
            <TreatmentHistory
                nativeWritesEnabled={false}
                nativeWritesLoading
                patientId={1}
                history={[]}
                careSessions={[]}
            />
        );
        expect(screen.queryByTestId('native-session-unavailable')).not.toBeInTheDocument();

        rerender(
            <QueryClientProvider client={new QueryClient()}>
                <TreatmentHistory
                    nativeWritesEnabled
                    patientId={1}
                    history={[]}
                    careSessions={[
                        {
                            id: 10,
                            status: 'completed',
                            is_historical: true,
                            actual_visit_date: '2026-10-18T10:00:00Z',
                            steps: [{ id: 1, title: 'Step', status: 'completed' }],
                            observations: [],
                        },
                    ]}
                />
            </QueryClientProvider>
        );
        fireEvent.click(screen.getByTestId('view-sessions-tab'));
        const timeline = screen.getByTestId('care-sessions-timeline-view');
        expect(timeline).toHaveTextContent('جلسة رعاية');
        expect(timeline).toHaveTextContent('تاريخ الزيارة');
        expect(timeline).toHaveTextContent('توثيق تاريخي');
        expect(timeline).not.toHaveTextContent('WORKFLOW');
    });

    it('Bug 16: TreatmentHistory masks raw Link:LabOrder:N notes in clinical display', () => {
        wrap(
            <TreatmentHistory
                nativeWritesEnabled={false}
                patientId={398}
                history={[
                    {
                        id: 101,
                        date: '2026-11-28T10:00:00Z',
                        tooth_number: 26,
                        procedure: 'عمل معمل: تاج زيركون',
                        status: 'Done',
                        notes: 'Link:LabOrder:17',
                    },
                ]}
                careSessions={[]}
            />
        );

        expect(screen.getByText(/مرتبط بطلب معمل #17/)).toBeInTheDocument();
        expect(screen.queryByText(/Link:LabOrder:17/)).not.toBeInTheDocument();
    });
});

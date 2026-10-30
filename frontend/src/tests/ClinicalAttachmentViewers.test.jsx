import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import {
    buildAttachmentUrl,
    ATTACHMENT_PURPOSE_OPTIONS,
    getPurposeLabel,
} from '../features/clinical-attachments/attachmentUtils';
import DiagnosticImageLightbox from '../features/clinical-attachments/components/DiagnosticImageLightbox';
import LinkClinicalAttachmentModal from '../features/clinical-attachments/components/LinkClinicalAttachmentModal';
import ClinicalChartInspector from '../features/clinical-chart/components/ClinicalChartInspector';
import { CLINICAL_CHART_COPY } from '../features/clinical-chart/components/clinicalChartWorkspaceCopy';
import CareSessionActiveBanner from '../features/care-sessions/CareSessionActiveBanner';
import RctStructuredCard from '../features/care-sessions/RctStructuredCard';
import PatientFiles from '../features/patients/PatientTabs/PatientFiles';

// Mock react-i18next
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
        i18n: { language: 'en' },
    }),
}));

const renderWithQueryClient = (ui) => {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
        },
    });
    return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

describe('Slice S24: Clinical Attachment Diagnostic Viewers (G15-M03..M05, M07..M08)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('attachmentUtils & Decision PD05 canonical allowlist', () => {
        it('provides canonical purpose code options conforming to Decision PD05', () => {
            const values = ATTACHMENT_PURPOSE_OPTIONS.map((opt) => opt.value);
            expect(values).toContain('PRE_OP_XRAY');
            expect(values).toContain('POST_OP_XRAY');
            expect(values).toContain('WORKING_LENGTH_XRAY');
            expect(values).toContain('INTRAORAL_PHOTO');
            expect(values).toContain('EXTRAORAL_PHOTO');
            expect(values).toContain('LAB_SCAN');
            expect(values).toContain('CONSENT_DOC');
            expect(values).toContain('OTHER');
        });

        it('buildAttachmentUrl handles null, absolute URLs, and relative paths safely', () => {
            expect(buildAttachmentUrl(null)).toBe('');
            expect(buildAttachmentUrl('https://cdn.example.com/xray.jpg')).toBe('https://cdn.example.com/xray.jpg');
            expect(buildAttachmentUrl('att-123')).toContain('/att-123');
        });

        it('getPurposeLabel returns bilingual readable fallback for each purpose', () => {
            expect(getPurposeLabel('PRE_OP_XRAY', false)).toBe('Pre-Op X-Ray');
            expect(getPurposeLabel('PRE_OP_XRAY', true)).toBe('أشعة قبل العلاج');
            expect(getPurposeLabel('WORKING_LENGTH_XRAY', false)).toBe('Working Length X-Ray');
            expect(getPurposeLabel('OTHER', false)).toBe('Other');
        });
    });

    describe('DiagnosticImageLightbox (Accessible Full-size Diagnostic Viewer)', () => {
        const sampleImage = {
            id: 'att-101',
            filename: 'periapical-46.jpg',
            file_path: 'https://example.com/xrays/periapical-46.jpg',
            purpose_code: 'PRE_OP_XRAY',
            tooth_key: '46',
            care_session_id: '202',
            work_item_id: '303',
            notes: 'Periapical radiograph showing 46 periapical radiolucency',
        };

        it('renders full-size image and clinical context badges', () => {
            const onClose = vi.fn();
            render(<DiagnosticImageLightbox isOpen={true} image={sampleImage} onClose={onClose} />);

            expect(screen.getByTestId('diagnostic-image-lightbox')).toBeInTheDocument();
            expect(screen.getByText('periapical-46.jpg')).toBeInTheDocument();
            expect(screen.getByTestId('lightbox-tooth-badge')).toHaveTextContent('Tooth 46');
            expect(screen.getByTestId('lightbox-session-badge')).toHaveTextContent('Session #202');
            expect(screen.getByTestId('lightbox-workitem-badge')).toHaveTextContent('Work Item #303');
            expect(screen.getByTestId('lightbox-purpose-badge')).toHaveTextContent('Pre-Op X-Ray');
            expect(screen.getByText(/Periapical radiograph showing 46/)).toBeInTheDocument();

            const img = screen.getByRole('img');
            expect(img).toHaveAttribute('src', 'https://example.com/xrays/periapical-46.jpg');

            fireEvent.click(screen.getByTestId('btn-close-lightbox'));
            expect(onClose).toHaveBeenCalled();
        });
    });

    describe('LinkClinicalAttachmentModal (G15-M03, M04, M05 linking)', () => {
        const mockAttachment = {
            id: 500,
            filename: 'bitewing.png',
            file_path: '/uploads/bitewing.png',
        };

        it('submits link payload with tooth_key, care_session_id, work_item_id, and purpose_code', () => {
            const onLinkCreated = vi.fn();
            render(
                <LinkClinicalAttachmentModal
                    isOpen={true}
                    attachment={mockAttachment}
                    patientId={1}
                    initialToothKey="16"
                    initialSessionId="10"
                    onLinkCreated={onLinkCreated}
                    onClose={vi.fn()}
                />
            );

            expect(screen.getByTestId('link-clinical-attachment-modal')).toBeInTheDocument();
            const toothInput = screen.getByTestId('select-tooth-key');
            expect(toothInput.value).toBe('16');

            const purposeSelect = screen.getByTestId('select-purpose-code');
            fireEvent.change(purposeSelect, { target: { value: 'WORKING_LENGTH_XRAY' } });

            const notesInput = screen.getByTestId('input-link-notes');
            fireEvent.change(notesInput, { target: { value: 'Verified to apical constriction' } });

            fireEvent.click(screen.getByTestId('btn-submit-link-attachment'));
            expect(onLinkCreated).toHaveBeenCalledWith({
                attachment_id: 500,
                tooth_key: '16',
                care_session_id: 10,
                work_item_id: null,
                purpose_code: 'WORKING_LENGTH_XRAY',
                notes: 'Verified to apical constriction',
            });
        });

        it('allows unlinking an existing link', () => {
            const onLinkDeleted = vi.fn();
            const existingLinks = [
                {
                    id: 77,
                    attachment_id: 500,
                    tooth_key: '16',
                    purpose_code: 'PRE_OP_XRAY',
                },
            ];

            render(
                <LinkClinicalAttachmentModal
                    isOpen={true}
                    attachment={mockAttachment}
                    patientId={1}
                    existingLinks={existingLinks}
                    onLinkCreated={vi.fn()}
                    onLinkDeleted={onLinkDeleted}
                    onClose={vi.fn()}
                />
            );

            const unlinkBtn = screen.getByTestId('btn-unlink-77');
            expect(unlinkBtn).toBeInTheDocument();
            fireEvent.click(unlinkBtn);
            expect(onLinkDeleted).toHaveBeenCalledWith(77);
        });
    });

    describe('G15-M07: Tooth Inspector Diagnostic Images Section', () => {
        const mockAttachments = [
            { id: 1, filename: 't16_preop.jpg', file_path: '/uploads/t16_preop.jpg' },
            { id: 2, filename: 't16_postop.jpg', file_path: '/uploads/t16_postop.jpg' },
        ];

        const mockLinks = [
            {
                id: 11,
                attachment_id: 1,
                tooth_key: '16',
                purpose_code: 'PRE_OP_XRAY',
                care_session_id: null,
                file_path: '/uploads/t16_preop.jpg',
                filename: 't16_preop.jpg',
                notes: 'Deep caries mesial 16',
            },
            {
                id: 12,
                attachment_id: 2,
                tooth_key: '16',
                purpose_code: 'POST_OP_XRAY',
                care_session_id: 1,
                file_path: '/uploads/t16_postop.jpg',
                filename: 't16_postop.jpg',
                notes: 'Final restoration post-op',
            },
        ];

        it('renders diagnostic images section with thumbnails for selected tooth', () => {
            render(
                <ClinicalChartInspector
                    copy={CLINICAL_CHART_COPY.en}
                    selection={{ toothKey: '16' }}
                    toothState={{ findings: [], procedures: [] }}
                    patientId="pat-1"
                    attachments={mockAttachments}
                    attachmentLinks={mockLinks}
                />
            );

            const section = screen.getByTestId('tooth-inspector-images');
            expect(section).toBeInTheDocument();
            expect(screen.getByTestId('tooth-image-thumbnail-11')).toBeInTheDocument();
            expect(screen.getByTestId('tooth-image-thumbnail-12')).toBeInTheDocument();

            // Purpose badges
            expect(screen.getByTestId('tooth-image-purpose-11')).toHaveTextContent('Pre-Op X-Ray');
            expect(screen.getByTestId('tooth-image-purpose-12')).toHaveTextContent('Post-Op X-Ray');
        });

        it('shows empty state when no images are linked to the selected tooth', () => {
            render(
                <ClinicalChartInspector
                    copy={CLINICAL_CHART_COPY.en}
                    selection={{ toothKey: '24' }}
                    toothState={{ findings: [], procedures: [] }}
                    patientId="pat-1"
                    attachments={mockAttachments}
                    attachmentLinks={mockLinks}
                />
            );

            expect(screen.getByTestId('inspector-no-images')).toBeInTheDocument();
            expect(screen.getByText('No diagnostic images linked to this tooth.')).toBeInTheDocument();
        });

        it('opens diagnostic lightbox when thumbnail is clicked', () => {
            render(
                <ClinicalChartInspector
                    copy={CLINICAL_CHART_COPY.en}
                    selection={{ toothKey: '16' }}
                    toothState={{ findings: [], procedures: [] }}
                    patientId="pat-1"
                    attachments={mockAttachments}
                    attachmentLinks={mockLinks}
                />
            );

            fireEvent.click(screen.getByTestId('tooth-image-thumbnail-11'));
            expect(screen.getByTestId('diagnostic-image-lightbox')).toBeInTheDocument();
            expect(screen.getByText('Deep caries mesial 16')).toBeInTheDocument();
        });
    });

    describe('G15-M08: Care Session Diagnostic Images (Banner & RCT Structured Card)', () => {
        const mockSession = {
            id: 25,
            patient_id: 1,
            status: 'in_progress',
            chair_name: 'Operatory 1',
            procedure_code: 'RCT',
            tooth_number: '36',
        };

        const mockAttachments = [
            { id: 9, filename: 'working_length_36.jpg', file_path: '/uploads/wl.jpg' },
        ];

        const mockLinks = [
            {
                id: 99,
                attachment_id: 9,
                tooth_key: '36',
                care_session_id: 25,
                purpose_code: 'WORKING_LENGTH_XRAY',
                file_path: '/uploads/wl.jpg',
                filename: 'working_length_36.jpg',
                notes: 'WL 21mm verified on apex locator & RVG',
            },
        ];

        it('CareSessionActiveBanner renders images badge count and thumbnail strip', () => {
            render(
                <CareSessionActiveBanner
                    session={mockSession}
                    onFinish={vi.fn()}
                    onCancel={vi.fn()}
                    onOpenWorkflow={vi.fn()}
                    onOpenFinishSheet={vi.fn()}
                    attachments={mockAttachments}
                    attachmentLinks={mockLinks}
                />
            );

            expect(screen.getByTestId('session-images-badge')).toBeInTheDocument();
            expect(screen.getByTestId('banner-session-images-strip')).toBeInTheDocument();
            expect(screen.getByTestId('banner-session-image-99')).toBeInTheDocument();
        });

        it('RctStructuredCard Images & X-Rays tab renders session images gallery', () => {
            render(
                <RctStructuredCard
                    session={mockSession}
                    toothKey="36"
                    onUpdateStepStatus={vi.fn()}
                    onSaveObservation={vi.fn()}
                    onFinishSession={vi.fn()}
                    attachments={mockAttachments}
                    attachmentLinks={mockLinks}
                />
            );

            const imagesTabBtn = screen.getByTestId('tab-rct-images');
            expect(imagesTabBtn).toBeInTheDocument();
            fireEvent.click(imagesTabBtn);

            const grid = screen.getByTestId('session-images-grid');
            expect(grid).toBeInTheDocument();
            expect(screen.getByTestId('session-image-thumbnail-99')).toBeInTheDocument();
            expect(screen.getByTestId('session-image-purpose-99')).toHaveTextContent('Working Length X-Ray');

            // Clicking opens lightbox
            fireEvent.click(screen.getByTestId('session-image-thumbnail-99'));
            expect(screen.getByTestId('diagnostic-image-lightbox')).toBeInTheDocument();
        });
    });

    describe('PatientFiles integration with clinical context links', () => {
        const mockAttachments = [
            {
                id: 10,
                filename: 'pano_initial.png',
                file_path: '/uploads/pano.png',
                size: 1024000,
                content_type: 'image/png',
                created_at: '2026-10-20T00:00:00Z',
            },
        ];

        const mockLinks = [
            {
                id: 100,
                attachment_id: 10,
                tooth_key: '46',
                care_session_id: 25,
                purpose_code: 'PRE_OP_XRAY',
            },
        ];

        it('displays clinical context badge on file item and provides link action', () => {
            renderWithQueryClient(
                <PatientFiles
                    patientId={1}
                    attachments={mockAttachments}
                    attachmentLinks={mockLinks}
                    handleDeleteAttachment={vi.fn()}
                    reloadAttachments={vi.fn()}
                />
            );

            expect(screen.getByTestId('attachment-context-badges-10')).toBeInTheDocument();
            expect(screen.getByTestId('badge-tooth-46')).toHaveTextContent('T46');
            expect(screen.getByTestId('badge-session-25')).toHaveTextContent('S#25');
            expect(screen.getByTestId('badge-purpose-PRE_OP_XRAY')).toHaveTextContent('Pre-Op X-Ray');
            expect(screen.getByTestId('btn-link-attachment-10')).toBeInTheDocument();

            // Click opens link modal
            fireEvent.click(screen.getByTestId('btn-link-attachment-10'));
            expect(screen.getByTestId('link-clinical-attachment-modal')).toBeInTheDocument();
        });
    });
});

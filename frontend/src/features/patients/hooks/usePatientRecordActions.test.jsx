import { renderHook, act } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePatientRecordActions } from './usePatientRecordActions';
import { toast } from '@/shared/ui';
import { uploadAttachment } from '@/api';

vi.mock('@/api', () => ({
    updatePatient: vi.fn(),
    deleteTreatment: vi.fn(),
    uploadAttachment: vi.fn(),
    deleteAttachment: vi.fn(),
    createPrescription: vi.fn(),
    updatePatientClinicalWorkItem: vi.fn(),
}));

vi.mock('@/shared/ui', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
    },
}));

describe('usePatientRecordActions - handleFileUpload', () => {
    let refetchAttachments;
    const t = (key) => key;

    beforeEach(() => {
        vi.clearAllMocks();
        refetchAttachments = vi.fn();
    });

    const createHook = (patientId = 42) => {
        return renderHook(() =>
            usePatientRecordActions({
                id: patientId,
                patient: { id: patientId, name: 'Test Patient' },
                navigate: vi.fn(),
                t,
                refetchPatient: vi.fn(),
                refetchAttachments,
                refetchHistory: vi.fn(),
                refetchWorkspace: vi.fn(),
                createPaymentMutate: vi.fn(),
                deletePaymentMutate: vi.fn(),
                setIsEditPatientOpen: vi.fn(),
                setIsPaymentModalOpen: vi.fn(),
                setIsTreatmentSheetOpen: vi.fn(),
                setIsRxModalOpen: vi.fn(),
                setEditingTreatmentId: vi.fn(),
                setNewTreatment: vi.fn(),
                getInitialTreatment: vi.fn(),
            })
        );
    };

    it('uploads file, triggers refetch, and clears input value on success', async () => {
        uploadAttachment.mockResolvedValueOnce({ id: 10, filename: 'xray.png' });
        const { result } = createHook(42);

        const mockFile = new File(['dummy content'], 'xray.png', { type: 'image/png' });
        const mockEvent = {
            target: {
                files: [mockFile],
                value: 'C:\\fakepath\\xray.png',
            },
        };

        await act(async () => {
            await result.current.handleFileUpload(mockEvent);
        });

        expect(uploadAttachment).toHaveBeenCalledWith(42, mockFile);
        expect(refetchAttachments).toHaveBeenCalledTimes(1);
        expect(mockEvent.target.value).toBe('');
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('displays backend detail string on 400 validation error (e.g. file size exceeded)', async () => {
        const serverError = {
            response: {
                status: 400,
                data: { detail: 'حجم الملف (12 MB) يتجاوز الحد الأقصى (10 MB)' },
            },
        };
        uploadAttachment.mockRejectedValueOnce(serverError);
        const { result } = createHook(42);

        const mockFile = new File(['too large'], 'large.png', { type: 'image/png' });
        const mockEvent = {
            target: {
                files: [mockFile],
                value: 'C:\\fakepath\\large.png',
            },
        };

        await act(async () => {
            await result.current.handleFileUpload(mockEvent);
        });

        expect(toast.error).toHaveBeenCalledWith('حجم الملف (12 MB) يتجاوز الحد الأقصى (10 MB)');
        expect(mockEvent.target.value).toBe('');
    });

    it('displays first error msg when detail is an array (e.g. FastAPI 422)', async () => {
        const validationError = {
            response: {
                status: 422,
                data: {
                    detail: [{ loc: ['body', 'file'], msg: 'Field required', type: 'value_error' }],
                },
            },
        };
        uploadAttachment.mockRejectedValueOnce(validationError);
        const { result } = createHook(42);

        const mockFile = new File(['content'], 'file.pdf', { type: 'application/pdf' });
        const mockEvent = {
            target: {
                files: [mockFile],
                value: 'file.pdf',
            },
        };

        await act(async () => {
            await result.current.handleFileUpload(mockEvent);
        });

        expect(toast.error).toHaveBeenCalledWith('Field required');
        expect(mockEvent.target.value).toBe('');
    });

    it('displays response message when present and detail is omitted', async () => {
        const errorWithMessage = {
            response: {
                status: 400,
                data: { message: 'نوع الملف غير مدعوم' },
            },
        };
        uploadAttachment.mockRejectedValueOnce(errorWithMessage);
        const { result } = createHook(42);

        const mockFile = new File(['content'], 'file.xyz', { type: 'application/octet-stream' });
        const mockEvent = {
            target: {
                files: [mockFile],
                value: 'file.xyz',
            },
        };

        await act(async () => {
            await result.current.handleFileUpload(mockEvent);
        });

        expect(toast.error).toHaveBeenCalledWith('نوع الملف غير مدعوم');
    });

    it('falls back to translated upload_fail when server provides no specific message', async () => {
        uploadAttachment.mockRejectedValueOnce(new Error('Network Error'));
        const { result } = createHook(42);

        const mockFile = new File(['content'], 'test.png', { type: 'image/png' });
        const mockEvent = {
            target: {
                files: [mockFile],
                value: 'test.png',
            },
        };

        await act(async () => {
            await result.current.handleFileUpload(mockEvent);
        });

        expect(toast.error).toHaveBeenCalledWith('patient_details.alerts.upload_fail');
        expect(mockEvent.target.value).toBe('');
    });

    it('does nothing when no file is selected', async () => {
        const { result } = createHook(42);
        const mockEvent = { target: { files: [] } };

        await act(async () => {
            await result.current.handleFileUpload(mockEvent);
        });

        expect(uploadAttachment).not.toHaveBeenCalled();
        expect(toast.error).not.toHaveBeenCalled();
    });
});

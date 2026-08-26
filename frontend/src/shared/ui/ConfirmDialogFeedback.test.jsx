import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ConfirmDialog from './ConfirmDialog';

describe('Shared Admin Feedback Primitives (ConfirmDialog) MS-31', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders dialog with message and buttons when open', () => {
        const onConfirm = vi.fn();
        const onClose = vi.fn();

        render(
            <ConfirmDialog
                isOpen={true}
                title="تأكيد الحذف"
                message="هل أنت متأكد من المتابعة؟"
                confirmText="حذف نهائي"
                cancelText="إلغاء"
                variant="danger"
                onConfirm={onConfirm}
                onClose={onClose}
            />
        );

        expect(screen.getByText('تأكيد الحذف')).toBeInTheDocument();
        expect(screen.getByText('هل أنت متأكد من المتابعة؟')).toBeInTheDocument();

        // Click cancel triggers onClose
        const cancelBtn = screen.getByRole('button', { name: 'إلغاء' });
        fireEvent.click(cancelBtn);
        expect(onClose).toHaveBeenCalled();

        // Click confirm triggers onConfirm and onClose
        const confirmBtn = screen.getByRole('button', { name: 'حذف نهائي' });
        fireEvent.click(confirmBtn);
        expect(onConfirm).toHaveBeenCalled();
    });

    it('handles onCancel fallback when onClose is not explicitly provided', () => {
        const onConfirm = vi.fn();
        const onCancel = vi.fn();

        render(
            <ConfirmDialog
                isOpen={true}
                title="تعطيل العنصر"
                message="سيتم إيقاف الخدمة مؤقتاً"
                confirmText="تعطيل"
                cancelText="تراجع"
                variant="warning"
                onConfirm={onConfirm}
                onCancel={onCancel}
            />
        );

        const cancelBtn = screen.getByRole('button', { name: 'تراجع' });
        fireEvent.click(cancelBtn);
        expect(onCancel).toHaveBeenCalled();
    });

    it('does not render content when isOpen is false', () => {
        render(
            <ConfirmDialog
                isOpen={false}
                title="تأكيد"
                message="مخفي"
                onConfirm={vi.fn()}
                onClose={vi.fn()}
            />
        );

        expect(screen.queryByText('مخفي')).not.toBeInTheDocument();
    });
});

/**
 * Dentix confirmation dialog. Preserves the historical synchronous confirm API
 * while consuming canonical dialog and button primitives.
 */
import Modal from './Modal';
import Button from './Button';

export default function ConfirmDialog({
    isOpen,
    onClose,
    onCancel,
    onConfirm,
    title = 'تأكيد',
    message = 'هل أنت متأكد؟',
    confirmText = 'تأكيد',
    cancelText = 'إلغاء',
    variant = 'danger',
    isLoading = false,
}) {
    const handleClose = onClose || onCancel || (() => {});
    const confirmVariant = variant === 'danger' ? 'danger' : 'primary';

    return (
        <Modal isOpen={isOpen} onClose={handleClose} title={title} maxWidth="max-w-sm">
            <div className="space-y-5">
                <p className="text-type-body text-text-secondary">{message}</p>
                <div className="flex justify-end gap-3">
                    <Button variant="ghost" onClick={handleClose} disabled={isLoading}>
                        {cancelText}
                    </Button>
                    <Button
                        variant={confirmVariant}
                        isLoading={isLoading}
                        onClick={() => {
                            onConfirm?.();
                            handleClose();
                        }}
                    >
                        {confirmText}
                    </Button>
                </div>
            </div>
        </Modal>
    );
}

export { ConfirmDialog as DentixConfirmDialog };

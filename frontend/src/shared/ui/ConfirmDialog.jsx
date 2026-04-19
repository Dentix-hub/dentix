/**
 * ConfirmDialog Component
 * Reusable confirmation dialog.
 */
import Modal from './Modal';

export default function ConfirmDialog({
    isOpen,
    onClose,
    onConfirm,
    title = 'تأكيد',
    message = 'هل أنت متأكد؟',
    confirmText = 'تأكيد',
    cancelText = 'إلغاء',
    variant = 'danger' // 'danger' | 'warning' | 'info'
}) {
    const variants = {
        danger: 'bg-red-500 hover:bg-red-600',
        warning: 'bg-amber-500 hover:bg-amber-600',
        info: 'bg-blue-500 hover:bg-blue-600',
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={title} maxWidth="max-w-sm">
            <div className="space-y-4">
                <p className="text-slate-600">{message}</p>
                <div className="flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 hover:bg-slate-100 rounded-lg font-bold"
                    >
                        {cancelText}
                    </button>
                    <button
                        onClick={() => { onConfirm(); onClose(); }}
                        className={`px-6 py-2 text-white rounded-lg font-bold ${variants[variant]}`}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </Modal>
    );
}

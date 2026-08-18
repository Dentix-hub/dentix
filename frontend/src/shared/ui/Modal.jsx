/**
 * Compatibility wrapper for the historical Dentix Modal API.
 * Feature code can migrate incrementally to DentixDialog without changing
 * business logic or route semantics.
 */
import { useTranslation } from 'react-i18next';
import DentixDialog from './DentixDialog';

export default function Modal({
    isOpen,
    onClose,
    title,
    children,
    maxWidth,
    size = 'md',
    scrollable = true,
    className = '',
    closeLabel,
    closeOnOutside = true,
}) {
    const { t } = useTranslation();

    return (
        <DentixDialog
            open={isOpen}
            onOpenChange={(nextOpen) => {
                if (!nextOpen) onClose?.();
            }}
            title={title}
            maxWidth={maxWidth}
            size={size}
            scrollable={scrollable}
            className={className}
            closeLabel={closeLabel || t('common.close', 'Close')}
            closeOnOutside={closeOnOutside}
        >
            {children}
        </DentixDialog>
    );
}

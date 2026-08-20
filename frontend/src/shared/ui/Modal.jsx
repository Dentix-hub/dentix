/**
 * Compatibility wrapper for the historical Dentix Modal API.
 * Feature code can migrate incrementally to DentixDialog without changing
 * business logic or route semantics.
 *
 * On compact phones the historical modal defaults to the canonical bottom sheet
 * so long forms and pickers remain inside the dynamic viewport. Consumers that
 * genuinely require a centered compact dialog can opt out with mobileVariant="dialog".
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import DentixDialog from './DentixDialog';
import DentixBottomSheet from './DentixBottomSheet';

function useCompactViewport() {
    const getMatch = () => typeof window !== 'undefined' && window.matchMedia('(max-width: 639px)').matches;
    const [isCompact, setIsCompact] = useState(getMatch);

    useEffect(() => {
        if (typeof window === 'undefined') return undefined;
        const media = window.matchMedia('(max-width: 639px)');
        const onChange = (event) => setIsCompact(event.matches);
        setIsCompact(media.matches);
        media.addEventListener?.('change', onChange);
        return () => media.removeEventListener?.('change', onChange);
    }, []);

    return isCompact;
}

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
    mobileVariant = 'sheet',
}) {
    const { t } = useTranslation();
    const isCompact = useCompactViewport();
    const handleOpenChange = (nextOpen) => {
        if (!nextOpen) onClose?.();
    };
    const resolvedCloseLabel = closeLabel || t('common.close', 'Close');

    if (isCompact && mobileVariant !== 'dialog') {
        return (
            <DentixBottomSheet
                open={isOpen}
                onOpenChange={handleOpenChange}
                title={title}
                className={className}
                closeLabel={resolvedCloseLabel}
                closeOnOutside={closeOnOutside}
            >
                {children}
            </DentixBottomSheet>
        );
    }

    return (
        <DentixDialog
            open={isOpen}
            onOpenChange={handleOpenChange}
            title={title}
            maxWidth={maxWidth}
            size={size}
            scrollable={scrollable}
            className={className}
            closeLabel={resolvedCloseLabel}
            closeOnOutside={closeOnOutside}
        >
            {children}
        </DentixDialog>
    );
}

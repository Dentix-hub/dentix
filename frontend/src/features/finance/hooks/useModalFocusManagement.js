import { useEffect, useRef } from 'react';

const FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
].join(',');

/**
 * Shared focus-management contract for Finance dialogs/drawers.
 * - moves focus inside on open
 * - traps Tab/Shift+Tab
 * - closes on Escape
 * - restores focus to the trigger on close
 */
export default function useModalFocusManagement(isOpen, onClose) {
    const containerRef = useRef(null);
    const previousFocusRef = useRef(null);
    const onCloseRef = useRef(onClose);

    useEffect(() => {
        onCloseRef.current = onClose;
    }, [onClose]);

    useEffect(() => {
        if (!isOpen) return undefined;

        const container = containerRef.current;
        if (!container) return undefined;

        previousFocusRef.current = document.activeElement;

        const getFocusable = () => Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR))
            .filter((node) => !node.hasAttribute('disabled') && node.getAttribute('aria-hidden') !== 'true');

        const focusable = getFocusable();
        (focusable[0] || container).focus();

        const handleKeyDown = (event) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                onCloseRef.current?.();
                return;
            }

            if (event.key !== 'Tab') return;

            const currentFocusable = getFocusable();
            if (currentFocusable.length === 0) {
                event.preventDefault();
                container.focus();
                return;
            }

            const first = currentFocusable[0];
            const last = currentFocusable[currentFocusable.length - 1];

            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        };

        document.addEventListener('keydown', handleKeyDown);

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            const previous = previousFocusRef.current;
            if (previous && typeof previous.focus === 'function' && document.contains(previous)) {
                previous.focus();
            }
        };
    }, [isOpen]);

    return containerRef;
}

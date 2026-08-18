import { useRef } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';

const SIZE_MAP = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
    '5xl': 'max-w-5xl',
};

/**
 * Canonical Dentix blocking dialog.
 *
 * Radix owns focus trapping, Escape dismissal, nested-layer ordering and scroll
 * locking. Dentix owns the public API, semantic tokens and visual contract.
 */
export default function DentixDialog({
    open,
    onOpenChange,
    title,
    children,
    size = 'md',
    maxWidth,
    scrollable = true,
    className = '',
    closeLabel = 'Close dialog',
    closeOnOutside = true,
}) {
    const previouslyFocusedRef = useRef(null);
    const wasOpenRef = useRef(false);
    const resolvedMaxWidth = maxWidth || SIZE_MAP[size] || SIZE_MAP.md;

    // Capture the invoking element before Radix mounts the focus scope. Capturing
    // in onOpenAutoFocus is too late in a real browser because focus may already
    // have moved into the portal by then.
    if (open && !wasOpenRef.current && typeof document !== 'undefined') {
        previouslyFocusedRef.current = document.activeElement;
    }
    wasOpenRef.current = open;

    return (
        <DialogPrimitive.Root open={open} onOpenChange={onOpenChange} modal>
            <DialogPrimitive.Portal>
                <DialogPrimitive.Overlay
                    data-dentix-overlay="backdrop"
                    className="fixed inset-0 z-modal bg-backdrop backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in data-[state=closed]:fade-out duration-standard motion-reduce:animate-none"
                />
                <DialogPrimitive.Content
                    data-dentix-overlay="dialog"
                    aria-describedby={undefined}
                    onPointerDownOutside={(event) => {
                        if (!closeOnOutside) event.preventDefault();
                    }}
                    onCloseAutoFocus={(event) => {
                        event.preventDefault();
                        const target = previouslyFocusedRef.current;
                        if (target && typeof target.focus === 'function' && document.contains(target)) {
                            target.focus();
                        }
                    }}
                    className={`
                        fixed left-1/2 top-1/2 z-modal w-[calc(100%-2rem)] ${resolvedMaxWidth}
                        -translate-x-1/2 -translate-y-1/2 border border-border bg-surface-elevated
                        text-text-primary shadow-high rounded-overlay
                        max-h-[calc(100dvh-2rem)]
                        data-[state=open]:animate-in data-[state=closed]:animate-out
                        data-[state=open]:fade-in data-[state=closed]:fade-out
                        data-[state=open]:zoom-in-95 data-[state=closed]:zoom-out-95
                        duration-emphasized motion-reduce:animate-none
                        ${scrollable ? 'overflow-y-auto' : 'overflow-hidden flex flex-col'}
                        ${className}
                    `}
                >
                    <div className="sticky top-0 z-sticky flex items-center justify-between gap-4 border-b border-border bg-surface-elevated px-4 py-3 md:px-6">
                        <DialogPrimitive.Title className={title ? 'text-type-section text-text-primary' : 'sr-only'}>
                            {title || 'Dialog'}
                        </DialogPrimitive.Title>
                        <DialogPrimitive.Close asChild>
                            <button
                                type="button"
                                aria-label={closeLabel}
                                className="ms-auto inline-flex h-9 w-9 items-center justify-center rounded-control text-text-muted transition-colors duration-fast hover:bg-surface-subtle hover:text-text-primary focus-visible:ring-focus"
                            >
                                <X size={20} aria-hidden="true" />
                            </button>
                        </DialogPrimitive.Close>
                    </div>
                    <div className={`relative px-4 py-4 md:px-6 md:py-5 ${scrollable ? '' : 'min-h-0 flex-1 overflow-y-auto'}`}>
                        {children}
                    </div>
                </DialogPrimitive.Content>
            </DialogPrimitive.Portal>
        </DialogPrimitive.Root>
    );
}

import { useRef } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';

const WIDTH_MAP = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
};

/**
 * Canonical Dentix side drawer.
 * Uses logical `end` positioning so the same primitive works in RTL and LTR.
 */
export default function DentixDrawer({
    open,
    onOpenChange,
    title,
    children,
    size = 'md',
    className = '',
    closeLabel = 'Close drawer',
    closeOnOutside = true,
}) {
    const previouslyFocusedRef = useRef(null);
    const wasOpenRef = useRef(false);
    const width = WIDTH_MAP[size] || WIDTH_MAP.md;

    if (open && !wasOpenRef.current && typeof document !== 'undefined') {
        previouslyFocusedRef.current = document.activeElement;
    }
    wasOpenRef.current = open;

    return (
        <DialogPrimitive.Root open={open} onOpenChange={onOpenChange} modal>
            <DialogPrimitive.Portal>
                <DialogPrimitive.Overlay
                    data-dentix-overlay="backdrop"
                    className="fixed inset-0 z-drawer bg-backdrop backdrop-blur-[2px] motion-reduce:backdrop-blur-none"
                />
                <DialogPrimitive.Content
                    data-dentix-overlay="drawer"
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
                    className={`fixed inset-y-0 end-0 z-drawer flex w-full ${width} flex-col border-s border-border bg-surface-elevated text-text-primary shadow-high ${className}`}
                >
                    <div className="flex items-center gap-4 border-b border-border px-4 py-3 md:px-6">
                        <DialogPrimitive.Title className="text-type-section text-text-primary">
                            {title}
                        </DialogPrimitive.Title>
                        <DialogPrimitive.Close asChild>
                            <button
                                type="button"
                                aria-label={closeLabel}
                                className="ms-auto inline-flex h-9 w-9 items-center justify-center rounded-control text-text-muted transition-colors duration-fast hover:bg-surface-subtle hover:text-text-primary"
                            >
                                <X size={20} aria-hidden="true" />
                            </button>
                        </DialogPrimitive.Close>
                    </div>
                    <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 md:px-6 md:py-5">
                        {children}
                    </div>
                </DialogPrimitive.Content>
            </DialogPrimitive.Portal>
        </DialogPrimitive.Root>
    );
}

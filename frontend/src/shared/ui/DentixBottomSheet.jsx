import { useRef } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';

/**
 * Canonical Dentix bottom sheet for compact/mobile task presentation.
 * Product workflows decide when a sheet is appropriate; this primitive does not
 * change route or business semantics by itself.
 */
export default function DentixBottomSheet({
    open,
    onOpenChange,
    title,
    children,
    className = '',
    closeLabel = 'Close sheet',
    closeOnOutside = true,
}) {
    const previouslyFocusedRef = useRef(null);
    const wasOpenRef = useRef(false);

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
                    data-dentix-overlay="bottom-sheet"
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
                    className={`fixed inset-x-0 bottom-0 z-drawer mx-auto flex max-h-[90dvh] w-full max-w-3xl flex-col rounded-t-overlay border border-b-0 border-border bg-surface-elevated text-text-primary shadow-high ${className}`}
                >
                    <div aria-hidden="true" className="mx-auto mt-2 h-1 w-10 rounded-pill bg-border-strong" />
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
                    <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] md:px-6 md:py-5">
                        {children}
                    </div>
                </DialogPrimitive.Content>
            </DialogPrimitive.Portal>
        </DialogPrimitive.Root>
    );
}

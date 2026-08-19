import { Fragment } from 'react';
import { Popover, PopoverButton, PopoverPanel } from '@headlessui/react';

/**
 * Canonical Dentix non-blocking anchored popover.
 *
 * Headless UI owns keyboard dismissal, outside click, focus return, positioning
 * and portal behavior. Dentix owns the public API and semantic surface contract.
 *
 * `children` may be a render function receiving `{ close }` when a workflow
 * needs to dismiss the popover after an explicit action (for example selecting
 * a date preset).
 */
export default function DentixPopover({
    trigger,
    children,
    anchor = 'bottom end',
    gap = 8,
    offset = 0,
    padding = 8,
    className = '',
    rootClassName = '',
    focus = false,
}) {
    const anchorConfig = typeof anchor === 'string'
        ? { to: anchor, gap, offset, padding }
        : { gap, offset, padding, ...anchor };

    return (
        <Popover className={`relative ${rootClassName}`}>
            {({ close }) => (
                <>
                    <PopoverButton as={Fragment}>{trigger}</PopoverButton>
                    <PopoverPanel
                        data-dentix-overlay="popover"
                        anchor={anchorConfig}
                        focus={focus}
                        transition
                        className={`z-popover rounded-overlay border border-border bg-surface-elevated p-2 text-text-primary shadow-medium outline-none transition duration-standard data-[closed]:scale-95 data-[closed]:opacity-0 motion-reduce:transition-none ${className}`}
                    >
                        {typeof children === 'function' ? children({ close }) : children}
                    </PopoverPanel>
                </>
            )}
        </Popover>
    );
}

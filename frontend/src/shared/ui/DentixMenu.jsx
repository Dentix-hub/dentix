import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

/** Canonical Dentix action menu wrapper. */
export default function DentixMenu({ trigger, children, align = 'end', sideOffset = 6, className = '' }) {
    return (
        <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>{trigger}</DropdownMenu.Trigger>
            <DropdownMenu.Portal>
                <DropdownMenu.Content
                    align={align}
                    sideOffset={sideOffset}
                    className={`z-dropdown min-w-44 rounded-overlay border border-border bg-surface-elevated p-1 text-text-primary shadow-medium outline-none ${className}`}
                >
                    {children}
                </DropdownMenu.Content>
            </DropdownMenu.Portal>
        </DropdownMenu.Root>
    );
}

export function DentixMenuItem({ children, className = '', ...props }) {
    return (
        <DropdownMenu.Item
            className={`flex cursor-default select-none items-center gap-2 rounded-control px-3 py-2 text-type-body outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-surface-subtle ${className}`}
            {...props}
        >
            {children}
        </DropdownMenu.Item>
    );
}

export function DentixMenuSeparator({ className = '' }) {
    return <DropdownMenu.Separator className={`my-1 h-px bg-border ${className}`} />;
}

import { useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DentixDialog from './DentixDialog';
import DentixDrawer from './DentixDrawer';
import DentixBottomSheet from './DentixBottomSheet';

function NestedDialogHarness() {
    const [parentOpen, setParentOpen] = useState(false);
    const [childOpen, setChildOpen] = useState(false);

    return (
        <>
            <button type="button" onClick={() => setParentOpen(true)}>Open parent</button>
            <DentixDialog open={parentOpen} onOpenChange={setParentOpen} title="Parent dialog">
                <button type="button" onClick={() => setChildOpen(true)}>Open child</button>
                <DentixDialog open={childOpen} onOpenChange={setChildOpen} title="Child dialog">
                    <button type="button">Child action</button>
                </DentixDialog>
            </DentixDialog>
        </>
    );
}

function DrawerHarness({ kind = 'drawer' }) {
    const [open, setOpen] = useState(false);
    const Overlay = kind === 'sheet' ? DentixBottomSheet : DentixDrawer;
    return (
        <>
            <button type="button" onClick={() => setOpen(true)}>Open {kind}</button>
            <Overlay open={open} onOpenChange={setOpen} title={`${kind} title`}>
                <button type="button">Inside {kind}</button>
            </Overlay>
        </>
    );
}

describe('Dentix overlay primitives', () => {
    it('dismisses only the topmost nested dialog on Escape and preserves the parent lock', async () => {
        render(<NestedDialogHarness />);
        fireEvent.click(screen.getByRole('button', { name: 'Open parent' }));
        fireEvent.click(await screen.findByRole('button', { name: 'Open child' }));

        // Radix intentionally aria-hides the parent while a nested modal is topmost,
        // so accessibility-role queries see only the child. Inspect the canonical
        // overlay stack itself and the Radix scroll-lock reference count here.
        await waitFor(() => {
            expect(document.querySelectorAll('[data-dentix-overlay="dialog"]')).toHaveLength(2);
            expect(document.body).toHaveAttribute('data-scroll-locked', '2');
        });

        const child = screen.getByRole('dialog', { name: 'Child dialog' });
        fireEvent.keyDown(child, { key: 'Escape' });

        await waitFor(() => {
            expect(screen.queryByRole('dialog', { name: 'Child dialog' })).not.toBeInTheDocument();
            expect(document.querySelectorAll('[data-dentix-overlay="dialog"]')).toHaveLength(1);
            expect(document.body).toHaveAttribute('data-scroll-locked', '1');
        });
        expect(screen.getByRole('dialog', { name: 'Parent dialog' })).toBeInTheDocument();
    });

    it('renders the drawer on the logical end edge and returns focus on close', async () => {
        render(<DrawerHarness />);
        const trigger = screen.getByRole('button', { name: 'Open drawer' });
        trigger.focus();
        fireEvent.click(trigger);

        const dialog = await screen.findByRole('dialog', { name: 'drawer title' });
        expect(dialog.className).toContain('end-0');
        expect(dialog.className).toContain('bg-surface-elevated');

        fireEvent.keyDown(dialog, { key: 'Escape' });
        await waitFor(() => expect(screen.queryByRole('dialog', { name: 'drawer title' })).not.toBeInTheDocument());
        expect(trigger).toHaveFocus();
    });

    it('renders an opaque bottom sheet and closes with Escape', async () => {
        render(<DrawerHarness kind="sheet" />);
        fireEvent.click(screen.getByRole('button', { name: 'Open sheet' }));
        const dialog = await screen.findByRole('dialog', { name: 'sheet title' });
        expect(dialog).toHaveAttribute('data-dentix-overlay', 'bottom-sheet');
        expect(dialog.className).toContain('bg-surface-elevated');

        fireEvent.keyDown(dialog, { key: 'Escape' });
        await waitFor(() => expect(screen.queryByRole('dialog', { name: 'sheet title' })).not.toBeInTheDocument());
    });
});

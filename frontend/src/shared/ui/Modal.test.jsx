import { useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Modal from './Modal';

function ModalHarness() {
    const [open, setOpen] = useState(false);
    return (
        <>
            <button type="button" onClick={() => setOpen(true)}>Open modal</button>
            <Modal isOpen={open} onClose={() => setOpen(false)} title="Test Modal">
                <button type="button">Inner action</button>
            </Modal>
        </>
    );
}

describe('Modal compatibility wrapper', () => {
    it('does not render when not open', () => {
        render(<Modal isOpen={false} onClose={() => {}} title="Test Modal">Content</Modal>);
        expect(screen.queryByText('Test Modal')).not.toBeInTheDocument();
    });

    it('renders on the canonical opaque Dentix dialog surface', () => {
        render(<Modal isOpen onClose={() => {}} title="Test Modal"><div>Modal Content</div></Modal>);
        const dialog = screen.getByRole('dialog');
        expect(screen.getByText('Modal Content')).toBeInTheDocument();
        expect(dialog.className).toContain('bg-surface-elevated');
        expect(dialog.className).toContain('z-modal');
        expect(dialog.className).not.toMatch(/bg-(?:white|slate-\d+)\/\d+/);
    });

    it('calls onClose when the canonical close button is clicked', () => {
        const handleClose = vi.fn();
        render(<Modal isOpen onClose={handleClose} title="Test Modal">Content</Modal>);
        fireEvent.click(screen.getByRole('button', { name: /Close|إغلاق/i }));
        expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when Escape is pressed', () => {
        const handleClose = vi.fn();
        render(<Modal isOpen onClose={handleClose} title="Test Modal">Content</Modal>);
        fireEvent.keyDown(document, { key: 'Escape' });
        expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('returns focus to the invoking control after close', async () => {
        render(<ModalHarness />);
        const trigger = screen.getByRole('button', { name: 'Open modal' });
        trigger.focus();
        fireEvent.click(trigger);

        await screen.findByRole('dialog');
        fireEvent.click(screen.getByRole('button', { name: /Close|إغلاق/i }));

        await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
        expect(trigger).toHaveFocus();
    });

    it('preserves the pre-existing body overflow value after close', async () => {
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'clip';
        try {
            render(<ModalHarness />);
            fireEvent.click(screen.getByRole('button', { name: 'Open modal' }));
            await screen.findByRole('dialog');
            fireEvent.click(screen.getByRole('button', { name: /Close|إغلاق/i }));
            await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
            expect(document.body.style.overflow).toBe('clip');
        } finally {
            document.body.style.overflow = previousOverflow;
        }
    });
});

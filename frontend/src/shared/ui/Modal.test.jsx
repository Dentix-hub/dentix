
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Modal from './Modal';

// Mock X icon
vi.mock('lucide-react', () => ({
    X: () => <svg data-testid="close-icon" />
}));

describe('Modal Component', () => {
    it('does not render when not open', () => {
        render(<Modal isOpen={false} onClose={() => { }} title="Test Modal">Content</Modal>);
        expect(screen.queryByText('Test Modal')).not.toBeInTheDocument();
    });

    it('renders when open', () => {
        render(<Modal isOpen={true} onClose={() => { }} title="Test Modal">
            <div>Modal Content</div>
        </Modal>);
        expect(screen.getByText('Test Modal')).toBeInTheDocument();
        expect(screen.getByText('Modal Content')).toBeInTheDocument();
    });

    it('calls onClose when close button is clicked', () => {
        const handleClose = vi.fn();
        render(<Modal isOpen={true} onClose={handleClose} title="Test Modal">Content</Modal>);

        fireEvent.click(screen.getByRole('button'));
        expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when backdrop is clicked', () => {
        const handleClose = vi.fn();
        const { container } = render(<Modal isOpen={true} onClose={handleClose} title="Test Modal">Content</Modal>);

        // The first div is the fixed backdrop
        fireEvent.click(container.firstChild);
        expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('does NOT call onClose when modal content is clicked', () => {
        const handleClose = vi.fn();
        render(<Modal isOpen={true} onClose={handleClose} title="Test Modal">
            <div data-testid="modal-content">Content</div>
        </Modal>);

        fireEvent.click(screen.getByTestId('modal-content'));
        expect(handleClose).not.toHaveBeenCalled();
    });

    it('calls onClose when Escape key is pressed', () => {
        const handleClose = vi.fn();
        render(<Modal isOpen={true} onClose={handleClose} title="Test Modal">Content</Modal>);

        fireEvent.keyDown(document, { key: 'Escape' });
        expect(handleClose).toHaveBeenCalledTimes(1);
    });
});


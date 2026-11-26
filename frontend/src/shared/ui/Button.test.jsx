import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import Button from './Button';

describe('Dentix shared Button public contract', () => {
    it('renders children with default type="button"', () => {
        render(<Button>Save Patient</Button>);
        const button = screen.getByRole('button', { name: 'Save Patient' });
        expect(button).toBeInTheDocument();
        expect(button).toHaveAttribute('type', 'button');
        expect(button).not.toBeDisabled();
        expect(button).not.toHaveAttribute('aria-busy');
    });

    it('disables button and sets aria-busy="true" when isLoading is true', () => {
        render(<Button isLoading>Saving...</Button>);
        const button = screen.getByRole('button', { name: 'Saving...' });
        expect(button).toBeDisabled();
        expect(button).toHaveAttribute('aria-busy', 'true');
    });

    it('respects explicit disabled and forwards className and standard DOM props', () => {
        render(
            <Button
                disabled
                className="custom-action-class"
                data-testid="custom-button-id"
                aria-label="Custom Action Button"
            >
                Custom Action
            </Button>,
        );
        const button = screen.getByTestId('custom-button-id');
        expect(button).toBeDisabled();
        expect(button).toHaveClass('custom-action-class');
        expect(button).toHaveAttribute('aria-label', 'Custom Action Button');
    });

    it('renders icon when passed as a component type', () => {
        const CustomIcon = (props) => <svg data-testid="custom-icon-component" {...props} />;
        render(<Button icon={CustomIcon}>Add Record</Button>);
        const icon = screen.getByTestId('custom-icon-component');
        expect(icon).toBeInTheDocument();
        expect(icon).toHaveAttribute('aria-hidden', 'true');
        expect(icon).toHaveClass('me-2');
        expect(screen.getByRole('button', { name: 'Add Record' })).toBeInTheDocument();
    });

    it('renders icon when passed as an already-rendered React element', () => {
        const iconElement = <span data-testid="custom-icon-element">★</span>;
        render(<Button icon={iconElement}>Favorite</Button>);
        const icon = screen.getByTestId('custom-icon-element');
        expect(icon).toBeInTheDocument();
        const iconWrapper = icon.parentElement;
        expect(iconWrapper).toHaveAttribute('aria-hidden', 'true');
        expect(iconWrapper).toHaveClass('me-2');
        expect(screen.getByRole('button', { name: 'Favorite' })).toBeInTheDocument();
    });

    it('uses high-contrast #0369A1 primary filled styling with accessible hover and focus ring', () => {
        render(<Button variant="primary">Primary Action</Button>);
        const button = screen.getByRole('button', { name: 'Primary Action' });
        expect(button).toHaveClass(
            'bg-primary-700',
            'text-white',
            'hover:bg-primary-800',
            'focus-visible:ring-2',
            'focus-visible:ring-primary-700',
        );
    });

    it('uses high-contrast #B91C1C danger filled styling with accessible hover and focus ring', () => {
        render(<Button variant="danger">Delete Record</Button>);
        const button = screen.getByRole('button', { name: 'Delete Record' });
        expect(button).toHaveClass(
            'bg-red-700',
            'text-white',
            'hover:bg-red-800',
            'focus-visible:ring-2',
            'focus-visible:ring-red-700',
        );
    });

    it('uses high-contrast light and dark classes on outline and ghost variants', () => {
        render(
            <>
                <Button variant="outline">Outline Action</Button>
                <Button variant="ghost">Ghost Action</Button>
            </>,
        );
        const outlineBtn = screen.getByRole('button', { name: 'Outline Action' });
        const ghostBtn = screen.getByRole('button', { name: 'Ghost Action' });
        expect(outlineBtn).toHaveClass('text-primary-700', 'dark:text-primary-300', 'focus-visible:ring-2');
        expect(ghostBtn).toHaveClass('hover:text-primary-700', 'dark:hover:text-primary-300', 'focus-visible:ring-2');
    });
});

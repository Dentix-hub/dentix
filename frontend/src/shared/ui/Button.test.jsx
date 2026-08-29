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
});

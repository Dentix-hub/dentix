
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import StatCard from './StatCard';

// Mock Icon component
const MockIcon = (props) => <svg data-testid="mock-icon" {...props} />;

describe('StatCard Component', () => {
    it('renders title and value', () => {
        render(<StatCard icon={MockIcon} title="Total Patients" value="1,234" />);
        expect(screen.getByText('Total Patients')).toBeInTheDocument();
        expect(screen.getByText('1,234')).toBeInTheDocument();
    });

    it('renders label instead of title if provided', () => {
        render(<StatCard icon={MockIcon} label="Active Users" value="50" />);
        expect(screen.getByText('Active Users')).toBeInTheDocument();
    });

    it('renders subtext when provided', () => {
        render(<StatCard icon={MockIcon} title="Sales" value="$500" subtext="+10% increase" />);
        expect(screen.getByText('+10% increase')).toBeInTheDocument();
    });

    it('calls onClick when clicked', () => {
        const handleClick = vi.fn();
        render(<StatCard icon={MockIcon} title="Click Me" value="0" onClick={handleClick} />);

        // Find the clickable container (the parent div)
        // Since StatCard doesn't have a role/testId on root, we click the text's parent or similar
        // Or we can add data-testid to the component for better testing, but using text is fine for now
        fireEvent.click(screen.getByText('Click Me').closest('div').parentElement.parentElement);

        expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('renders the icon', () => {
        render(<StatCard icon={MockIcon} title="Icon Test" value="0" />);
        expect(screen.getByTestId('mock-icon')).toBeInTheDocument();
    });
});


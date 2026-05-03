
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

// Simple component for testing
const TestComponent = () => <div>Hello, World!</div>;

describe('Frontend Smoke Test', () => {
    it('renders heading', () => {
        render(<TestComponent />);
        expect(screen.getByText('Hello, World!')).toBeInTheDocument();
    });
});

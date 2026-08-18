import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import Input from './Input';
import Select from './Select';

describe('Dentix form primitive contract', () => {
    it('links Input label, help and error semantics', () => {
        const { rerender } = render(<Input label="Patient name" help="Use the legal name" required />);
        const input = screen.getByRole('textbox', { name: 'Patient name' });
        expect(input).toBeRequired();
        expect(input).toHaveAccessibleDescription('Use the legal name');

        rerender(<Input label="Patient name" error="Name is required" required />);
        expect(screen.getByRole('textbox', { name: 'Patient name' })).toHaveAttribute('aria-invalid', 'true');
        expect(screen.getByRole('alert')).toHaveTextContent('Name is required');
    });

    it('links Select label and validation semantics', () => {
        render(
            <Select
                label="Doctor"
                value=""
                onChange={() => {}}
                required
                error="Choose a doctor"
                options={[{ value: '1', label: 'Dr A' }]}
            />,
        );
        const select = screen.getByRole('combobox', { name: 'Doctor' });
        expect(select).toBeRequired();
        expect(select).toHaveAttribute('aria-invalid', 'true');
        expect(select).toHaveAccessibleDescription('Choose a doctor');
    });
});

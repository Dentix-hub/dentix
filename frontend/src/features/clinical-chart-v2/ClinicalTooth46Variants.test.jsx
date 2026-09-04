import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalTooth46Variants from './ClinicalTooth46Variants';

describe('ClinicalTooth46Variants approval page', () => {
    it('renders the healthy tooth and eight dedicated clinical variants', () => {
        render(<ClinicalTooth46Variants />);

        expect(screen.getByTestId('tooth-46-variant-grid').children).toHaveLength(9);
        expect(screen.getByText('9 أصول شفافة')).toBeInTheDocument();
        expect(screen.getByTestId('healthy-tooth-preview').getAttribute('src')).toMatch(/tooth-46-healthy\.png$/);
    });

    it('changes the large preview through accessible variant controls', () => {
        render(<ClinicalTooth46Variants />);

        const caries = screen.getByRole('button', { name: 'عرض تسوس إطباقي' });
        const rct = screen.getByRole('button', { name: 'عرض علاج عصب' });
        expect(caries).toHaveAttribute('aria-pressed', 'true');

        fireEvent.click(rct);

        expect(rct).toHaveAttribute('aria-pressed', 'true');
        expect(caries).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId('selected-variant-preview').getAttribute('src')).toMatch(/tooth-46-rct-v1\.png$/);
        expect(screen.getByText(/حجرة لب وقناتان/)).toBeInTheDocument();
    });
});

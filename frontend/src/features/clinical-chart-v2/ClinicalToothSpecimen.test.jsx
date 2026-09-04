import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalToothSpecimen from './ClinicalToothSpecimen';

describe('ClinicalToothSpecimen approved strategy C', () => {
    it('renders the locked anatomy and every approved procedure', () => {
        render(<ClinicalToothSpecimen />);

        expect(screen.getByTestId('anatomy-grid').children).toHaveLength(8);
        expect(screen.getByTestId('procedure-grid').children).toHaveLength(9);
        expect(screen.getByText(/التشريح المقفول/)).toBeInTheDocument();
    });

    it('uses the approved anatomy and procedure artwork as separate renderer inputs', () => {
        render(<ClinicalToothSpecimen />);

        const healthy = screen.getByTestId('healthy-preview');
        const procedure = screen.getByTestId('procedure-preview');

        expect(healthy.getAttribute('data-artwork-src')).toMatch(/approved-tooth-anatomy-reference\.png$/);
        expect(procedure.getAttribute('data-artwork-src')).toMatch(/procedure-effects-approval-v1\.png$/);
        expect(procedure).toHaveAttribute('data-source-crop', '145,0,255,260');
    });

    it('changes the large clinical preview through accessible procedure controls', () => {
        render(<ClinicalToothSpecimen />);

        const caries = screen.getByRole('button', { name: /تسوس/ });
        const rct = screen.getByRole('button', { name: /علاج عصب/ });

        expect(caries).toHaveAttribute('aria-pressed', 'true');
        fireEvent.click(rct);
        expect(rct).toHaveAttribute('aria-pressed', 'true');
        expect(caries).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId('procedure-preview')).toHaveAttribute('data-source-crop', '140,316,270,270');
        expect(screen.getByText(/حجرة اللب والقنوات الفعلية/)).toBeInTheDocument();
    });

    it('keeps the caries contract on the clinical crown', () => {
        render(<ClinicalToothSpecimen />);

        expect(screen.getByText(/ولا تمتد إلى الجذر/)).toBeInTheDocument();
    });
});

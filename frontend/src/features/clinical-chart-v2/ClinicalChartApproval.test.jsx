import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalChartApproval from './ClinicalChartApproval';

describe('ClinicalChartApproval full-mouth specimen', () => {
    it('renders all 32 FDI teeth as accessible controls', () => {
        render(<ClinicalChartApproval />);

        expect(screen.getAllByRole('button', { name: /اختيار السن/ })).toHaveLength(32);
        expect(document.querySelectorAll('[data-arch-row]')).toHaveLength(2);
        expect(document.querySelectorAll('[data-arch-row]')[0].querySelectorAll('[data-fdi]')).toHaveLength(16);
        expect(document.querySelectorAll('[data-arch-row]')[1].querySelectorAll('[data-fdi]')).toHaveLength(16);
        expect(screen.getByRole('button', { name: 'اختيار السن 46' })).toHaveAttribute('aria-pressed', 'true');
    });

    it('renders dedicated transparent healthy assets without generic procedure artwork', () => {
        render(<ClinicalChartApproval />);

        const tooth14 = screen.getByTestId('tooth-artwork-14');
        expect(tooth14.getAttribute('data-artwork-src')).toMatch(/adult-fdi-clean\/tooth-14-healthy\.png$/);
        expect(tooth14.closest('[data-procedure]')).toHaveAttribute('data-procedure', 'healthy');
        expect(tooth14.closest('[data-asset-status]')).toHaveAttribute('data-asset-status', 'ready');
    });

    it('updates the selected tooth summary', () => {
        render(<ClinicalChartApproval />);

        fireEvent.click(screen.getByRole('button', { name: 'اختيار السن 36' }));

        expect(screen.getByRole('button', { name: 'اختيار السن 36' })).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByRole('button', { name: 'سليم للسن 36' })).toHaveAttribute('aria-pressed', 'true');
    });

    it('never substitutes the generic procedure board for a healthy tooth asset', () => {
        render(<ClinicalChartApproval />);

        const compositeTooth = screen.getByTestId('tooth-artwork-24');
        expect(compositeTooth.getAttribute('data-artwork-src')).toMatch(/adult-fdi-clean\/tooth-24-healthy\.png$/);
        expect(compositeTooth.getAttribute('data-artwork-src')).not.toMatch(/procedure-effects-approval/);
    });

    it('renders and switches exact dedicated FDI 46 variants inside the full chart', () => {
        render(<ClinicalChartApproval />);

        const tooth46 = screen.getByTestId('tooth-artwork-46');
        expect(tooth46).toHaveAttribute('data-renderer', 'programmatic');
        expect(tooth46).toHaveAttribute('data-effect', 'caries');
        expect(screen.getByTestId('programmatic-caries')).toBeInTheDocument();
        expect(tooth46.closest('[data-asset-status]')).toHaveAttribute('data-asset-status', 'ready');

        fireEvent.click(screen.getByRole('button', { name: 'علاج عصب للسن 46' }));

        expect(screen.getByTestId('tooth-artwork-46')).toHaveAttribute('data-effect', 'rct');
        expect(screen.getByTestId('programmatic-rct')).toBeInTheDocument();
    });

    it.each([
        ['حشو تجميلي', 'composite'],
        ['حشو أملغم', 'amalgam'],
        ['تاج', 'crown'],
        ['زرعة', 'implant'],
        ['سن مفقود', 'missing'],
        ['كسر بالتاج', 'fracture'],
    ])('renders the %s state as a programmatic layer', (label, effect) => {
        render(<ClinicalChartApproval />);
        fireEvent.click(screen.getByRole('button', { name: `${label} للسن 46` }));

        expect(screen.getByTestId('tooth-artwork-46')).toHaveAttribute('data-renderer', 'programmatic');
        expect(screen.getByTestId('tooth-artwork-46')).toHaveAttribute('data-effect', effect);
        expect(screen.getByTestId(`programmatic-${effect}`)).toBeInTheDocument();
    });

    it('fails closed for teeth without dedicated clinical variants', () => {
        render(<ClinicalChartApproval />);
        fireEvent.click(screen.getByRole('button', { name: 'اختيار السن 36' }));

        const picker = screen.getByTestId('clinical-state-picker');
        expect(within(picker).getAllByRole('button')).toHaveLength(9);
        expect(within(picker).getByRole('button', { name: 'سليم للسن 36' })).toBeEnabled();
        expect(within(picker).getAllByRole('button').filter((button) => button.disabled)).toHaveLength(8);

        const tooth36 = screen.getByTestId('tooth-artwork-36');
        expect(tooth36.getAttribute('data-artwork-src')).toMatch(/adult-fdi-clean\/tooth-36-healthy\.png$/);
    });
});

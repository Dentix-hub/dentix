import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';

describe('ClinicalChartWorkspace scaffold', () => {
    it('renders the existing Dentix chart unchanged instead of a replacement specimen', () => {
        render(<ClinicalChartWorkspace />);

        expect(screen.getByTestId('clinical-chart-workspace')).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /مخطط الأسنان \(بالغين\)/ })).toBeInTheDocument();
        expect(screen.getAllByRole('button')).toHaveLength(160);
        expect(document.querySelectorAll('[data-layer="roots"]')).toHaveLength(32);
        expect(document.querySelectorAll('[data-layer="surfaces"]')).toHaveLength(32);
        expect(screen.queryByText('Crown geometry parity')).not.toBeInTheDocument();
        expect(screen.queryByText('Root anatomy families')).not.toBeInTheDocument();
    });

    it('toggles the selected surface in the isolated demo workspace', () => {
        render(<ClinicalChartWorkspace />);
        const surface = screen.getByRole('button', { name: 'Tooth UR1 — Mesial (M)' });

        expect(surface).toHaveAttribute('aria-pressed', 'false');
        fireEvent.click(surface);
        expect(surface).toHaveAttribute('aria-pressed', 'true');
        fireEvent.click(surface);
        expect(surface).toHaveAttribute('aria-pressed', 'false');
    });
});

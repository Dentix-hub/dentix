import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';

describe('ClinicalChartWorkspace scaffold', () => {
    it('renders the existing Dentix chart unchanged instead of a replacement specimen', () => {
        render(<ClinicalChartWorkspace />);

        expect(screen.getByTestId('clinical-chart-workspace')).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /مخطط الأسنان \(بالغين\)/ })).toBeInTheDocument();
        expect(screen.getAllByRole('button')).toHaveLength(32);
        expect(screen.queryByText('Crown geometry parity')).not.toBeInTheDocument();
        expect(screen.queryByText('Root anatomy families')).not.toBeInTheDocument();
    });
});

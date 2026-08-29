import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';

describe('ClinicalChartWorkspace scaffold', () => {
    it('renders the isolated chart workspace without crashing', () => {
        render(<ClinicalChartWorkspace />);

        expect(screen.getByTestId('clinical-chart-workspace')).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'مخطط الأسنان' })).toBeInTheDocument();
        expect(screen.getByTestId('source-crown')).toBeInTheDocument();
        expect(screen.getByTestId('normalized-crown')).toBeInTheDocument();
        expect(screen.getByTestId('anatomy-tooth-11')).toHaveAttribute('data-root-count', '1');
        expect(screen.getByTestId('anatomy-tooth-16')).toHaveAttribute('data-root-count', '3');
        expect(screen.getByTestId('anatomy-tooth-75')).toHaveAttribute('data-root-count', '2');
    });
});

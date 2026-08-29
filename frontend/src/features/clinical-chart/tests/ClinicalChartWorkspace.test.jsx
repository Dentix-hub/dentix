import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';

describe('ClinicalChartWorkspace scaffold', () => {
    it('renders the isolated chart workspace without crashing', () => {
        render(<ClinicalChartWorkspace />);

        expect(screen.getByTestId('clinical-chart-workspace')).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'مخطط الأسنان' })).toBeInTheDocument();
        expect(screen.getByRole('status')).toHaveTextContent('Chart foundation ready');
    });
});


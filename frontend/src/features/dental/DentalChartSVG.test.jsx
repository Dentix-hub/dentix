import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import DentalChartSVG from './DentalChartSVG';

describe('DentalChartSVG clinical renderer', () => {
    it('renders the adult chart in conventional FDI order', () => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={false} />
        );

        const teeth = [...container.querySelectorAll('[data-tooth]')].map((node) => Number(node.dataset.tooth));

        expect(teeth.slice(0, 16)).toEqual([
            18, 17, 16, 15, 14, 13, 12, 11,
            21, 22, 23, 24, 25, 26, 27, 28,
        ]);
        expect(teeth.slice(16)).toEqual([
            48, 47, 46, 45, 44, 43, 42, 41,
            31, 32, 33, 34, 35, 36, 37, 38,
        ]);
    });

    it('keeps the existing Universal-number click contract', () => {
        const onToothClick = vi.fn();
        render(
            <DentalChartSVG teethStatus={{}} onToothClick={onToothClick} isPediatric={false} />
        );

        fireEvent.click(screen.getByRole('button', { name: /Tooth 46/ }));
        expect(onToothClick).toHaveBeenCalledWith(30);
    });

    it('maps current backend conditions to clinical rendering states', () => {
        render(
            <DentalChartSVG
                teethStatus={{
                    46: { condition: 'RootCanal' },
                    26: { condition: 'Decayed' },
                    36: { condition: 'Crown' },
                    38: { condition: 'Missing' },
                }}
                onToothClick={vi.fn()}
                isPediatric={false}
            />
        );

        expect(screen.getByRole('button', { name: 'Tooth 46 — علاج عصب' })).toHaveAttribute('data-condition', 'RootCanal');
        expect(screen.getByRole('button', { name: 'Tooth 26 — تسوس' })).toHaveAttribute('data-condition', 'Decayed');
        expect(screen.getByRole('button', { name: 'Tooth 36 — تاج' })).toHaveAttribute('data-condition', 'Crown');
        expect(screen.getByRole('button', { name: 'Tooth 38 — سن مفقود' })).toHaveAttribute('data-condition', 'Missing');
    });

    it('renders primary dentition with FDI labels', () => {
        render(
            <DentalChartSVG teethStatus={{ 55: { condition: 'Filled' } }} onToothClick={vi.fn()} isPediatric />
        );

        expect(screen.getByRole('button', { name: 'Tooth 55 — حشو' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Tooth 85/ })).toBeInTheDocument();
    });
});

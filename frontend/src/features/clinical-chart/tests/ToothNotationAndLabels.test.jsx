import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DentalChartSVG from '@/features/dental/DentalChartSVG';
import {
    CHART_NOTATION_MODES,
    NOTATION_MODE_LABELS,
    fdiToUniversal,
    formatToothLabel,
} from '../domain/toothNotation';

describe('Phase A11 — Tooth Notation and Labels', () => {
    describe('A11-M01: Support current notation display mode', () => {
        it('defaults to Palmer notation and renders familiar UR/UL/LL/LR adult labels', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );

            expect(screen.getByText('Palmer Notation')).toBeInTheDocument();
            expect(container.querySelector('span[data-testid="tooth-label-11"]')).toHaveTextContent('UR1');
            expect(container.querySelector('span[data-testid="tooth-label-21"]')).toHaveTextContent('UL1');
            expect(container.querySelector('span[data-testid="tooth-label-36"]')).toHaveTextContent('LL6');
            expect(container.querySelector('span[data-testid="tooth-label-48"]')).toHaveTextContent('LR8');
        });

        it('defaults to Palmer notation for pediatric charts and renders letter labels', () => {
            const { container } = render(
                <DentalChartSVG isPediatric showRoots teethStatus={{}} />,
            );

            expect(screen.getByText('Palmer Notation')).toBeInTheDocument();
            expect(container.querySelector('span[data-testid="tooth-label-55"]')).toHaveTextContent('UR E');
            expect(container.querySelector('span[data-testid="tooth-label-61"]')).toHaveTextContent('UL A');
            expect(container.querySelector('span[data-testid="tooth-label-75"]')).toHaveTextContent('LL E');
            expect(container.querySelector('span[data-testid="tooth-label-81"]')).toHaveTextContent('LR A');
        });
    });

    describe('A11-M02: Add notation abstraction (toothNotation domain)', () => {
        it('exports frozen notation constants and human-readable mode labels', () => {
            expect(CHART_NOTATION_MODES).toEqual({
                PALMER: 'palmer',
                FDI: 'fdi',
                UNIVERSAL: 'universal',
            });
            expect(NOTATION_MODE_LABELS).toEqual({
                palmer: 'Palmer Notation',
                fdi: 'FDI World Dental Federation Notation',
                universal: 'Universal Numbering System',
            });
        });

        it('converts adult and pediatric FDI keys accurately to Universal notation', () => {
            // Upper right
            expect(fdiToUniversal('18')).toBe('1');
            expect(fdiToUniversal('11')).toBe('8');
            // Upper left
            expect(fdiToUniversal('21')).toBe('9');
            expect(fdiToUniversal('28')).toBe('16');
            // Lower left
            expect(fdiToUniversal('38')).toBe('17');
            expect(fdiToUniversal('31')).toBe('24');
            // Lower right
            expect(fdiToUniversal('41')).toBe('25');
            expect(fdiToUniversal('48')).toBe('32');

            // Primary teeth
            expect(fdiToUniversal('55')).toBe('A');
            expect(fdiToUniversal('61')).toBe('F');
            expect(fdiToUniversal('75')).toBe('K');
            expect(fdiToUniversal('85')).toBe('T');
        });

        it('formats tooth labels according to the active notation mode', () => {
            // Test tooth 11 (FDI 11, Universal 8, Palmer UR1)
            expect(formatToothLabel('11', { notationMode: 'fdi' })).toBe('11');
            expect(formatToothLabel('11', { notationMode: 'universal' })).toBe('8');
            expect(formatToothLabel('11', { notationMode: 'palmer' })).toBe('UR1');

            // Test tooth 46 (FDI 46, Universal 30, Palmer LR6)
            expect(formatToothLabel('46', { notationMode: 'fdi' })).toBe('46');
            expect(formatToothLabel('46', { notationMode: 'universal' })).toBe('30');
            expect(formatToothLabel('46', { notationMode: 'palmer' })).toBe('LR6');

            // Test primary tooth 55 (FDI 55, Universal A, Palmer UR E)
            expect(formatToothLabel('55', { notationMode: 'fdi', isPediatric: true })).toBe('55');
            expect(formatToothLabel('55', { notationMode: 'universal', isPediatric: true })).toBe('A');
            expect(formatToothLabel('55', { notationMode: 'palmer', isPediatric: true })).toBe('UR E');
        });

        it('switches DentalChartSVG labels and header when notationMode is FDI or Universal', () => {
            const { container, rerender } = render(
                <DentalChartSVG isPediatric={false} notationMode="fdi" showRoots teethStatus={{}} />,
            );

            expect(screen.getByText('FDI World Dental Federation Notation')).toBeInTheDocument();
            expect(container.querySelector('span[data-testid="tooth-label-11"]')).toHaveTextContent('11');
            expect(container.querySelector('span[data-testid="tooth-label-46"]')).toHaveTextContent('46');

            rerender(
                <DentalChartSVG isPediatric={false} notationMode="universal" showRoots teethStatus={{}} />,
            );

            expect(screen.getByText('Universal Numbering System')).toBeInTheDocument();
            expect(container.querySelector('span[data-testid="tooth-label-11"]')).toHaveTextContent('8');
            expect(container.querySelector('span[data-testid="tooth-label-46"]')).toHaveTextContent('30');
        });
    });

    describe('A11-M03: Verify label placement after roots', () => {
        it('places labels cleanly at the bottom margin without overlapping root apices', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            const labelSpans = container.querySelectorAll('span[data-testid^="tooth-label-"]');

            expect(labelSpans).toHaveLength(32);
            labelSpans.forEach((label) => {
                const parent = label.parentElement;
                expect(parent.className).toContain('absolute');
                expect(parent.className).toContain('-bottom-5');
                expect(label.className).toContain('font-mono');
                expect(label.className).toContain('text-sm');
                expect(label.className).toContain('font-bold');
            });
        });

        it('keeps the Palmer label accessible in aria attributes even when FDI or Universal is displayed', () => {
            render(
                <DentalChartSVG
                    enableSurfaceSelection
                    isPediatric={false}
                    notationMode="fdi"
                    onSurfaceClick={() => {}}
                    showRoots
                    teethStatus={{}}
                />,
            );

            // Screen readers still access standardized accessible descriptors
            expect(screen.getByRole('button', { name: /Tooth UR1 — Mesial/ })).toBeInTheDocument();
        });
    });
});

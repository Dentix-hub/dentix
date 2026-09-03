import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DentalChartSVG from './DentalChartSVG';
import { CHART_NOTATION_MODES } from '@/features/clinical-chart/domain/chartNotation';
import { getCrownGeometry } from '@/features/clinical-chart/rendering/crownGeometry';

const getCrownContract = (container) => Array.from(container.querySelectorAll('svg[data-layer="crown"]')).map((svg) => {
    const path = svg.querySelector('path');
    const orientation = svg.querySelector('[data-crown-orientation]');
    const scale = svg.querySelector('[data-crown-scale]');
    return {
        toothKey: svg.getAttribute('data-tooth-key'),
        width: svg.getAttribute('width'),
        height: svg.getAttribute('height'),
        viewBox: svg.getAttribute('viewBox'),
        path: path.getAttribute('d'),
        fill: path.getAttribute('fill'),
        stroke: path.getAttribute('stroke'),
        strokeWidth: path.getAttribute('stroke-width'),
        transform: orientation.getAttribute('transform'),
        scale: scale.getAttribute('transform'),
    };
});

describe('DentalChartSVG optional root extension', () => {
    it('preserves current Palmer labels by default after roots', () => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={false} showRoots />,
        );
        const labels = container.querySelectorAll('[data-layer="notation-label"]');

        expect(labels).toHaveLength(32);
        expect(screen.getByText('Palmer Notation')).toBeInTheDocument();
        expect(container.querySelector('[data-layer="notation-label"][data-tooth-key="11"]'))
            .toHaveTextContent('UR1');
        labels.forEach((label) => {
            const anatomyViewport = label.parentElement.previousElementSibling;
            expect(anatomyViewport.querySelector('[data-layer="roots"]')).toBeInTheDocument();
            expect(anatomyViewport.querySelector('[data-layer="crown"]')).toBeInTheDocument();
            expect(label.className).toContain('whitespace-nowrap');
        });
    });

    it.each([
        [CHART_NOTATION_MODES.FDI, 'FDI Notation', '11'],
        [CHART_NOTATION_MODES.UNIVERSAL, 'Universal Notation', '8'],
    ])('uses the bounded %s presentation config without changing tooth identity', (
        notationMode,
        displayName,
        expectedLabel,
    ) => {
        const { container } = render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                isPediatric={false}
                showRoots
                notationMode={notationMode}
            />,
        );
        const tooth11 = container.querySelector('[data-layer="notation-label"][data-tooth-key="11"]');

        expect(screen.getByText(displayName)).toBeInTheDocument();
        expect(tooth11).toHaveTextContent(expectedLabel);
        expect(tooth11).toHaveAttribute('data-notation-mode', notationMode);
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="11"]'))
            .toBeInTheDocument();
        expect(container.querySelector('svg[data-layer="crown"][data-tooth-key="11"]'))
            .toBeInTheDocument();
    });

    it('keeps the production chart root-free by default', () => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={false} />,
        );

        expect(container.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
        expect(container.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(0);
    });

    it('adds roots behind the same untouched crown geometry only when requested', () => {
        const props = { teethStatus: {}, onToothClick: vi.fn(), isPediatric: false };
        const { container, rerender } = render(<DentalChartSVG {...props} />);
        const baselineCrowns = getCrownContract(container);

        rerender(<DentalChartSVG {...props} showRoots />);

        expect(container.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(32);
        expect(getCrownContract(container)).toEqual(baselineCrowns);
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="18"] g')).toHaveAttribute('transform', 'rotate(180 25 24)');
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="38"] g')).not.toHaveAttribute('transform');
    });

    it('supports the complete primary dentition with the same optional layer', () => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric showRoots />,
        );

        expect(container.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(20);
        expect(container.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(20);
    });

    it.each([false, true])('preserves every %s dentition crown without orientation or scale transforms', (isPediatric) => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={isPediatric} showRoots />,
        );

        const crowns = container.querySelectorAll('svg[data-layer="crown"]');
        expect(crowns).toHaveLength(isPediatric ? 20 : 32);
        crowns.forEach((crown) => {
            expect(crown.querySelector('[data-crown-orientation]')).not.toHaveAttribute('transform');
            expect(crown.querySelector('[data-crown-scale]')).toHaveAttribute('data-crown-scale', '1');
            expect(crown.querySelector('[data-crown-scale]')).not.toHaveAttribute('transform');
        });
    });

    it('renders root proportions from the same per-tooth display registry', () => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={false} showRoots />,
        );

        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="11"] [data-root-scale]'))
            .toHaveAttribute('data-root-scale', '0.97 0.96');
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="31"] [data-root-scale]'))
            .toHaveAttribute('data-root-scale', '0.95 0.92');
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="12"] [data-root-scale]'))
            .toHaveAttribute('data-root-scale', '0.84 0.82');
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="16"] [data-root-scale]'))
            .toHaveAttribute('data-root-scale', '0.9 0.84');
    });

    it('adds five accessible surface targets per tooth only in surface-selection mode', () => {
        const { container } = render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                isPediatric={false}
                showRoots
                enableSurfaceSelection
                onSurfaceClick={vi.fn()}
            />,
        );

        expect(container.querySelectorAll('[data-layer="surfaces"]')).toHaveLength(32);
        expect(screen.getAllByRole('button')).toHaveLength(160);
        expect(container.querySelectorAll('button')).toHaveLength(0);
        expect(container.querySelectorAll('[data-surface-code="O"]')).toHaveLength(20);
        expect(container.querySelectorAll('[data-surface-code="I"]')).toHaveLength(12);
    });

    it('emits neutral surface selection intents for pointer and keyboard input', () => {
        const onSurfaceClick = vi.fn();
        render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                isPediatric={false}
                enableSurfaceSelection
                onSurfaceClick={onSurfaceClick}
            />,
        );
        const mesialSurface = screen.getByRole('button', { name: 'Tooth UR1 — Mesial (M)' });

        fireEvent.click(mesialSurface);
        expect(onSurfaceClick).toHaveBeenLastCalledWith({ toothKey: '11', toothNumber: 8, surfaceCode: 'M' });

        fireEvent.keyDown(mesialSurface, { key: 'Enter' });
        expect(onSurfaceClick).toHaveBeenCalledTimes(2);
        expect(mesialSurface).toHaveAttribute('tabindex', '0');
        expect(mesialSurface.className.baseVal).toContain('focus:fill-blue-100');
    });

    it('shows a selected surface without changing the underlying crown path', () => {
        const { container } = render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                isPediatric={false}
                enableSurfaceSelection
                selectedSurface={{ toothKey: '46', surfaceCode: 'O' }}
                onSurfaceClick={vi.fn()}
            />,
        );
        const selected = container.querySelector('svg[data-tooth-key="46"] [data-surface-code="O"]');

        expect(selected).toHaveAttribute('aria-pressed', 'true');
        expect(selected.className.baseVal).toContain('fill-blue-200');
        expect(container.querySelector('svg[data-tooth-key="46"] [data-layer-role="base-anatomy"] path').getAttribute('d')).toBeTruthy();
    });

    it('keeps the direct chart non-interactive when read-only overrides surface mode', () => {
        const { container } = render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                isPediatric={false}
                enableSurfaceSelection
                onSurfaceClick={vi.fn()}
                readOnly
            />,
        );

        expect(screen.queryAllByRole('button')).toHaveLength(0);
        expect(container.querySelectorAll('[data-layer="surfaces"]')).toHaveLength(0);
        expect(container.firstChild).toHaveAttribute('data-interaction-mode', 'read-only');
    });
});

describe('DentalChartSVG live anatomical crown and root integration', () => {
    const LEGACY_SIMPLIFIED_PATHS = [
        "M10,5 C15,0 35,0 40,5 C45,15 45,35 40,45 C35,50 15,50 10,45 C5,35 5,15 10,5 Z M15,15 L20,20 M30,15 L25,20 M25,25 L25,35",
        "M12,8 C17,3 33,3 38,8 C42,15 42,30 38,40 C33,45 17,45 12,40 C8,30 8,15 12,8 Z M25,15 L25,30",
        "M15,10 C20,5 30,5 35,10 C40,20 35,40 25,48 C15,40 10,20 15,10 Z",
        "M10,10 C15,8 35,8 40,10 C42,20 40,40 35,45 C30,48 20,48 15,45 C10,40 8,20 10,10 Z",
        "M15,12 C18,10 32,10 35,12 C36,20 35,35 32,40 C28,42 22,42 18,40 C15,35 14,20 15,12 Z",
    ];

    it.each(['11', '13', '14', '16', '36', '46'])(
        'renders permanent tooth %s using anatomical dental-v3-organic geometry instead of legacy simplified paths',
        (toothKey) => {
            const crownGeometry = getCrownGeometry(toothKey);
            expect(crownGeometry.source).toBe('dental-v3-organic');

            const { container } = render(
                <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={false} showRoots />,
            );

            const crownSvg = container.querySelector(`svg[data-layer="crown"][data-tooth-key="${toothKey}"]`);
            expect(crownSvg).toBeInTheDocument();

            const renderedPaths = Array.from(
                crownSvg.querySelectorAll('[data-layer-role="base-anatomy"] path'),
            ).map((p) => p.getAttribute('d'));

            expect(renderedPaths).toHaveLength(5);

            const expectedPaths = Object.values(crownGeometry.paths);
            expect(renderedPaths).toEqual(expect.arrayContaining(expectedPaths));

            renderedPaths.forEach((renderedPath) => {
                expect(LEGACY_SIMPLIFIED_PATHS).not.toContain(renderedPath);
            });
        },
    );

    it('preserves anatomical morphological distinction across tooth families', () => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={false} showRoots />,
        );

        const getFirstSurfacePath = (toothKey) => container.querySelector(
            `svg[data-layer="crown"][data-tooth-key="${toothKey}"] [data-layer-role="base-anatomy"] path`,
        )?.getAttribute('d');

        const incisor11 = getFirstSurfacePath('11');
        const canine13 = getFirstSurfacePath('13');
        const premolar14 = getFirstSurfacePath('14');
        const molar16 = getFirstSurfacePath('16');
        const molar46 = getFirstSurfacePath('46');

        expect(new Set([incisor11, canine13, premolar14, molar16, molar46]).size).toBe(5);
    });

    it('renders root layers on the main chart with accurate root counts', () => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={false} showRoots />,
        );

        expect(container.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(32);

        const testCases = [
            { toothKey: '11', expectedRoots: 1 },
            { toothKey: '14', expectedRoots: 2 },
            { toothKey: '16', expectedRoots: 3 },
            { toothKey: '46', expectedRoots: 2 },
        ];

        testCases.forEach(({ toothKey, expectedRoots }) => {
            const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
            expect(rootSvg).toBeInTheDocument();
            const rootPaths = rootSvg.querySelectorAll('[data-layer-role="base-anatomy"] > path');
            expect(rootPaths).toHaveLength(expectedRoots);
            expect(rootSvg).toHaveAttribute('data-root-count', String(expectedRoots));
        });
    });

    it('renders patient status styles across all anatomical crown surfaces', () => {
        const statusMap = {
            '11': { condition: 'Healthy' },
            '16': { condition: 'Decayed' },
            '14': { condition: 'Filled' },
            '13': { condition: 'Missing' },
            '36': { condition: 'Crown' },
            '46': { condition: 'RootCanal' },
        };

        const { container } = render(
            <DentalChartSVG teethStatus={statusMap} onToothClick={vi.fn()} isPediatric={false} showRoots />,
        );

        // Healthy 11: white fill, slate stroke
        const paths11 = container.querySelectorAll('svg[data-layer="crown"][data-tooth-key="11"] [data-layer-role="base-anatomy"] path');
        paths11.forEach((p) => {
            expect(p).toHaveAttribute('fill', '#ffffff');
            expect(p).toHaveAttribute('stroke', '#94a3b8');
        });

        // Decayed 16: red tint fill, red stroke, red dot indicator
        const paths16 = container.querySelectorAll('svg[data-layer="crown"][data-tooth-key="16"] [data-layer-role="base-anatomy"] path');
        paths16.forEach((p) => {
            expect(p).toHaveAttribute('fill', '#fecaca');
            expect(p).toHaveAttribute('stroke', '#ef4444');
        });
        expect(container.querySelector('svg[data-layer="crown"][data-tooth-key="16"] circle')).toHaveAttribute('fill', '#ef4444');

        // Filled 14: blue tint fill, blue stroke
        const paths14 = container.querySelectorAll('svg[data-layer="crown"][data-tooth-key="14"] [data-layer-role="base-anatomy"] path');
        paths14.forEach((p) => {
            expect(p).toHaveAttribute('fill', '#bfdbfe');
            expect(p).toHaveAttribute('stroke', '#3b82f6');
        });

        // Missing 13: slate-50 fill, slate-200 stroke
        const paths13 = container.querySelectorAll('svg[data-layer="crown"][data-tooth-key="13"] [data-layer-role="base-anatomy"] path');
        paths13.forEach((p) => {
            expect(p).toHaveAttribute('fill', '#f1f5f9');
            expect(p).toHaveAttribute('stroke', '#e2e8f0');
        });

        // Crown 36: yellow fill, yellow stroke
        const paths36 = container.querySelectorAll('svg[data-layer="crown"][data-tooth-key="36"] [data-layer-role="base-anatomy"] path');
        paths36.forEach((p) => {
            expect(p).toHaveAttribute('fill', '#fef08a');
            expect(p).toHaveAttribute('stroke', '#eab308');
        });

        // RootCanal 46: purple fill, purple stroke
        const paths46 = container.querySelectorAll('svg[data-layer="crown"][data-tooth-key="46"] [data-layer-role="base-anatomy"] path');
        paths46.forEach((p) => {
            expect(p).toHaveAttribute('fill', '#e9d5ff');
            expect(p).toHaveAttribute('stroke', '#a855f7');
        });
    });

    it('preserves surface selection hit targets and event dispatching with anatomical crowns', () => {
        const onSurfaceClick = vi.fn();
        const { container } = render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                isPediatric={false}
                enableSurfaceSelection
                onSurfaceClick={onSurfaceClick}
                showRoots
            />,
        );

        const tooth16Surfaces = container.querySelectorAll('svg[data-tooth-key="16"] [data-layer="surfaces"] path');
        expect(tooth16Surfaces).toHaveLength(5);

        const occlusalSurface = container.querySelector('svg[data-tooth-key="16"] [data-surface-code="O"]');
        expect(occlusalSurface).toBeInTheDocument();
        fireEvent.click(occlusalSurface);

        expect(onSurfaceClick).toHaveBeenCalledTimes(1);
        expect(onSurfaceClick).toHaveBeenCalledWith(expect.objectContaining({
            toothKey: '16',
            surfaceCode: 'O',
        }));
    });

    it('renders 32 teeth for permanent and 20 teeth for primary dentition', () => {
        const { container: adultChart } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={false} showRoots />,
        );
        expect(adultChart.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
        expect(adultChart.querySelectorAll('[data-layer="notation-label"]')).toHaveLength(32);

        const { container: pediatricChart } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={true} showRoots />,
        );
        expect(pediatricChart.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(20);
        expect(pediatricChart.querySelectorAll('[data-layer="notation-label"]')).toHaveLength(20);
    });

    it('supports mixed dentition with anatomical permanent crowns and primary crowns coexisting', () => {
        const mixedToothOrder = [
            '16', '55', '54', '53', '12', '11',
            '21', '22', '63', '64', '65', '26',
            '36', '75', '74', '73', '32', '31',
            '41', '42', '83', '84', '85', '46',
        ];

        const { container } = render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                toothOrder={mixedToothOrder}
                showRoots
            />,
        );

        expect(container.firstChild).toHaveAttribute('data-dentition', 'mixed');
        expect(container.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(mixedToothOrder.length);

        // Permanent tooth 16 has 5 anatomical surface paths
        const tooth16Paths = container.querySelectorAll('svg[data-layer="crown"][data-tooth-key="16"] [data-layer-role="base-anatomy"] path');
        expect(tooth16Paths).toHaveLength(5);

        // Primary tooth 55 has single outline path
        const tooth55Paths = container.querySelectorAll('svg[data-layer="crown"][data-tooth-key="55"] [data-layer-role="base-anatomy"] path');
        expect(tooth55Paths).toHaveLength(1);
    });
});


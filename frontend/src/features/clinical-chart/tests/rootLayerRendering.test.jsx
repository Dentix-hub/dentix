import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DentalChartSVG from '@/features/dental/DentalChartSVG';
import {
    DENTAL_ANATOMY_REGISTRY,
    DENTITIONS,
} from '../domain/dentalAnatomyRegistry';
import { getRootGeometry } from '../rendering/rootGeometry';

const ROOT_FAMILY_VISUAL_MATRIX = [
    { label: 'permanent maxillary central incisor', toothKey: '11', rootCount: 1 },
    { label: 'permanent mandibular canine', toothKey: '33', rootCount: 1 },
    { label: 'permanent maxillary first premolar', toothKey: '14', rootCount: 2 },
    { label: 'permanent maxillary second premolar', toothKey: '15', rootCount: 1 },
    { label: 'permanent maxillary molar', toothKey: '16', rootCount: 3 },
    { label: 'permanent mandibular molar', toothKey: '36', rootCount: 2 },
    { label: 'primary maxillary incisor', toothKey: '51', rootCount: 1 },
    { label: 'primary mandibular canine', toothKey: '73', rootCount: 1 },
    { label: 'primary maxillary molar', toothKey: '55', rootCount: 3 },
    { label: 'primary mandibular molar', toothKey: '85', rootCount: 2 },
];

const renderChart = (isPediatric) => render(
    <DentalChartSVG
        isPediatric={isPediatric}
        onToothClick={vi.fn()}
        showRoots
        teethStatus={{}}
    />,
);

const getRootLayer = (container, toothKey) => container.querySelector(
    `svg[data-layer="roots"][data-tooth-key="${toothKey}"]`,
);

const getBaseRootPaths = (rootLayer) => rootLayer.querySelectorAll(
    '[data-layer-role="base-anatomy"] > path',
);

const getPathCoordinatePairs = (path) => {
    const values = path.match(/-?\d+(?:\.\d+)?/g).map(Number);
    return Array.from({ length: values.length / 2 }, (_, index) => ({
        x: values[index * 2],
        y: values[(index * 2) + 1],
    }));
};

describe('A10 independent root layer rendering', () => {
    it.each([
        { dentition: DENTITIONS.PERMANENT, isPediatric: false, toothCount: 32 },
        { dentition: DENTITIONS.PRIMARY, isPediatric: true, toothCount: 20 },
    ])('renders one separate root layer below every $dentition crown', ({
        dentition,
        isPediatric,
        toothCount,
    }) => {
        const { container } = renderChart(isPediatric);
        const roots = container.querySelectorAll('svg[data-layer="roots"]');
        const crowns = container.querySelectorAll('svg[data-layer="crown"]');

        expect(roots).toHaveLength(toothCount);
        expect(crowns).toHaveLength(toothCount);
        Object.values(DENTAL_ANATOMY_REGISTRY)
            .filter((anatomy) => anatomy.dentition === dentition)
            .forEach((anatomy) => {
                const rootLayer = getRootLayer(container, anatomy.toothKey);
                const crownLayer = container.querySelector(
                    `svg[data-layer="crown"][data-tooth-key="${anatomy.toothKey}"]`,
                );

                expect(rootLayer).toBeInTheDocument();
                expect(crownLayer).toBeInTheDocument();
                expect(rootLayer.parentElement).toBe(crownLayer.parentElement);
                expect(rootLayer.nextElementSibling).toBe(crownLayer);
                expect(rootLayer).toHaveAttribute('aria-hidden', 'true');
                expect(rootLayer).toHaveAttribute('width', '50');
                expect(rootLayer).toHaveAttribute('height', '48');
                expect(rootLayer).toHaveAttribute('viewBox', '0 0 50 48');
            });
    });

    it.each(ROOT_FAMILY_VISUAL_MATRIX)(
        'renders the $label visual matrix case with $rootCount root(s)',
        ({ toothKey, rootCount }) => {
            const anatomy = DENTAL_ANATOMY_REGISTRY[toothKey];
            const { container } = renderChart(anatomy.dentition === DENTITIONS.PRIMARY);
            const rootLayer = getRootLayer(container, toothKey);

            expect(getBaseRootPaths(rootLayer)).toHaveLength(rootCount);
            expect(rootLayer.querySelector('[data-layer-index="0"]'))
                .toHaveAttribute('data-layer-role', 'base-anatomy');
        },
    );

    it('keeps maxillary roots apical-up and mandibular roots apical-down', () => {
        const { container: adult } = renderChart(false);
        const { container: primary } = renderChart(true);

        ['11', '14', '16'].forEach((toothKey) => {
            expect(getRootLayer(adult, toothKey).querySelector('[data-root-orientation]'))
                .toHaveAttribute('transform', 'rotate(180 25 24)');
        });
        ['31', '34', '36'].forEach((toothKey) => {
            expect(getRootLayer(adult, toothKey).querySelector('[data-root-orientation]'))
                .not.toHaveAttribute('transform');
        });
        expect(getRootLayer(primary, '55').querySelector('[data-root-orientation]'))
            .toHaveAttribute('transform', 'rotate(180 25 24)');
        expect(getRootLayer(primary, '85').querySelector('[data-root-orientation]'))
            .not.toHaveAttribute('transform');
    });

    it('keeps every scaled apex and lateral control point inside its tooth viewport', () => {
        Object.values(DENTAL_ANATOMY_REGISTRY).forEach((anatomy) => {
            getRootGeometry(anatomy.toothKey).forEach((root) => {
                const halfStroke = root.style.strokeWidth / 2;
                const coordinates = getPathCoordinatePairs(root.path);
                const scaled = coordinates.map(({ x, y }) => ({
                    x: 25 + ((x - 25) * root.displayScale.x),
                    y: y * root.displayScale.y,
                }));

                expect(Math.min(...scaled.map(({ x }) => x)) - halfStroke)
                    .toBeGreaterThanOrEqual(0);
                expect(Math.max(...scaled.map(({ x }) => x)) + halfStroke)
                    .toBeLessThanOrEqual(50);
                expect(Math.max(...scaled.map(({ y }) => y)) + halfStroke)
                    .toBeLessThanOrEqual(48);
            });
        });
    });

    it.each([false, true])('keeps each root viewport inside a fixed-width tooth slot', (isPediatric) => {
        const { container } = renderChart(isPediatric);

        container.querySelectorAll('svg[data-layer="roots"]').forEach((rootLayer) => {
            const toothSlot = rootLayer.parentElement;

            expect(rootLayer.classList).toContain('absolute');
            expect(toothSlot.className).toContain('w-[50px]');
            expect(rootLayer.getAttribute('width')).toBe('50');
        });
    });
});

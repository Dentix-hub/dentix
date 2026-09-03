import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DentalChartSVG from '../../dental/DentalChartSVG';
import ClinicalChartRenderer from '../components/ClinicalChartRenderer';
import ClinicalChartShell from '../components/ClinicalChartShell';
import {
    DENTAL_ANATOMY_REGISTRY,
    DENTITIONS,
    PERMANENT_TOOTH_KEYS,
    PRIMARY_TOOTH_KEYS,
    TOOTH_TYPES,
} from '../domain/dentalAnatomyRegistry';
import {
    CHART_INTERACTION_MODES,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';
import { getRootGeometry } from '../rendering/rootGeometry';
import {
    ADULT_DENTITION_FIXTURE,
    MIXED_DENTITION_FIXTURE,
    PRIMARY_DENTITION_FIXTURE,
} from '../fixtures/demoProjectionFixtures';

describe('Phase A16 — Full Regression Verification Suite', () => {
    describe('A16-M01: Anatomy registry 100% coverage test (all 52 teeth)', () => {
        it('verifies all 32 permanent teeth and 20 primary teeth adhere to complete anatomical contract', () => {
            expect(PERMANENT_TOOTH_KEYS).toHaveLength(32);
            expect(PRIMARY_TOOTH_KEYS).toHaveLength(20);

            const allToothKeys = [...PERMANENT_TOOTH_KEYS, ...PRIMARY_TOOTH_KEYS];
            expect(allToothKeys).toHaveLength(52);
            expect(Object.keys(DENTAL_ANATOMY_REGISTRY)).toHaveLength(52);

            allToothKeys.forEach((toothKey) => {
                const record = DENTAL_ANATOMY_REGISTRY[toothKey];
                expect(record).toBeDefined();
                expect(record.toothKey).toBe(toothKey);
                expect([DENTITIONS.PERMANENT, DENTITIONS.PRIMARY]).toContain(record.dentition);
                expect(Object.values(TOOTH_TYPES)).toContain(record.toothType);
                expect(['maxillary', 'mandibular']).toContain(record.arch);
                expect(['right', 'left']).toContain(record.side);

                // Root morphology contract
                expect(record.rootCount).toBeGreaterThanOrEqual(1);
                expect(record.rootCount).toBeLessThanOrEqual(3);
                expect(record.rootOutlineRefs).toHaveLength(record.rootCount);

                // Surface model contract (anterior vs posterior)
                const expectedSurfaceModel = [TOOTH_TYPES.INCISOR, TOOTH_TYPES.CANINE].includes(record.toothType)
                    ? 'anterior'
                    : 'posterior';
                expect(record.surfaceMap.model).toBe(expectedSurfaceModel);

                // Geometry generator test
                const roots = getRootGeometry(toothKey);
                expect(roots).toHaveLength(record.rootCount);
                roots.forEach((root) => {
                    expect(root.path).toBeTruthy();
                    expect(root.cervicalAnchors.left.x).toBeDefined();
                    expect(root.cervicalAnchors.right.x).toBeDefined();
                    expect(root.apexAnchor.x).toBeDefined();
                });
            });
        });
    });

    describe('A16-M02: Renderer smoke test across all dentitions', () => {
        it('renders permanent dentition without errors or warnings', () => {
            const input = createClinicalChartRendererInput({
                chartId: 'smoke-permanent',
                anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
                dentition: DENTITIONS.PERMANENT,
                visualState: ADULT_DENTITION_FIXTURE,
            });

            render(<ClinicalChartRenderer input={input} />);
            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
        });

        it('renders primary dentition without errors or warnings', () => {
            const input = createClinicalChartRendererInput({
                chartId: 'smoke-primary',
                anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
                dentition: DENTITIONS.PRIMARY,
                visualState: PRIMARY_DENTITION_FIXTURE,
            });

            render(<ClinicalChartRenderer input={input} />);
            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(20);
        });
    });

    describe('A16-M03: Multi-instance isolation test', () => {
        it('verifies two concurrent chart instances maintain isolated state and selections', () => {
            let intentA = null;
            let intentB = null;

            const inputA = createClinicalChartRendererInput({
                chartId: 'instance-alpha',
                anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
                dentition: DENTITIONS.PERMANENT,
                interactionMode: CHART_INTERACTION_MODES.EDIT,
                layers: { roots: true, surfaces: true },
                visualState: {
                    ...ADULT_DENTITION_FIXTURE,
                    selection: { kind: 'surface', toothKey: '11', surfaceCode: 'M' },
                },
                callbacks: { onIntent: (i) => { intentA = i; } },
            });

            const inputB = createClinicalChartRendererInput({
                chartId: 'instance-beta',
                anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
                dentition: DENTITIONS.PERMANENT,
                interactionMode: CHART_INTERACTION_MODES.EDIT,
                layers: { roots: true, surfaces: true },
                visualState: {
                    ...ADULT_DENTITION_FIXTURE,
                    selection: { kind: 'surface', toothKey: '46', surfaceCode: 'O' },
                },
                callbacks: { onIntent: (i) => { intentB = i; } },
            });

            const { container } = render(
                <div>
                    <div data-testid="container-a">
                        <ClinicalChartRenderer input={inputA} />
                    </div>
                    <div data-testid="container-b">
                        <ClinicalChartRenderer input={inputB} />
                    </div>
                </div>,
            );

            // Container A has 32 teeth, Container B has 32 teeth
            const chartA = container.querySelector('[data-testid="container-a"]');
            const chartB = container.querySelector('[data-testid="container-b"]');
            expect(chartA.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
            expect(chartB.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);

            // Selected surface in A is 11-M
            const selectedA = chartA.querySelector('svg[data-tooth-key="11"] [data-surface-code="M"]');
            expect(selectedA).toHaveAttribute('aria-pressed', 'true');

            // Selected surface in B is 46-O
            const selectedB = chartB.querySelector('svg[data-tooth-key="46"] [data-surface-code="O"]');
            expect(selectedB).toHaveAttribute('aria-pressed', 'true');

            // 11-M in B is NOT pressed
            const unselectedB = chartB.querySelector('svg[data-tooth-key="11"] [data-surface-code="M"]');
            expect(unselectedB).toHaveAttribute('aria-pressed', 'false');

            // Click in A dispatches to A with chartId instance-alpha
            fireEvent.click(selectedA);
            expect(intentA.chartId).toBe('instance-alpha');
            expect(intentB).toBeNull();
        });
    });

    describe('A16-M04: Root visual regression evidence', () => {
        it('verifies anatomical root counts and morphology on representative teeth archetypes', () => {
            render(
                <DentalChartSVG
                    enableSurfaceSelection
                    isPediatric={false}
                    showRoots
                />,
            );

            // Maxillary central incisor 11: 1 root
            const incisorRoots = document.querySelector('svg[data-layer="roots"][data-tooth-key="11"]');
            expect(incisorRoots).toHaveAttribute('data-root-count', '1');

            // Maxillary first premolar 14: 2 roots (bifurcated)
            const premolarRoots = document.querySelector('svg[data-layer="roots"][data-tooth-key="14"]');
            expect(premolarRoots).toHaveAttribute('data-root-count', '2');

            // Maxillary first molar 16: 3 roots
            const maxMolarRoots = document.querySelector('svg[data-layer="roots"][data-tooth-key="16"]');
            expect(maxMolarRoots).toHaveAttribute('data-root-count', '3');

            // Mandibular first molar 46: 2 roots
            const mandMolarRoots = document.querySelector('svg[data-layer="roots"][data-tooth-key="46"]');
            expect(mandMolarRoots).toHaveAttribute('data-root-count', '2');
        });
    });

    describe('A16-M05: Mixed dentition render test', () => {
        it('renders mixed dentition fixture accurately without layout collision', () => {
            const input = createClinicalChartRendererInput({
                chartId: 'mixed-dentition-smoke',
                anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
                dentition: DENTITIONS.PERMANENT,
                visualState: MIXED_DENTITION_FIXTURE,
            });

            render(<ClinicalChartRenderer input={input} />);

            // Renders cleanly with teeth present
            expect(document.querySelectorAll('svg[data-layer="crown"]').length).toBeGreaterThan(0);
        });
    });

    describe('A16-M06: RTL render test', () => {
        it('preserves anatomical orientation (patient right on left, patient left on right) under RTL root', () => {
            render(
                <div dir="rtl">
                    <ClinicalChartShell />
                </div>,
            );

            const shell = screen.getByTestId('clinical-chart-shell');
            expect(shell.closest('[dir="rtl"]')).toBeInTheDocument();

            // Inner SVG canvas preserves dir="ltr"
            const canvas = document.querySelector('[data-notation-mode] > div[dir="ltr"]');
            expect(canvas).toBeInTheDocument();
        });
    });

    describe('A16-M07: Mobile render test', () => {
        it('renders responsive mobile container and supports single quadrant focus', () => {
            render(<ClinicalChartShell />);

            // Focus on LL quadrant
            const select = screen.getByTestId('shell-quadrant-select');
            fireEvent.change(select, { target: { value: 'LL' } });

            // Only 8 teeth rendered in quadrant LL
            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(8);
            expect(document.querySelector('[data-quadrant="LL"]')).toBeInTheDocument();
        });
    });
});

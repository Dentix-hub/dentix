import { fireEvent, render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ClinicalChartRenderer from '../components/ClinicalChartRenderer';
import ClinicalChartComparisonCard from '../components/ClinicalChartComparisonCard';
import {
    DENTAL_ANATOMY_REGISTRY,
    DENTITIONS,
    PERMANENT_TOOTH_KEYS,
    PRIMARY_TOOTH_KEYS,
    TOOTH_TYPES,
} from '../domain/dentalAnatomyRegistry';
import {
    A12_ADULT_DENTITION_FIXTURE,
    A12_MIXED_DENTITION_FIXTURE,
    A12_SCENARIO_FIXTURES,
    MIXED_DENTITION_TOOTH_ORDER,
} from '../fixtures';
import {
    CHART_INTENT_TYPES,
    CHART_INTERACTION_MODES,
    CHART_NOTATION_MODES,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';
import { getRootGeometry } from '../rendering/rootGeometry';
import DentalChartSVG from '@/features/dental/DentalChartSVG';
import { CLINICAL_CHART_COPY } from '../components/clinicalChartWorkspaceCopy';

// ---------------------------------------------------------------------------
// A16-M01 - Exhaustive Anatomy Registry Contract
// ---------------------------------------------------------------------------

describe('A16-M01 exhaustive anatomy registry contract', () => {
    const allRecords = Object.values(DENTAL_ANATOMY_REGISTRY);

    it('contains exactly 52 unique tooth records spanning permanent and primary dentitions', () => {
        expect(allRecords).toHaveLength(52);
        expect(PERMANENT_TOOTH_KEYS).toHaveLength(32);
        expect(PRIMARY_TOOTH_KEYS).toHaveLength(20);

        const keys = allRecords.map((record) => record.toothKey);
        expect(new Set(keys).size).toBe(52);
    });

    it('ensures all surfaceMap.geometryRef and root outlineRef values are unique', () => {
        const geometryRefs = allRecords.map((record) => record.surfaceMap.geometryRef);
        expect(new Set(geometryRefs).size).toBe(52);

        const allRootOutlineRefs = allRecords.flatMap((record) =>
            record.rootOutlineRefs.map((root) => root.outlineRef),
        );
        expect(new Set(allRootOutlineRefs).size).toBe(allRootOutlineRefs.length);
    });

    it.each(allRecords)('satisfies the complete anatomy schema for tooth $toothKey', (record) => {
        expect(record.toothKey).toBeTypeOf('string');
        expect(Object.values(DENTITIONS)).toContain(record.dentition);
        expect(Object.values(TOOTH_TYPES)).toContain(record.toothType);
        expect(['maxillary', 'mandibular']).toContain(record.arch);
        expect(['right', 'left']).toContain(record.side);
        expect(record.crownOutlineRef).toBeTruthy();

        expect(['anterior', 'posterior']).toContain(record.surfaceMap.model);
        expect(record.surfaceMap.geometryRef).toBe(`surfaces:${record.toothKey}`);
        expect(record.surfaceMap.surfaceCodes).toHaveLength(5);

        expect(record.rootCount).toBeGreaterThan(0);
        expect(record.rootOutlineRefs).toHaveLength(record.rootCount);
        expect(record.canalAnchorPlaceholders).toHaveLength(record.rootCount);

        expect(record.labelAnchor).toEqual({
            x: expect.any(Number),
            y: expect.any(Number),
        });
        expect(record.overlayAnchors.center).toEqual({
            x: expect.any(Number),
            y: expect.any(Number),
        });
        expect(record.overlayAnchors.crown).toEqual({
            x: expect.any(Number),
            y: expect.any(Number),
        });
        expect(record.overlayAnchors.root).toEqual({
            x: expect.any(Number),
            y: expect.any(Number),
        });

        const roots = getRootGeometry(record.toothKey);
        expect(roots).toHaveLength(record.rootCount);
        expect(roots.map((root) => root.rootId)).toEqual(record.rootOutlineRefs.map((root) => root.rootId));
    });
});

// ---------------------------------------------------------------------------
// A16-M02 - Generic Renderer Smoke Gate
// ---------------------------------------------------------------------------

describe('A16-M02 generic renderer smoke gate', () => {
    const fixtures = Object.values(A12_SCENARIO_FIXTURES);

    it('has exactly 11 scenario fixtures', () => {
        expect(fixtures).toHaveLength(11);
    });

    it.each(fixtures)('renders fixture $projectionId without throwing and unmounts cleanly', (fixture) => {
        const input = createClinicalChartRendererInput({
            chartId: `smoke:${fixture.projectionId}`,
            anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
            dentition: fixture.dentition,
            visualState: fixture,
            notationMode: CHART_NOTATION_MODES.FDI,
            interactionMode: CHART_INTERACTION_MODES.READ_ONLY,
            layers: {
                roots: true,
                surfaces: false,
            },
            callbacks: {},
        });

        const { container, unmount } = render(<ClinicalChartRenderer input={input} />);

        expect(container.firstChild).toBeInTheDocument();
        expect(container.firstChild).toHaveAttribute('data-dentition', fixture.dentition);

        const expectedCrownCount = fixture.dentition === 'primary'
            ? 20
            : (fixture.dentition === 'mixed' ? MIXED_DENTITION_TOOTH_ORDER.length : 32);
        expect(container.querySelectorAll('[data-layer="crown"]')).toHaveLength(expectedCrownCount);

        expect(() => unmount()).not.toThrow();
    });
});

// ---------------------------------------------------------------------------
// A16-M03 - Multi-Instance Isolation Test
// ---------------------------------------------------------------------------

describe('A16-M03 multi-instance isolation test', () => {
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
                ...A12_ADULT_DENTITION_FIXTURE,
                selection: { kind: 'surface', toothKey: '11', surfaceCode: 'M' },
            },
            callbacks: { onIntent: (intent) => { intentA = intent; } },
        });

        const inputB = createClinicalChartRendererInput({
            chartId: 'instance-beta',
            anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
            dentition: DENTITIONS.PERMANENT,
            interactionMode: CHART_INTERACTION_MODES.EDIT,
            layers: { roots: true, surfaces: true },
            visualState: {
                ...A12_ADULT_DENTITION_FIXTURE,
                selection: { kind: 'surface', toothKey: '46', surfaceCode: 'O' },
            },
            callbacks: { onIntent: (intent) => { intentB = intent; } },
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

        const chartA = container.querySelector('[data-testid="container-a"]');
        const chartB = container.querySelector('[data-testid="container-b"]');
        expect(chartA.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
        expect(chartB.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);

        // Chart A has surface 11:M pressed; 46:O is not pressed
        const selectedA = chartA.querySelector('svg[data-tooth-key="11"] [data-surface-code="M"]');
        const unselectedA = chartA.querySelector('svg[data-tooth-key="46"] [data-surface-code="O"]');
        expect(selectedA).toHaveAttribute('aria-pressed', 'true');
        expect(unselectedA).toHaveAttribute('aria-pressed', 'false');

        // Chart B has surface 46:O pressed; 11:M is not pressed
        const selectedB = chartB.querySelector('svg[data-tooth-key="46"] [data-surface-code="O"]');
        const unselectedB = chartB.querySelector('svg[data-tooth-key="11"] [data-surface-code="M"]');
        expect(selectedB).toHaveAttribute('aria-pressed', 'true');
        expect(unselectedB).toHaveAttribute('aria-pressed', 'false');

        // Clicking surface in Chart A dispatches intent only to instance-alpha
        fireEvent.click(selectedA);
        expect(intentA).not.toBeNull();
        expect(intentA.chartId).toBe('instance-alpha');
        expect(intentA.type).toBe(CHART_INTENT_TYPES.SURFACE_SELECTED);
        expect(intentA.target.toothKey).toBe('11');
        expect(intentA.target.surfaceCode).toBe('M');
        expect(intentB).toBeNull();
    });
});

// ---------------------------------------------------------------------------
// A16-M04 - Root Visual Regression Evidence
// ---------------------------------------------------------------------------

describe('A16-M04 root visual regression evidence', () => {
    const REPRESENTATIVE_TEETH = ['11', '14', '16', '36', '51', '55', '85'];

    const extractStableGeometry = (toothKey) => (
        getRootGeometry(toothKey).map(({ toothKey: key, rootId, path, cervicalAnchors, apexAnchor, displayScale }) => ({
            toothKey: key,
            rootId,
            path,
            cervicalAnchors,
            apexAnchor,
            displayScale,
        }))
    );

    it.each(REPRESENTATIVE_TEETH)('matches snapshot for representative tooth %s', (toothKey) => {
        expect(extractStableGeometry(toothKey)).toMatchSnapshot();
    });

    it('verifies exact anatomical root counts for representative permanent and primary teeth', () => {
        // Permanent representatives: 11 = 1, 14 = 2, 16 = 3, 46 = 2
        expect(DENTAL_ANATOMY_REGISTRY['11'].rootCount).toBe(1);
        expect(getRootGeometry('11')).toHaveLength(1);

        expect(DENTAL_ANATOMY_REGISTRY['14'].rootCount).toBe(2);
        expect(getRootGeometry('14')).toHaveLength(2);

        expect(DENTAL_ANATOMY_REGISTRY['16'].rootCount).toBe(3);
        expect(getRootGeometry('16')).toHaveLength(3);

        expect(DENTAL_ANATOMY_REGISTRY['46'].rootCount).toBe(2);
        expect(getRootGeometry('46')).toHaveLength(2);

        // Representative primary molars: 54/55 = 3, 74/75/84/85 = 2
        expect(DENTAL_ANATOMY_REGISTRY['54'].rootCount).toBe(3);
        expect(getRootGeometry('54')).toHaveLength(3);

        expect(DENTAL_ANATOMY_REGISTRY['55'].rootCount).toBe(3);
        expect(getRootGeometry('55')).toHaveLength(3);

        expect(DENTAL_ANATOMY_REGISTRY['74'].rootCount).toBe(2);
        expect(getRootGeometry('74')).toHaveLength(2);

        expect(DENTAL_ANATOMY_REGISTRY['75'].rootCount).toBe(2);
        expect(getRootGeometry('75')).toHaveLength(2);

        expect(DENTAL_ANATOMY_REGISTRY['84'].rootCount).toBe(2);
        expect(getRootGeometry('84')).toHaveLength(2);

        expect(DENTAL_ANATOMY_REGISTRY['85'].rootCount).toBe(2);
        expect(getRootGeometry('85')).toHaveLength(2);
    });

    it('renders root counts and paths in the DOM correctly on representative teeth', () => {
        const { container } = render(
            <DentalChartSVG
                enableSurfaceSelection
                isPediatric={false}
                readOnly
                showRoots
                teethStatus={{}}
            />,
        );

        const checkRootLayer = (toothKey, expectedCount) => {
            const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
            expect(rootSvg).toBeInTheDocument();
            expect(rootSvg).toHaveAttribute('data-root-count', String(expectedCount));
            const rootPaths = rootSvg.querySelectorAll('[data-layer-role="base-anatomy"] > path');
            expect(rootPaths).toHaveLength(expectedCount);
        };

        checkRootLayer('11', 1);
        checkRootLayer('14', 2);
        checkRootLayer('16', 3);
        checkRootLayer('46', 2);
    });
});

// ---------------------------------------------------------------------------
// A16-M05 - Real Mixed Dentition Render Gate
// ---------------------------------------------------------------------------

describe('A16-M05 real mixed dentition render gate', () => {
    it('verifies real mixed dentition rendering with permanent and primary teeth together', () => {
        // 1. Fixture dentition is 'mixed'
        expect(A12_MIXED_DENTITION_FIXTURE.dentition).toBe('mixed');
        expect(A12_MIXED_DENTITION_FIXTURE.toothOrder).toHaveLength(24);

        // 2. Renderer input dentition is 'mixed'
        const input = createClinicalChartRendererInput({
            chartId: 'regression:a16-mixed-dentition',
            anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
            dentition: A12_MIXED_DENTITION_FIXTURE.dentition,
            visualState: A12_MIXED_DENTITION_FIXTURE,
            notationMode: CHART_NOTATION_MODES.FDI,
            interactionMode: CHART_INTERACTION_MODES.READ_ONLY,
            layers: { roots: true, surfaces: false },
            callbacks: {},
        });
        expect(input.dentition).toBe('mixed');
        expect(input.visualState.toothOrder).toEqual(MIXED_DENTITION_TOOTH_ORDER);

        // Render through the renderer
        const { container } = render(<ClinicalChartRenderer input={input} />);

        // Chart container reflects mixed dentition
        expect(container.firstChild).toHaveAttribute('data-dentition', 'mixed');

        // 3. Permanent tooth 16 renders
        const tooth16 = container.querySelector('svg[data-layer="crown"][data-tooth-key="16"]');
        expect(tooth16).toBeInTheDocument();
        const root16 = container.querySelector('svg[data-layer="roots"][data-tooth-key="16"]');
        expect(root16).toBeInTheDocument();
        expect(root16).toHaveAttribute('data-root-count', '3');

        // 4. Primary tooth 55 renders
        const tooth55 = container.querySelector('svg[data-layer="crown"][data-tooth-key="55"]');
        expect(tooth55).toBeInTheDocument();
        const root55 = container.querySelector('svg[data-layer="roots"][data-tooth-key="55"]');
        expect(root55).toBeInTheDocument();
        expect(root55).toHaveAttribute('data-root-count', '3');

        // 5. Permanent tooth 11 renders
        const tooth11 = container.querySelector('svg[data-layer="crown"][data-tooth-key="11"]');
        expect(tooth11).toBeInTheDocument();
        const root11 = container.querySelector('svg[data-layer="roots"][data-tooth-key="11"]');
        expect(root11).toBeInTheDocument();
        expect(root11).toHaveAttribute('data-root-count', '1');

        // 6. Primary tooth 85 renders
        const tooth85 = container.querySelector('svg[data-layer="crown"][data-tooth-key="85"]');
        expect(tooth85).toBeInTheDocument();
        const root85 = container.querySelector('svg[data-layer="roots"][data-tooth-key="85"]');
        expect(root85).toBeInTheDocument();
        expect(root85).toHaveAttribute('data-root-count', '2');

        // 7. Total rendered crowns equals the explicit mixed toothOrder length (24)
        const renderedCrowns = container.querySelectorAll('svg[data-layer="crown"]');
        expect(renderedCrowns).toHaveLength(MIXED_DENTITION_TOOTH_ORDER.length);
        expect(renderedCrowns).toHaveLength(24);

        // 8. No permanent-only fallback occurs
        // In adult permanent fallback, exactly 32 crowns render, including 18, 28, 38, 48
        expect(renderedCrowns).not.toHaveLength(32);
        expect(container.querySelector('svg[data-layer="crown"][data-tooth-key="18"]')).toBeNull();
        expect(container.querySelector('svg[data-layer="crown"][data-tooth-key="28"]')).toBeNull();
        expect(container.querySelector('svg[data-layer="crown"][data-tooth-key="38"]')).toBeNull();
        expect(container.querySelector('svg[data-layer="crown"][data-tooth-key="48"]')).toBeNull();

        // 9. All tooth keys exist in anatomy registry with no duplicate keys
        const toothOrderKeys = input.visualState.toothOrder;
        expect(new Set(toothOrderKeys).size).toBe(toothOrderKeys.length);
        toothOrderKeys.forEach((key) => {
            expect(DENTAL_ANATOMY_REGISTRY[key]).toBeDefined();
        });
    });
});

// ---------------------------------------------------------------------------
// A16-M06 - RTL Anatomical Orientation Preservation Test
// ---------------------------------------------------------------------------

describe('A16-M06 RTL anatomical orientation preservation', () => {
    it('preserves anatomical LTR orientation internally inside an RTL shell', () => {
        const input = createClinicalChartRendererInput({
            chartId: 'rtl-test-chart',
            anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
            dentition: DENTITIONS.PERMANENT,
            visualState: A12_ADULT_DENTITION_FIXTURE,
            notationMode: CHART_NOTATION_MODES.PALMER,
            interactionMode: CHART_INTERACTION_MODES.READ_ONLY,
            layers: { roots: true, surfaces: false },
            callbacks: {},
        });

        const { container } = render(
            <div dir="rtl" data-testid="rtl-workspace-shell">
                <ClinicalChartRenderer input={input} />
            </div>,
        );

        // Shell container has dir="rtl"
        const shell = container.querySelector('[data-testid="rtl-workspace-shell"]');
        expect(shell).toHaveAttribute('dir', 'rtl');

        // Inner chart canvas explicitly specifies dir="ltr" to protect dental quadrant axis
        const innerCanvas = container.querySelector('[data-notation-mode] > div[dir="ltr"]');
        expect(innerCanvas).toBeInTheDocument();

        // Screen Left displays upper left / patient upper right (teeth 18-11 or Universal 1-8)
        // Screen Right displays upper right / patient upper left (teeth 21-28 or Universal 9-16)
        const crowns = Array.from(container.querySelectorAll('svg[data-layer="crown"]'))
            .map((svg) => svg.getAttribute('data-tooth-key'));
        expect(crowns).toHaveLength(32);
    });
});

// ---------------------------------------------------------------------------
// A16-M07 - Mobile Responsive Behavior Test
// ---------------------------------------------------------------------------

describe('A16-M07 mobile responsive behavior', () => {
    it('supports responsive horizontal scroll and quadrant quick-navigation on mobile', () => {
        const { container } = render(
            <ClinicalChartComparisonCard
                chartId="mobile-comparison-card"
                copy={CLINICAL_CHART_COPY.ar}
                projection={A12_ADULT_DENTITION_FIXTURE}
                subtitle="معاينة الهاتف"
                title="مخطط الأسنان"
            />,
        );

        // Chart container provides horizontal touch scrolling
        const chartWrapper = container.querySelector('[data-dentition]');
        expect(chartWrapper).toHaveClass('overflow-x-auto');
        expect(chartWrapper).toHaveClass('overscroll-x-contain');
        expect(chartWrapper).toHaveClass('touch-pan-x');

        // Minimum width ensures teeth do not wrap awkwardly
        const innerCanvas = chartWrapper.querySelector('div[dir="ltr"]');
        expect(innerCanvas).toHaveClass('min-w-[700px]');

        // Mobile quadrant navigation is available
        const mobileNav = container.querySelector('[data-mobile-quadrant-nav]');
        expect(mobileNav).toBeInTheDocument();
        const quadrantButtons = mobileNav.querySelectorAll('button');
        expect(quadrantButtons).toHaveLength(4);

        // Clicking quadrant button scrolls the target tooth into view
        const targetTooth = container.querySelector('[data-layer="crown"][data-tooth-key="14"]');
        targetTooth.scrollIntoView = vi.fn();
        fireEvent.click(quadrantButtons[0]); // UR -> tooth 14
        expect(targetTooth.scrollIntoView).toHaveBeenCalledWith({
            behavior: 'smooth',
            block: 'nearest',
            inline: 'center',
        });
    });
});

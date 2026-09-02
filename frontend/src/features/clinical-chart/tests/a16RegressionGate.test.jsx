import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalChartRenderer from '../components/ClinicalChartRenderer';
import {
    DENTAL_ANATOMY_REGISTRY,
    DENTITIONS,
    PERMANENT_TOOTH_KEYS,
    PRIMARY_TOOTH_KEYS,
    TOOTH_TYPES,
} from '../domain/dentalAnatomyRegistry';
import { A12_SCENARIO_FIXTURES } from '../fixtures';
import {
    CHART_INTERACTION_MODES,
    CHART_NOTATION_MODES,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';
import { getRootGeometry } from '../rendering/rootGeometry';

// ---------------------------------------------------------------------------
// A16-M01 — Exhaustive Anatomy Registry Contract
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
// A16-M02 — Generic Renderer Smoke Gate
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
        expect(container.querySelectorAll('[data-layer="crown"]').length).toBeGreaterThan(0);

        expect(() => unmount()).not.toThrow();
    });
});

// ---------------------------------------------------------------------------
// A16-M04 — Root Geometry Regression Snapshot
// ---------------------------------------------------------------------------

describe('A16-M04 root geometry regression snapshot', () => {
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
});

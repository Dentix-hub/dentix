import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalChartRenderer from '../components/ClinicalChartRenderer';
import { DENTAL_ANATOMY_REGISTRY } from '../domain/dentalAnatomyRegistry';
import {
    A12_ADULT_DENTITION_FIXTURE,
    A12_BRIDGE_14_15_16_FIXTURE,
    A12_CROWN_FIXTURE,
    A12_DISTAL_CARIES_46_FIXTURE,
    A12_EXISTING_AND_PLANNED_FIXTURE,
    A12_IMPLANT_FIXTURE,
    A12_MISSING_TOOTH_FIXTURE,
    A12_MIXED_DENTITION_FIXTURE,
    A12_MOD_COMPOSITE_46_FIXTURE,
    A12_PRIMARY_DENTITION_FIXTURE,
    A12_RCT_FIXTURE,
    A12_SCENARIO_FIXTURES,
    MIXED_DENTITION_TOOTH_ORDER,
} from '../fixtures';
import {
    CHART_INTERACTION_MODES,
    CHART_NOTATION_MODES,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';

const renderFixture = (projection) => render(
    <ClinicalChartRenderer
        input={createClinicalChartRendererInput({
            chartId: `fixture:${projection.projectionId}`,
            anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
            dentition: projection.dentition,
            visualState: projection,
            notationMode: CHART_NOTATION_MODES.FDI,
            interactionMode: CHART_INTERACTION_MODES.READ_ONLY,
            layers: {
                roots: true,
                surfaces: false,
            },
            callbacks: {},
        })}
    />,
);

const toothCrown = (container, toothKey) => (
    container.querySelector(`svg[data-layer="crown"][data-tooth-key="${toothKey}"]`)
);

const toothRoots = (container, toothKey) => (
    container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`)
);

describe('A12 odontogram scenario fixture matrix', () => {
    it('exposes eleven immutable, projection-valid scenario fixtures', () => {
        const fixtures = Object.values(A12_SCENARIO_FIXTURES);

        expect(fixtures).toHaveLength(11);
        expect(new Set(fixtures.map((fixture) => fixture.projectionId))).toHaveProperty('size', 11);
        fixtures.forEach((fixture) => {
            expect(Object.isFrozen(fixture)).toBe(true);
            expect(fixture.schemaVersion).toBe(1);
        });
    });

    it.each([
        ['adult', A12_ADULT_DENTITION_FIXTURE, 32, 'permanent'],
        ['primary', A12_PRIMARY_DENTITION_FIXTURE, 20, 'primary'],
        ['mixed', A12_MIXED_DENTITION_FIXTURE, MIXED_DENTITION_TOOTH_ORDER.length, 'mixed'],
    ])('renders the %s dentition fixture', (_name, fixture, count, dentition) => {
        const { container } = renderFixture(fixture);
        const crownKeys = Array.from(container.querySelectorAll('[data-layer="crown"]'))
            .map((node) => node.getAttribute('data-tooth-key'));

        expect(container.firstChild).toHaveAttribute('data-dentition', dentition);
        expect(crownKeys).toHaveLength(count);
        if (dentition === 'mixed') {
            expect(crownKeys).toEqual(MIXED_DENTITION_TOOTH_ORDER);
            expect(toothRoots(container, '26')
                .querySelectorAll('[data-layer-role="base-anatomy"] > path')).toHaveLength(3);
            expect(toothRoots(container, '63')
                .querySelectorAll('[data-layer-role="base-anatomy"] > path')).toHaveLength(1);
        } else {
            expect(new Set(crownKeys)).toEqual(new Set(fixture.toothOrder));
        }
    });

    it('renders distal caries on tooth 46 crown only', () => {
        const { container } = renderFixture(A12_DISTAL_CARIES_46_FIXTURE);
        const caries = toothCrown(container, '46')
            .querySelector('[data-effect="surface-caries"][data-target-surface="D"]');

        expect(caries).toBeInTheDocument();
        expect(toothRoots(container, '46').querySelector('[data-effect="surface-caries"]'))
            .not.toBeInTheDocument();
    });

    it('renders the M, O, and D composite surfaces on tooth 46', () => {
        const { container } = renderFixture(A12_MOD_COMPOSITE_46_FIXTURE);
        const surfaces = Array.from(toothCrown(container, '46')
            .querySelectorAll('[data-effect="surface-restoration"]'))
            .map((node) => node.getAttribute('data-target-surface'))
            .sort();

        expect(surfaces).toEqual(['D', 'M', 'O']);
    });

    it('renders RCT against both anatomical roots of tooth 46', () => {
        const { container } = renderFixture(A12_RCT_FIXTURE);
        const rootTargets = Array.from(toothRoots(container, '46')
            .querySelectorAll('[data-effect="endodontic-therapy"]'))
            .map((node) => node.getAttribute('data-target-root'))
            .sort();

        expect(rootTargets).toEqual(['distal', 'mesial']);
    });

    it('renders a completed prosthetic crown fixture', () => {
        const { container } = renderFixture(A12_CROWN_FIXTURE);
        const crown = toothCrown(container, '36')
            .querySelector('[data-effect="prosthetic-crown"][data-phase="completed"]');

        expect(crown).toBeInTheDocument();
    });

    it('renders a missing-tooth lifecycle fixture', () => {
        const { container } = renderFixture(A12_MISSING_TOOTH_FIXTURE);
        const missing = toothCrown(container, '38')
            .querySelector('[data-effect="missing"]');

        expect(missing).toBeInTheDocument();
    });

    it('renders an implant fixture and crown while hiding natural roots', () => {
        const { container } = renderFixture(A12_IMPLANT_FIXTURE);
        const roots = toothRoots(container, '23');
        const crown = toothCrown(container, '23');

        expect(roots.querySelector('[data-layer-role="base-anatomy"]')).toHaveAttribute('opacity', '0');
        expect(roots.querySelector('[data-effect="implant-fixture"]')).toBeInTheDocument();
        expect(crown.querySelector('[data-effect="implant-crown"]')).toBeInTheDocument();
    });

    it('renders the 14-15-16 bridge with a missing pontic at tooth 15', () => {
        const { container } = renderFixture(A12_BRIDGE_14_15_16_FIXTURE);

        ['14', '15', '16'].forEach((toothKey) => {
            expect(toothCrown(container, toothKey).querySelector('[data-effect="bridge-unit"]'))
                .toBeInTheDocument();
        });
        expect(toothCrown(container, '15').querySelector('[data-effect="missing"]'))
            .toBeInTheDocument();
    });

    it('renders existing and planned layers simultaneously in deterministic order', () => {
        const { container } = renderFixture(A12_EXISTING_AND_PLANNED_FIXTURE);
        const crown = toothCrown(container, '46');
        const existingLayer = crown.querySelector('[data-layer-role="existing-completed-work"]');
        const plannedLayer = crown.querySelector('[data-layer-role="planned-active-work"]');

        expect(existingLayer.querySelector('[data-effect="surface-restoration"][data-phase="completed"]'))
            .toBeInTheDocument();
        expect(plannedLayer.querySelector('[data-effect="prosthetic-crown"][data-phase="planned"]'))
            .toBeInTheDocument();
        expect(Number(existingLayer.getAttribute('data-layer-index')))
            .toBeLessThan(Number(plannedLayer.getAttribute('data-layer-index')));
    });
});

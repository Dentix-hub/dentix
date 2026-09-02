import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DentalChartSVG from '@/features/dental/DentalChartSVG';
import ClinicalChartRenderer from '../components/ClinicalChartRenderer';
import { createClinicalChartRendererInput } from '../rendering/ClinicalChartRendererAdapter';
import {
    ADULT_DENTITION_FIXTURE,
    BRIDGE_FIXTURE,
    CARIES_ON_SURFACE_FIXTURE,
    CLINICAL_DEMO_FIXTURES,
    CROWN_FIXTURE,
    EXTRACTION_COMPLETED_FIXTURE,
    EXTRACTION_PLANNED_FIXTURE,
    IMPLANT_FIXTURE,
    MIXED_DENTITION_FIXTURE,
    MOD_RESTORATION_FIXTURE,
    PRIMARY_DENTITION_FIXTURE,
    RCT_FIXTURE,
} from '../fixtures';
import { resolveClinicalChartVisuals } from '../domain/visualRuleRegistry';

describe('Phase A12 — Target Clinical Coverage Demo Fixtures', () => {
    describe('A12-M01: Adult dentition fixture', () => {
        it('loads full 32 permanent teeth without errors', () => {
            expect(ADULT_DENTITION_FIXTURE.toothOrder).toHaveLength(32);
            expect(ADULT_DENTITION_FIXTURE.dentition).toBe('permanent');

            const input = createClinicalChartRendererInput({
                chartId: 'demo-adult',
                dentition: 'permanent',
                layers: { roots: true, surfaces: true },
            });
            const { container } = render(<ClinicalChartRenderer input={input} />);

            expect(container.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
            expect(container.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(32);
        });
    });

    describe('A12-M02: Primary dentition fixture', () => {
        it('loads complete 20 primary teeth for pediatric charts', () => {
            expect(PRIMARY_DENTITION_FIXTURE.toothOrder).toHaveLength(20);
            expect(PRIMARY_DENTITION_FIXTURE.dentition).toBe('primary');

            const input = createClinicalChartRendererInput({
                chartId: 'demo-primary',
                dentition: 'primary',
                layers: { roots: true, surfaces: true },
            });
            const { container } = render(<ClinicalChartRenderer input={input} />);

            expect(container.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(20);
            expect(container.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(20);
        });
    });

    describe('A12-M03: Mixed dentition fixture', () => {
        it('loads mixed dentition projection with explicit toothOrder and mixed teeth keys', () => {
            expect(MIXED_DENTITION_FIXTURE.dentition).toBe('mixed');
            expect(MIXED_DENTITION_FIXTURE.toothOrder.length).toBeGreaterThanOrEqual(20);

            // Contains both permanent and primary tooth keys
            expect(MIXED_DENTITION_FIXTURE.toothOrder).toContain('16'); // Permanent molar
            expect(MIXED_DENTITION_FIXTURE.toothOrder).toContain('55'); // Primary molar
            expect(MIXED_DENTITION_FIXTURE.toothOrder).toContain('11'); // Permanent incisor
            expect(MIXED_DENTITION_FIXTURE.toothOrder).toContain('85'); // Primary molar
        });
    });

    describe('A12-M04: Caries-on-surface fixture', () => {
        it('resolves localized caries visual rules targeted to specific tooth surfaces', () => {
            const visuals = resolveClinicalChartVisuals(CARIES_ON_SURFACE_FIXTURE);

            expect(visuals['46']).toBeDefined();
            const instruction46 = visuals['46'].instructions.find((i) => i.code === 'CARIES');
            expect(instruction46).toBeDefined();
            expect(instruction46.target.kind).toBe('surface');
            expect(instruction46.target.surfaceCode).toBe('O');

            expect(visuals['16']).toBeDefined();
            const instruction16 = visuals['16'].instructions.find((i) => i.code === 'CARIES');
            expect(instruction16).toBeDefined();
            expect(instruction16.target.surfaceCode).toBe('M');

            expect(visuals['21']).toBeDefined();
            const instruction21 = visuals['21'].instructions.find((i) => i.code === 'CARIES');
            expect(instruction21).toBeDefined();
            expect(instruction21.target.surfaceCode).toBe('D');
        });
    });

    describe('A12-M05: MOD restoration fixture', () => {
        it('resolves multi-surface composite restoration visual rules covering M, O, and D', () => {
            const visuals = resolveClinicalChartVisuals(MOD_RESTORATION_FIXTURE);

            expect(visuals['46']).toBeDefined();
            const compositeInstructions = visuals['46'].instructions.filter(
                (i) => i.code === 'REST_COMPOSITE',
            );
            expect(compositeInstructions).toHaveLength(3);

            const surfaceCodes = compositeInstructions.map((i) => i.target.surfaceCode);
            expect(surfaceCodes).toContain('M');
            expect(surfaceCodes).toContain('O');
            expect(surfaceCodes).toContain('D');
        });
    });

    describe('A12-M06: RCT fixture', () => {
        it('resolves root canal therapy visual rules targeted to root structures', () => {
            const visuals = resolveClinicalChartVisuals(RCT_FIXTURE);

            expect(visuals['11']).toBeDefined();
            const rct11 = visuals['11'].instructions.find((i) => i.code === 'ENDO_RCT');
            expect(rct11).toBeDefined();
            expect(rct11.target.kind).toBe('root');
            expect(rct11.target.rootId).toBe('single');
            expect(rct11.phase).toBe('completed');

            expect(visuals['36']).toBeDefined();
            const rct36 = visuals['36'].instructions.filter((i) => i.code === 'ENDO_RCT');
            expect(rct36).toHaveLength(2);
        });
    });

    describe('A12-M07: Crown fixture', () => {
        it('resolves completed and planned full-coverage crown visual rules', () => {
            const visuals = resolveClinicalChartVisuals(CROWN_FIXTURE);

            expect(visuals['14']).toBeDefined();
            const crown14 = visuals['14'].instructions.find((i) => i.code === 'PROS_CROWN');
            expect(crown14).toBeDefined();
            expect(crown14.phase).toBe('completed');
            expect(crown14.target.kind).toBe('tooth');

            expect(visuals['21']).toBeDefined();
            const crown21 = visuals['21'].instructions.find((i) => i.code === 'PROS_CROWN');
            expect(crown21).toBeDefined();
            expect(crown21.phase).toBe('planned');
            expect(crown21.target.kind).toBe('tooth');
        });
    });

    describe('A12-M08: Bridge fixture', () => {
        it('resolves multi-unit bridge including abutment crowns and missing pontic', () => {
            const visuals = resolveClinicalChartVisuals(BRIDGE_FIXTURE);

            // Abutment tooth 21
            expect(visuals['21'].instructions.some((i) => i.code === 'PROS_CROWN')).toBe(true);

            // Pontic tooth 22
            expect(visuals['22'].instructions.some((i) => i.code === 'PROS_BRIDGE')).toBe(true);
            expect(visuals['22'].instructions.some((i) => i.code === 'MISSING')).toBe(true);

            // Abutment tooth 23
            expect(visuals['23'].instructions.some((i) => i.code === 'PROS_CROWN')).toBe(true);
        });
    });

    describe('A12-M09: Implant fixture', () => {
        it('resolves implant fixture and implant crown rules replacing natural roots', () => {
            const visuals = resolveClinicalChartVisuals(IMPLANT_FIXTURE);

            expect(visuals['36']).toBeDefined();
            expect(visuals['36'].instructions.some((i) => i.code === 'IMPLANT_FIXTURE')).toBe(true);
            expect(visuals['36'].instructions.some((i) => i.code === 'IMPLANT_CROWN')).toBe(true);
            expect(visuals['36'].instructions.some((i) => i.code === 'MISSING')).toBe(true);
        });
    });

    describe('A12-M10: Extraction planned fixture', () => {
        it('resolves planned surgical extraction visual marker', () => {
            const visuals = resolveClinicalChartVisuals(EXTRACTION_PLANNED_FIXTURE);

            expect(visuals['38']).toBeDefined();
            const extractPlanned = visuals['38'].instructions.find(
                (i) => i.code === 'SURG_EXTRACTION',
            );
            expect(extractPlanned).toBeDefined();
            expect(extractPlanned.phase).toBe('planned');
            expect(extractPlanned.target.kind).toBe('tooth');
        });
    });

    describe('A12-M11: Extraction completed fixture', () => {
        it('resolves missing and completed extraction visual markers', () => {
            const visuals = resolveClinicalChartVisuals(EXTRACTION_COMPLETED_FIXTURE);

            expect(visuals['18']).toBeDefined();
            expect(visuals['18'].instructions.some((i) => i.code === 'MISSING')).toBe(true);

            expect(visuals['28']).toBeDefined();
            expect(visuals['28'].instructions.some((i) => i.code === 'SURG_EXTRACTION')).toBe(true);
            expect(visuals['28'].instructions.some((i) => i.code === 'EXTRACTED')).toBe(true);
        });
    });

    describe('Complete registry verification', () => {
        it('exports all 11 scenarios in CLINICAL_DEMO_FIXTURES catalog', () => {
            const expectedKeys = [
                'adultDentition',
                'primaryDentition',
                'mixedDentition',
                'cariesOnSurface',
                'modRestoration',
                'rct',
                'crown',
                'bridge',
                'implant',
                'extractionPlanned',
                'extractionCompleted',
            ];
            expect(Object.keys(CLINICAL_DEMO_FIXTURES)).toEqual(expectedKeys);
        });
    });
});

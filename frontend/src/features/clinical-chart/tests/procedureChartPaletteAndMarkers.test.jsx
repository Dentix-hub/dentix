import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ClinicalChartRenderer from '../components/ClinicalChartRenderer';
import ToothProcedureMarkers from '../rendering/ToothProcedureMarkers';
import { adaptWorkspaceSnapshotToRenderer } from '../adapters/workspaceSnapshotAdapter';
import {
    MAX_VISIBLE_PROCEDURE_MARKERS,
    PROJECTION_TARGET_KINDS,
    PROJECTION_VISUAL_PHASES,
    createToothVisualState,
} from '../domain/clinicalChartProjection';
import {
    CARIES_FINDING_FILL,
    PROCEDURE_CHART_PALETTE,
    PROCEDURE_CHART_PALETTE_KEYS,
    PROCEDURE_CHART_PALETTE_LIST,
    computeColorDistanceFromCaries,
    computeContrastRatio,
    resolveMarkerPaletteColor,
    resolvePaletteColor,
} from '../domain/procedureChartPalette';
import {
    COLOR_OVERRIDABLE_PROCEDURE_EFFECTS,
    FINDING_CODES,
    PROCEDURE_CODES,
    TOOTH_LIFECYCLE_CODES,
    VISUAL_LAYER_ROLES,
    VISUAL_RULE_REGISTRY,
    resolveClinicalChartVisuals,
    resolveToothVisualInstructions,
} from '../domain/visualRuleRegistry';
import { VISUAL_RULE_DEMO_PROJECTION } from '../fixtures/visualRuleDemoProjection';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('U4B — procedureChartPalette integrity & backend parity', () => {
    it('defines exactly 12 frozen palette keys with fill, stroke, labelAr, and labelEn', () => {
        expect(PROCEDURE_CHART_PALETTE_KEYS).toEqual([
            'blue',
            'teal',
            'green',
            'lime',
            'amber',
            'orange',
            'purple',
            'indigo',
            'pink',
            'cyan',
            'slate',
            'brown',
        ]);
        expect(PROCEDURE_CHART_PALETTE_LIST).toHaveLength(12);
        expect(Object.isFrozen(PROCEDURE_CHART_PALETTE)).toBe(true);
        expect(Object.isFrozen(PROCEDURE_CHART_PALETTE_KEYS)).toBe(true);

        PROCEDURE_CHART_PALETTE_LIST.forEach((swatch) => {
            expect(Object.isFrozen(swatch)).toBe(true);
            expect(swatch.key).toBeTruthy();
            expect(swatch.fill).toMatch(/^#[0-9a-f]{6}$/i);
            expect(swatch.stroke).toMatch(/^#[0-9a-f]{6}$/i);
            expect(swatch.labelAr.length).toBeGreaterThan(0);
            expect(swatch.labelEn.length).toBeGreaterThan(0);
        });
    });

    it('stays in 100% parity with backend CHART_STYLE_COLOR_KEYS in backend/clinical/chart_styles.py', () => {
        const backendChartStylesPath = path.resolve(
            __dirname,
            '../../../../../backend/clinical/chart_styles.py',
        );
        const backendSource = fs.readFileSync(backendChartStylesPath, 'utf8');
        const blockMatch = backendSource.match(
            /CHART_STYLE_COLOR_KEYS[^=]*=\s*\(([\s\S]*?)\)/,
        );
        expect(blockMatch).not.toBeNull();
        const backendKeys = Array.from(blockMatch[1].matchAll(/"([a-z_]+)"/g)).map((m) => m[1]);

        expect(PROCEDURE_CHART_PALETTE_KEYS).toEqual(backendKeys);
    });

    it('satisfies WCAG contrast >= 3.0:1 for stroke vs white (#ffffff) and stays distinct from CARIES red (#b91c1c)', () => {
        expect(VISUAL_RULE_REGISTRY.finding.CARIES.presentation.fill).toBe(CARIES_FINDING_FILL);

        const reportRows = PROCEDURE_CHART_PALETTE_LIST.map((swatch) => {
            const strokeContrastVsWhite = computeContrastRatio(swatch.stroke, '#ffffff');
            const fillContrastVsWhite = computeContrastRatio(swatch.fill, '#ffffff');
            const distanceFromCaries = computeColorDistanceFromCaries(swatch.fill, CARIES_FINDING_FILL);
            return {
                key: swatch.key,
                fill: swatch.fill,
                stroke: swatch.stroke,
                strokeContrastVsWhite,
                fillContrastVsWhite,
                distanceFromCaries,
            };
        });

        reportRows.forEach((row) => {
            expect(row.strokeContrastVsWhite).toBeGreaterThanOrEqual(3.0);
            // Minimum Euclidean RGB distance from #b91c1c is > 50 (none in caries red range)
            expect(row.distanceFromCaries).toBeGreaterThanOrEqual(50);
        });
    });

    it('resolves known keys and returns null for unknown, empty, or non-string keys without throwing', () => {
        expect(resolvePaletteColor('orange')).toEqual({
            key: 'orange',
            fill: '#ea580c',
            stroke: '#c2410c',
            labelAr: 'برتقالي',
            labelEn: 'Orange',
        });
        expect(resolvePaletteColor('  TEAL ')).toBe(PROCEDURE_CHART_PALETTE.teal);
        expect(resolvePaletteColor(null)).toBeNull();
        expect(resolvePaletteColor(undefined)).toBeNull();
        expect(resolvePaletteColor('')).toBeNull();
        expect(resolvePaletteColor('   ')).toBeNull();
        expect(resolvePaletteColor('red')).toBeNull();
        expect(resolvePaletteColor('unknown-color')).toBeNull();
        expect(resolvePaletteColor(123)).toBeNull();
        expect(resolvePaletteColor({})).toBeNull();

        expect(resolveMarkerPaletteColor('unknown')).toBe(PROCEDURE_CHART_PALETTE.teal);
        expect(resolveMarkerPaletteColor(null)).toBe(PROCEDURE_CHART_PALETTE.teal);
        expect(resolveMarkerPaletteColor('purple')).toBe(PROCEDURE_CHART_PALETTE.purple);
    });
});

describe('U4B — clinicalChartProjection styleColorKey & markers normalization', () => {
    it('normalizes valid styleColorKey on procedure entries and ignores unknown keys', () => {
        const state = createToothVisualState({
            toothKey: '16',
            findings: [{
                code: FINDING_CODES.CARIES,
                styleColorKey: 'orange',
                targets: [{ kind: PROJECTION_TARGET_KINDS.SURFACE, toothKey: '16', surfaceCode: 'O' }],
            }],
            procedures: [
                {
                    visualId: 'proc-styled',
                    code: PROCEDURE_CODES.REST_COMPOSITE,
                    styleColorKey: 'orange',
                    targets: [{ kind: PROJECTION_TARGET_KINDS.SURFACE, toothKey: '16', surfaceCode: 'M' }],
                },
                {
                    visualId: 'proc-unknown-style',
                    code: PROCEDURE_CODES.PROS_CROWN,
                    styleColorKey: 'crimson-invalid',
                    targets: [{ kind: PROJECTION_TARGET_KINDS.TOOTH, toothKey: '16' }],
                },
            ],
        });

        expect(state.findings[0]).not.toHaveProperty('styleColorKey');
        expect(state.procedures[0].styleColorKey).toBe('orange');
        expect(state.procedures[1]).not.toHaveProperty('styleColorKey');
    });

    it('normalizes per-tooth markers, ignores unknown marker colorKey, and caps visible markers at 3 with +N overflow info', () => {
        const state = createToothVisualState({
            toothKey: '16',
            markers: [
                { marker_id: 'm-1', procedure_name: 'تبييض', color_key: 'teal', surface_codes: ['B', 'invalid'] },
                { marker_id: 'm-2', procedure_name: 'فلورايد', color_key: 'unknown-hue', phase: 'planned' },
                { marker_id: 'm-3', procedure_name: 'تنظيف جير', color_key: 'amber' },
                { marker_id: 'm-4', procedure_name: 'حساسية', color_key: 'purple' },
                { marker_id: 'm-5', procedure_name: 'متابعة', color_key: 'green' },
            ],
        });

        expect(state.markers).toHaveLength(MAX_VISIBLE_PROCEDURE_MARKERS);
        expect(state.markerOverflowCount).toBe(2);
        expect(state.markers[0]).toEqual({
            markerId: 'm-1',
            procedureName: 'تبييض',
            colorKey: 'teal',
            toothKey: '16',
            surfaceCodes: ['B'],
            phase: 'completed',
            sourceId: null,
        });
        expect(state.markers[1].colorKey).toBeNull();
        expect(state.markers[1].phase).toBe('planned');
        expect(Object.isFrozen(state.markers)).toBe(true);
        expect(Object.isFrozen(state.markers[0])).toBe(true);
    });
});

describe('U4B — visualRuleRegistry color override & golden equality', () => {
    it('overrides only fill and stroke for all 7 color-overridable procedure effects while keeping opacity, width, phase, and layer role unchanged', () => {
        const effectCases = [
            {
                code: PROCEDURE_CODES.REST_COMPOSITE,
                effect: 'surface-restoration',
                target: { kind: PROJECTION_TARGET_KINDS.SURFACE, toothKey: '16', surfaceCode: 'O' },
            },
            {
                code: PROCEDURE_CODES.ENDO_RCT,
                effect: 'endodontic-therapy',
                target: { kind: PROJECTION_TARGET_KINDS.ROOT, toothKey: '16', rootId: 'palatal' },
            },
            {
                code: PROCEDURE_CODES.PROS_CROWN,
                effect: 'prosthetic-crown',
                target: { kind: PROJECTION_TARGET_KINDS.TOOTH, toothKey: '16' },
            },
            {
                code: PROCEDURE_CODES.PROS_BRIDGE,
                effect: 'bridge-unit',
                target: { kind: PROJECTION_TARGET_KINDS.TOOTH, toothKey: '16' },
            },
            {
                code: PROCEDURE_CODES.IMPLANT_FIXTURE,
                effect: 'implant-fixture',
                target: { kind: PROJECTION_TARGET_KINDS.TOOTH, toothKey: '16' },
            },
            {
                code: PROCEDURE_CODES.IMPLANT_CROWN,
                effect: 'implant-crown',
                target: { kind: PROJECTION_TARGET_KINDS.TOOTH, toothKey: '16' },
            },
            {
                code: PROCEDURE_CODES.SURG_EXTRACTION,
                effect: 'surgical-extraction',
                target: { kind: PROJECTION_TARGET_KINDS.TOOTH, toothKey: '16' },
            },
        ];

        expect(effectCases.map((c) => c.effect)).toEqual(COLOR_OVERRIDABLE_PROCEDURE_EFFECTS);

        effectCases.forEach(({ code, effect, target }) => {
            for (const phase of [
                PROJECTION_VISUAL_PHASES.COMPLETED,
                PROJECTION_VISUAL_PHASES.PLANNED,
                PROJECTION_VISUAL_PHASES.ACTIVE,
            ]) {
                const defaultState = createToothVisualState({
                    toothKey: '16',
                    procedures: [{ visualId: `v-${code}`, code, phase, targets: [target] }],
                });
                const styledState = createToothVisualState({
                    toothKey: '16',
                    procedures: [{
                        visualId: `v-${code}`,
                        code,
                        phase,
                        styleColorKey: 'teal',
                        targets: [target],
                    }],
                });

                const defaultInst = resolveToothVisualInstructions(defaultState).instructions[1];
                const styledInst = resolveToothVisualInstructions(styledState).instructions[1];

                expect(styledInst.effect).toBe(effect);
                expect(styledInst.layerRole).toBe(defaultInst.layerRole);
                expect(styledInst.layerIndex).toBe(defaultInst.layerIndex);
                expect(styledInst.order).toBe(defaultInst.order);
                expect(styledInst.presentation.fill).toBe(PROCEDURE_CHART_PALETTE.teal.fill);
                expect(styledInst.presentation.stroke).toBe(PROCEDURE_CHART_PALETTE.teal.stroke);
                expect(styledInst.presentation.fillOpacity).toBe(defaultInst.presentation.fillOpacity);
                expect(styledInst.presentation.strokeWidth).toBe(defaultInst.presentation.strokeWidth);
                expect(styledInst.presentation.strokeDasharray).toBe(defaultInst.presentation.strokeDasharray);
            }
        });
    });

    it('never overrides findings or lifecycle rules and produces byte-identical instructions when styleColorKey is absent or unknown', () => {
        const baseline = resolveClinicalChartVisuals(VISUAL_RULE_DEMO_PROJECTION);

        const stateWithoutStyle = createToothVisualState({
            toothKey: '46',
            lifecycle: TOOTH_LIFECYCLE_CODES.IMPACTED,
            findings: [{
                visualId: 'f-1',
                code: FINDING_CODES.CARIES,
                targets: [{ kind: PROJECTION_TARGET_KINDS.SURFACE, toothKey: '46', surfaceCode: 'D' }],
            }],
            procedures: [{
                visualId: 'p-1',
                code: PROCEDURE_CODES.REST_COMPOSITE,
                targets: [{ kind: PROJECTION_TARGET_KINDS.SURFACE, toothKey: '46', surfaceCode: 'O' }],
            }],
        });

        const stateWithUnknownStyle = {
            ...stateWithoutStyle,
            findings: [{
                ...stateWithoutStyle.findings[0],
                styleColorKey: 'orange',
            }],
            procedures: [{
                ...stateWithoutStyle.procedures[0],
                styleColorKey: 'not-a-palette-key',
            }],
        };

        const visualsWithoutStyle = resolveToothVisualInstructions(stateWithoutStyle);
        const visualsWithUnknownStyle = resolveToothVisualInstructions(stateWithUnknownStyle);

        expect(visualsWithUnknownStyle).toEqual(visualsWithoutStyle);
        expect(visualsWithUnknownStyle.byLayer[VISUAL_LAYER_ROLES.FINDINGS][0].presentation.fill)
            .toBe(CARIES_FINDING_FILL);
        expect(baseline[44].byLayer[VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK][0].presentation)
            .toEqual({
                fill: '#2563eb',
                fillOpacity: 0.92,
                stroke: '#1d4ed8',
                strokeWidth: 1.2,
            });
    });
});

describe('U4B — ToothProcedureMarkers & end-to-end chart rendering', () => {
    it('renders N markers (up to 3), +N overflow badge, accessible <title>, non-color-only diamond glyph, and pointer-events: none', () => {
        const markers = [
            { markerId: 'm1', procedureName: 'تبييض ليزر', colorKey: 'teal', phase: 'completed' },
            { markerId: 'm2', procedureName: 'طلاء فلورايد', colorKey: 'amber', phase: 'planned' },
            { markerId: 'm3', procedureName: 'تلميع', colorKey: 'purple', phase: 'completed' },
            { markerId: 'm4', procedureName: 'إزالة تصبغات', colorKey: 'green', phase: 'completed' },
            { markerId: 'm5', procedureName: 'متابعة لثة', colorKey: 'blue', phase: 'completed' },
        ];

        const { container, rerender } = render(
            <ToothProcedureMarkers arch="upper" markers={markers} toothKey="16" />,
        );

        const rootSvg = screen.getByTestId('tooth-procedure-markers-16');
        expect(rootSvg).toHaveAttribute('pointer-events', 'none');
        expect(rootSvg).toHaveClass('pointer-events-none');
        expect(rootSvg).toHaveAttribute('data-arch', 'upper');
        expect(rootSvg).toHaveAttribute('data-edge', 'bottom');
        expect(rootSvg).toHaveAttribute('data-marker-count', '3');
        expect(rootSvg).toHaveAttribute('data-overflow-count', '2');
        expect(rootSvg.querySelector('[data-marker-cy]')).toHaveAttribute('data-marker-cy', '54');

        // Verify 3 marker nodes with <title>, halo, dot, and inner diamond glyph
        const marker0 = screen.getByTestId('tooth-procedure-marker-16-0');
        expect(marker0.querySelector('title')).toHaveTextContent('تبييض ليزر');
        expect(marker0.querySelector('[data-marker-dot="true"]'))
            .toHaveAttribute('fill', PROCEDURE_CHART_PALETTE.teal.fill);
        expect(marker0.querySelector('[data-marker-halo="true"]'))
            .toHaveAttribute('stroke', PROCEDURE_CHART_PALETTE.teal.stroke);
        expect(marker0.querySelector('[data-marker-glyph="diamond"]')).toBeInTheDocument();

        const marker1 = screen.getByTestId('tooth-procedure-marker-16-1');
        expect(marker1.querySelector('title')).toHaveTextContent('طلاء فلورايد');
        expect(marker1.querySelector('[data-marker-halo="true"]'))
            .toHaveAttribute('stroke-dasharray', '2 1');

        const overflow = screen.getByTestId('tooth-procedure-marker-overflow-16');
        expect(overflow).toHaveTextContent('+2');

        // Lower arch positions markers on the top outer edge (cy = 5)
        rerender(<ToothProcedureMarkers arch="lower" markers={markers.slice(0, 2)} toothKey="46" />);
        const lowerSvg = screen.getByTestId('tooth-procedure-markers-46');
        expect(lowerSvg).toHaveAttribute('data-arch', 'lower');
        expect(lowerSvg).toHaveAttribute('data-edge', 'top');
        expect(lowerSvg.querySelector('[data-marker-cy]')).toHaveAttribute('data-marker-cy', '5');
        expect(container.querySelector('[data-testid="tooth-procedure-marker-overflow-46"]')).toBeNull();
    });

    it('acceptance: paints surface-restoration with styleColorKey="orange" and renders a teal marker dot via workspaceSnapshotAdapter + ClinicalChartRenderer without intercepting clicks', () => {
        const onToothClick = vi.fn();
        const onSurfaceClick = vi.fn();
        const snapshot = {
            schema_version: 1,
            projection_id: 'u4b-acceptance-snap',
            patient_id: 77,
            tenant_id: 1,
            read_mode: 'LEGACY_ONLY',
            coverage: { teeth: 'COMPLETE', treatments: 'COMPLETE', sessions: 'COMPLETE' },
            warnings: [],
            work_items: [],
            teeth: {
                '16': {
                    tooth_key: '16',
                    lifecycle: 'PRESENT',
                    findings: [],
                    procedures: [
                        {
                            visual_id: 'legacy:treatment:501:visual',
                            code: 'REST_COMPOSITE',
                            phase: 'completed',
                            style_color_key: 'orange',
                            targets: [
                                { kind: 'surface', tooth_key: '16', surface_code: 'M' },
                                { kind: 'surface', tooth_key: '16', surface_code: 'O' },
                            ],
                        },
                    ],
                    markers: [
                        {
                            marker_id: 'legacy:treatment:502:marker:16',
                            procedure_name: 'تبييض منزلي',
                            color_key: 'teal',
                            tooth_key: '16',
                            surface_codes: [],
                            phase: 'completed',
                            source_id: 502,
                        },
                    ],
                },
            },
        };

        const adapted = adaptWorkspaceSnapshotToRenderer(snapshot, {
            showRoots: true,
            showSurfaces: true,
            onToothClick,
            onSurfaceClick,
        });

        expect(adapted.isEmpty).toBe(false);
        expect(adapted.projection.teeth['16'].procedures[0].styleColorKey).toBe('orange');
        expect(adapted.projection.teeth['16'].markers).toHaveLength(1);
        expect(adapted.projection.teeth['16'].markers[0].colorKey).toBe('teal');

        const { container } = render(
            <div dir="rtl">
                <ClinicalChartRenderer input={adapted.rendererInput} />
            </div>,
        );

        const crown16 = container.querySelector('svg[data-layer="crown"][data-tooth-key="16"]');
        const surfaceM = crown16.querySelector(
            '[data-effect="surface-restoration"][data-target-surface="M"] path',
        );
        const surfaceO = crown16.querySelector(
            '[data-effect="surface-restoration"][data-target-surface="O"] path',
        );

        expect(surfaceM).toHaveAttribute('fill', '#ea580c');
        expect(surfaceM).toHaveAttribute('stroke', '#c2410c');
        expect(surfaceO).toHaveAttribute('fill', '#ea580c');
        expect(surfaceO).toHaveAttribute('stroke', '#c2410c');

        const markerGroup = screen.getByTestId('tooth-procedure-marker-16-0');
        expect(markerGroup.querySelector('title')).toHaveTextContent('تبييض منزلي');
        expect(markerGroup.querySelector('[data-marker-dot="true"]'))
            .toHaveAttribute('fill', '#0d9488');
        expect(markerGroup.querySelector('[data-marker-dot="true"]'))
            .toHaveAttribute('stroke', '#0f766e');

        // Clicking a surface still fires onSurfaceClick (markers have pointer-events: none)
        const interactiveMesial = crown16.querySelector('[data-layer="surfaces"] [data-surface-code="M"]');
        fireEvent.click(interactiveMesial);
        expect(onSurfaceClick).toHaveBeenCalledWith({
            kind: 'surface',
            toothKey: '16',
            surfaceCode: 'M',
        });
    });

    it('recognizes a tooth with only markers as non-empty clinical evidence in workspaceSnapshotAdapter', () => {
        const snapshot = {
            schema_version: 1,
            projection_id: 'marker-only-snap',
            read_mode: 'LEGACY_ONLY',
            teeth: {
                '55': {
                    tooth_key: '55',
                    lifecycle: 'PRESENT',
                    findings: [],
                    procedures: [],
                    markers: [
                        {
                            marker_id: 'm-55',
                            procedure_name: 'جلسة فلورايد',
                            color_key: 'green',
                            tooth_key: '55',
                        },
                    ],
                },
            },
        };

        const adapted = adaptWorkspaceSnapshotToRenderer(snapshot);
        expect(adapted.isEmpty).toBe(false);
        expect(adapted.dentition).toBe('mixed');
        expect(adapted.projection.teeth['55'].markers).toHaveLength(1);
    });
});

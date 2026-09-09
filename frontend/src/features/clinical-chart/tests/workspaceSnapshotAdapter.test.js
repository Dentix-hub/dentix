import { describe, expect, it, vi } from 'vitest';
import { adaptWorkspaceSnapshotToRenderer } from '../adapters/workspaceSnapshotAdapter';
import { PROJECTION_DENTITIONS } from '../domain/clinicalChartProjection';
import { FINDING_CODES, PROCEDURE_CODES, TOOTH_LIFECYCLE_CODES } from '../domain/clinicalVisualCodes';

describe('workspaceSnapshotAdapter', () => {
    const createBaseSnapshot = (overrides = {}) => ({
        schema_version: 1,
        projection_id: 'cws-snap-101',
        patient_id: 101,
        tenant_id: 1,
        read_mode: 'VNEXT_PRIMARY',
        coverage: {
            teeth: 'COMPLETE',
            treatments: 'COMPLETE',
            sessions: 'COMPLETE',
        },
        warnings: [],
        teeth: {},
        work_items: [],
        generated_at: '2026-09-08T12:00:00Z',
        effective_at: '2026-09-08T12:00:00Z',
        ...overrides,
    });

    it('adapts permanent dentition by default with 32 teeth', () => {
        const snapshot = createBaseSnapshot();
        const adapted = adaptWorkspaceSnapshotToRenderer(snapshot);

        expect(adapted.dentition).toBe(PROJECTION_DENTITIONS.PERMANENT);
        expect(adapted.projection.toothOrder).toHaveLength(32);
        expect(Object.keys(adapted.projection.teeth)).toHaveLength(32);
        expect(adapted.projection.teeth['11']).toBeDefined();
        expect(adapted.projection.teeth['11'].lifecycle).toBe('PRESENT');
        expect(adapted.readMode).toBe('VNEXT_PRIMARY');
        expect(adapted.isFallback).toBe(false);
        expect(adapted.isPartial).toBe(false);
        expect(adapted.isEmpty).toBe(true);
    });

    it('adapts pediatric dentition when isPediatric is true', () => {
        const snapshot = createBaseSnapshot();
        const adapted = adaptWorkspaceSnapshotToRenderer(snapshot, { isPediatric: true });

        expect(adapted.dentition).toBe(PROJECTION_DENTITIONS.PRIMARY);
        expect(adapted.projection.toothOrder).toHaveLength(20);
        expect(Object.keys(adapted.projection.teeth)).toHaveLength(20);
        expect(adapted.projection.teeth['51']).toBeDefined();
        expect(adapted.projection.teeth['11']).toBeUndefined();
    });

    it('resolves to mixed dentition when both primary and permanent teeth have clinical data', () => {
        const snapshot = createBaseSnapshot({
            teeth: {
                '16': {
                    tooth_key: '16',
                    procedures: [
                        {
                            visual_id: 've-1',
                            code: 'REST_COMPOSITE',
                            phase: 'completed',
                            targets: [{ kind: 'tooth', tooth_key: '16' }],
                        },
                    ],
                },
                '55': {
                    tooth_key: '55',
                    findings: [
                        {
                            visual_id: 've-2',
                            code: 'CARIES',
                            phase: 'existing',
                            targets: [{ kind: 'tooth', tooth_key: '55' }],
                        },
                    ],
                },
            },
        });

        const adapted = adaptWorkspaceSnapshotToRenderer(snapshot);

        expect(adapted.dentition).toBe(PROJECTION_DENTITIONS.MIXED);
        expect(adapted.projection.toothOrder).toHaveLength(52);
        expect(adapted.isEmpty).toBe(false);
    });

    it('does not hide opposite-dentition clinical data behind the adult/child toggle', () => {
        const primaryOnly = createBaseSnapshot({
            teeth: {
                '55': {
                    tooth_key: '55',
                    lifecycle: 'MISSING',
                },
            },
        });
        const permanentOnly = createBaseSnapshot({
            teeth: {
                '16': {
                    tooth_key: '16',
                    lifecycle: 'MISSING',
                },
            },
        });

        const adult = adaptWorkspaceSnapshotToRenderer(primaryOnly);
        const child = adaptWorkspaceSnapshotToRenderer(permanentOnly, { isPediatric: true });

        expect(adult.dentition).toBe(PROJECTION_DENTITIONS.MIXED);
        expect(adult.projection.teeth['55'].lifecycle).toBe('MISSING');
        expect(child.dentition).toBe(PROJECTION_DENTITIONS.MIXED);
        expect(child.projection.teeth['16'].lifecycle).toBe('MISSING');
    });

    it('omits invalid tooth-specific targets with warnings instead of crashing the chart', () => {
        const snapshot = createBaseSnapshot({
            teeth: {
                '21': {
                    tooth_key: '21',
                    findings: [{
                        visual_id: 'bad-surface',
                        code: 'CARIES',
                        phase: 'existing',
                        targets: [{ kind: 'surface', tooth_key: '21', surface_code: 'O' }],
                    }],
                },
                '16': {
                    tooth_key: '16',
                    procedures: [{
                        visual_id: 'bad-root',
                        code: 'ENDO_RCT',
                        phase: 'completed',
                        targets: [{ kind: 'root', tooth_key: '16', root_id: 'single' }],
                    }],
                },
            },
        });

        const adapted = adaptWorkspaceSnapshotToRenderer(snapshot);

        expect(adapted.projection.teeth['21'].findings).toHaveLength(0);
        expect(adapted.projection.teeth['16'].procedures).toHaveLength(0);
        expect(adapted.warnings.filter((warning) => (
            warning.code === 'INVALID_ANATOMICAL_TARGET'
        ))).toHaveLength(2);
    });

    it('filters unsupported clinical codes from visual procedures while preserving warnings', () => {
        const snapshot = createBaseSnapshot({
            teeth: {
                '11': {
                    tooth_key: '11',
                    procedures: [
                        {
                            visual_id: 've-unsupported',
                            code: 'PROS_DENTURE', // Not in odontogram renderer procedure allowlist
                            phase: 'completed',
                            targets: [{ kind: 'tooth', tooth_key: '11' }],
                        },
                        {
                            visual_id: 've-supported',
                            code: 'REST_COMPOSITE',
                            phase: 'completed',
                            targets: [{ kind: 'tooth', tooth_key: '11' }],
                        },
                    ],
                },
            },
            warnings: [
                {
                    code: 'UNSUPPORTED_CLINICAL_CODE',
                    message: "Unsupported legacy procedure 'Complete Denture' preserved as unclassified warning.",
                    source_kind: 'treatment',
                    source_id: 80,
                },
            ],
        });

        const adapted = adaptWorkspaceSnapshotToRenderer(snapshot);
        const t11 = adapted.projection.teeth['11'];

        // Only REST_COMPOSITE is included visually; PROS_DENTURE is excluded
        expect(t11.procedures).toHaveLength(1);
        expect(t11.procedures[0].code).toBe('REST_COMPOSITE');

        // Warnings preserved in adapted output
        expect(adapted.warnings).toHaveLength(1);
        expect(adapted.warnings[0].code).toBe('UNSUPPORTED_CLINICAL_CODE');
        expect(adapted.warnings[0].message).toContain('Complete Denture');
    });

    it('maps findings, procedures, and lifecycles correctly', () => {
        const snapshot = createBaseSnapshot({
            teeth: {
                '21': {
                    tooth_key: '21',
                    lifecycle: 'EXTRACTED',
                    findings: [
                        {
                            visual_id: 've-f1',
                            code: 'CARIES',
                            phase: 'existing',
                            targets: [{ kind: 'surface', tooth_key: '21', surface_code: 'I' }],
                        },
                    ],
                    procedures: [
                        {
                            visual_id: 've-p1',
                            code: 'PROS_CROWN',
                            phase: 'completed',
                            targets: [{ kind: 'tooth', tooth_key: '21' }],
                        },
                    ],
                },
            },
        });

        const adapted = adaptWorkspaceSnapshotToRenderer(snapshot);
        const t21 = adapted.projection.teeth['21'];

        expect(t21.lifecycle).toBe(TOOTH_LIFECYCLE_CODES.EXTRACTED);
        expect(t21.findings).toHaveLength(1);
        expect(t21.findings[0].code).toBe(FINDING_CODES.CARIES);
        expect(t21.findings[0].targets[0]).toEqual({
            kind: 'surface',
            toothKey: '21',
            surfaceCode: 'I',
        });
        expect(t21.procedures).toHaveLength(1);
        expect(t21.procedures[0].code).toBe(PROCEDURE_CODES.PROS_CROWN);
    });

    it('computes derived flags correctly: isFallback, isPartial, isEmpty', () => {
        // 1. Full native complete -> no fallback, not partial
        const completeSnap = createBaseSnapshot();
        const adaptedComplete = adaptWorkspaceSnapshotToRenderer(completeSnap);
        expect(adaptedComplete.isFallback).toBe(false);
        expect(adaptedComplete.isPartial).toBe(false);
        expect(adaptedComplete.isEmpty).toBe(true);

        // 2. Partial coverage
        const partialSnap = createBaseSnapshot({
            coverage: {
                teeth: 'COMPLETE',
                treatments: 'PARTIAL',
                sessions: 'COMPLETE',
            },
        });
        const adaptedPartial = adaptWorkspaceSnapshotToRenderer(partialSnap);
        expect(adaptedPartial.isFallback).toBe(true);
        expect(adaptedPartial.isPartial).toBe(true);

        // 3. Fallback warning present
        const warningSnap = createBaseSnapshot({
            warnings: [{ code: 'FALLBACK_DATA_ACTIVE', message: 'Fallback active' }],
        });
        const adaptedWarning = adaptWorkspaceSnapshotToRenderer(warningSnap);
        expect(adaptedWarning.isFallback).toBe(true);

        // 4. Not empty when work items exist
        const withWorkItems = createBaseSnapshot({
            work_items: [{ id: '1', kind: 'procedure', code: 'REST_COMPOSITE' }],
        });
        const adaptedWithWorkItems = adaptWorkspaceSnapshotToRenderer(withWorkItems);
        expect(adaptedWithWorkItems.isEmpty).toBe(false);
    });

    it('fires onToothClick exactly once when tooth is selected', () => {
        const onToothClick = vi.fn();
        const onSurfaceClick = vi.fn();
        const snapshot = createBaseSnapshot();

        const adapted = adaptWorkspaceSnapshotToRenderer(snapshot, {
            onToothClick,
            onSurfaceClick,
        });

        // Simulate onToothSelected callback from renderer adapter
        adapted.rendererInput.callbacks.onToothSelected({
            type: 'SELECT_TOOTH',
            target: { toothKey: '16' },
        });

        expect(onToothClick).toHaveBeenCalledTimes(1);
        expect(onToothClick).toHaveBeenCalledWith('16', 'fdi');

        // Simulate surface click callback
        adapted.rendererInput.callbacks.onSurfaceSelected({
            type: 'SELECT_SURFACE',
            target: { toothKey: '16', surfaceCode: 'M' },
        });
        expect(onSurfaceClick).toHaveBeenCalledTimes(1);
        expect(onSurfaceClick).toHaveBeenCalledWith({ toothKey: '16', surfaceCode: 'M' });
    });

    it('respects readMode from backend snapshot', () => {
        for (const mode of ['LEGACY_ONLY', 'SHADOW', 'VNEXT_PRIMARY']) {
            const snapshot = createBaseSnapshot({ read_mode: mode });
            const adapted = adaptWorkspaceSnapshotToRenderer(snapshot);
            expect(adapted.readMode).toBe(mode);
        }
    });

    it('defaults readMode to LEGACY_ONLY when absent or undefined in snapshot (fail-closed)', () => {
        const snapshotWithoutReadMode = createBaseSnapshot({ read_mode: undefined });
        delete snapshotWithoutReadMode.read_mode;
        const adapted = adaptWorkspaceSnapshotToRenderer(snapshotWithoutReadMode);
        expect(adapted.readMode).toBe('LEGACY_ONLY');

        const emptyAdapted = adaptWorkspaceSnapshotToRenderer(null);
        expect(emptyAdapted.readMode).toBe('LEGACY_ONLY');
    });

    it('sets condition to null for unrecorded teeth while preserving explicit legacy Healthy', () => {
        const snapshot = createBaseSnapshot({
            teeth: {
                '21': {
                    tooth_key: '21',
                    condition: 'Healthy',
                },
            },
        });

        const adapted = adaptWorkspaceSnapshotToRenderer(snapshot);
        // Tooth 11 is unrecorded -> teethStatus condition must be null
        expect(adapted.teethStatus['11']).toBeDefined();
        expect(adapted.teethStatus['11'].condition).toBeNull();

        // Tooth 21 has explicit legacy Healthy -> preserved as 'Healthy'
        expect(adapted.teethStatus['21']).toBeDefined();
        expect(adapted.teethStatus['21'].condition).toBe('Healthy');
    });
});

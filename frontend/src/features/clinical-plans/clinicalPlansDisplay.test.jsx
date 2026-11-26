import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import arTranslations from '@/locales/ar/translation.json';
import enTranslations from '@/locales/en/translation.json';
import AddProcedureModal from './AddProcedureModal';
import PlanItemRow from './PlanItemRow';
import PlanPhaseCard from './PlanPhaseCard';
import DeletePhaseConfirm from './DeletePhaseConfirm';
import PlanComparisonModal from './PlanComparisonModal';
import PlanOverlayActiveBanner from '@/features/patients/components/PlanOverlayActiveBanner';

const localeState = vi.hoisted(() => ({ language: 'ar' }));

function resolveTranslation(dict, key) {
    return key.split('.').reduce((acc, part) => (acc && typeof acc === 'object' ? acc[part] : undefined), dict);
}

function makeTranslator(language) {
    const dict = language === 'ar' ? arTranslations : enTranslations;
    return (key, fallbackOrOptions, maybeOptions) => {
        const fallback = typeof fallbackOrOptions === 'string' ? fallbackOrOptions : key;
        const options = typeof fallbackOrOptions === 'object' && fallbackOrOptions !== null
            ? fallbackOrOptions
            : maybeOptions;
        const raw = resolveTranslation(dict, key);
        let text = typeof raw === 'string' ? raw : fallback;
        if (options && typeof options === 'object') {
            for (const [k, v] of Object.entries(options)) {
                text = text.replaceAll(`{{${k}}}`, String(v));
            }
        }
        return text;
    };
}

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: makeTranslator(localeState.language),
        i18n: { language: localeState.language },
    }),
}));

describe('Clinical plans display & localization regressions', () => {
    beforeEach(() => {
        localeState.language = 'ar';
    });

    describe('AddProcedureModal', () => {
        const candidates = [
            {
                id: 501,
                code: 'ENDO_RCT',
                status: 'proposed',
                targets: [{ tooth_key: '16', surface_code: 'MO' }],
            },
            {
                id: 502,
                code: 'D2391',
                status: 'planned',
                targets: [{ tooth_key: '24', surface_code: 'O' }],
            },
            {
                id: 503,
                status: 'active',
                targets: [],
            },
            {
                id: 504,
                code: 'PROS_CROWN',
                display_name: 'Custom Gold Crown',
                status: 'open',
                targets: [{ tooth_key: '36' }],
            },
        ];

        it('localizes dialog phase title and candidate labels/targets/statuses in Arabic without "undefined"', () => {
            localeState.language = 'ar';
            render(
                <AddProcedureModal
                    open
                    phaseName="Phase 1"
                    onClose={vi.fn()}
                    onSubmit={vi.fn()}
                    isLoading={false}
                    candidates={candidates}
                    selectedWorkItemId=""
                    onSelectWorkItemId={vi.fn()}
                    isPending={false}
                    isRtl
                />
            );

            const heading = screen.getByRole('heading');
            expect(heading.textContent).toContain('المرحلة 1');
            expect(heading.textContent).not.toContain('Phase 1');

            const select = screen.getByTestId('candidate-procedure-select');
            const optionTexts = Array.from(select.querySelectorAll('option')).map((o) => o.textContent);

            expect(optionTexts).toContain('علاج جذور — [16 (MO)] (مقترحة)');
            expect(optionTexts).toContain('D2391 — [24 (O)] (مخطط)');
            expect(optionTexts).toContain('عنصر #503 (نشط)');
            expect(optionTexts).toContain('Custom Gold Crown — [36] (مفتوح)');
            expect(optionTexts.join(' ')).not.toContain('undefined');
        });

        it('renders canonical procedure names, targets, statuses, and fallback in English', () => {
            localeState.language = 'en';
            render(
                <AddProcedureModal
                    open
                    phaseName="Phase 1"
                    onClose={vi.fn()}
                    onSubmit={vi.fn()}
                    isLoading={false}
                    candidates={candidates}
                    selectedWorkItemId=""
                    onSelectWorkItemId={vi.fn()}
                    isPending={false}
                    isRtl={false}
                />
            );

            const heading = screen.getByRole('heading');
            expect(heading.textContent).toContain('Phase 1');

            const select = screen.getByTestId('candidate-procedure-select');
            const optionTexts = Array.from(select.querySelectorAll('option')).map((o) => o.textContent);

            expect(optionTexts).toContain('Root Canal Treatment — [16 (MO)] (Proposed)');
            expect(optionTexts).toContain('D2391 — [24 (O)] (Planned)');
            expect(optionTexts).toContain('Item #503 (Active)');
            expect(optionTexts).toContain('Custom Gold Crown — [36] (Open)');
            expect(optionTexts.join(' ')).not.toContain('undefined');
        });
    });

    describe('PlanItemRow', () => {
        const plan = { id: 1, status: 'draft' };

        it('reads work_item.code, targets[].surface_code, and localized statuses in Arabic', () => {
            localeState.language = 'ar';
            render(
                <>
                    <PlanItemRow
                        plan={plan}
                        canModifyPlan
                        onRemoveItem={vi.fn()}
                        item={{
                            id: 1,
                            work_item_id: 501,
                            estimated_fee: 900,
                            unpriced: false,
                            work_item: {
                                id: 501,
                                code: 'REST_COMPOSITE',
                                status: 'planned',
                                targets: [{ tooth_key: '14', surface_code: 'MOD' }],
                            },
                        }}
                    />
                    <PlanItemRow
                        plan={plan}
                        canModifyPlan
                        onRemoveItem={vi.fn()}
                        item={{
                            id: 2,
                            work_item_id: 502,
                            estimated_fee: 0,
                            unpriced: true,
                            work_item: {
                                id: 502,
                                code: 'Scaling',
                                status: 'in_progress',
                                targets: [],
                            },
                        }}
                    />
                    <PlanItemRow
                        plan={plan}
                        canModifyPlan
                        onRemoveItem={vi.fn()}
                        item={{
                            id: 9,
                            work_item_id: 509,
                            estimated_fee: 0,
                            unpriced: true,
                        }}
                    />
                </>
            );

            const row1 = screen.getByTestId('phase-item-1');
            expect(row1.textContent).toContain('حشوة كمبوزيت');
            expect(row1.textContent).toContain('14 (MOD)');
            expect(row1.textContent).toContain('مخطط');
            expect(row1.textContent).not.toContain('Item #1');

            const row2 = screen.getByTestId('phase-item-2');
            expect(row2.textContent).toContain('Scaling');
            expect(row2.textContent).toContain('قيد التنفيذ');
            expect(row2.textContent).not.toContain('Item #2');

            const row9 = screen.getByTestId('phase-item-9');
            expect(row9.textContent).toContain('عنصر #9');
        });

        it('renders canonical procedure name and Item fallback in English', () => {
            localeState.language = 'en';
            render(
                <>
                    <PlanItemRow
                        plan={plan}
                        canModifyPlan
                        onRemoveItem={vi.fn()}
                        item={{
                            id: 1,
                            work_item_id: 501,
                            estimated_fee: 900,
                            unpriced: false,
                            work_item: {
                                id: 501,
                                code: 'REST_COMPOSITE',
                                status: 'planned',
                                targets: [{ tooth_key: '14', surface_code: 'MOD' }],
                            },
                        }}
                    />
                    <PlanItemRow
                        plan={plan}
                        canModifyPlan
                        onRemoveItem={vi.fn()}
                        item={{
                            id: 9,
                            work_item_id: 509,
                            estimated_fee: 0,
                            unpriced: true,
                        }}
                    />
                </>
            );

            const row1 = screen.getByTestId('phase-item-1');
            expect(row1.textContent).toContain('Composite Restoration');
            expect(row1.textContent).toContain('14 (MOD)');
            expect(row1.textContent).toContain('Planned');

            const row9 = screen.getByTestId('phase-item-9');
            expect(row9.textContent).toContain('Item #9');
        });
    });

    describe('PlanPhaseCard & DeletePhaseConfirm', () => {
        it('localizes default "Phase N" names while preserving custom names and passing localized name to actions', () => {
            localeState.language = 'ar';
            const onOpenAddProcedure = vi.fn();
            const onDeletePhase = vi.fn();
            const plan = {
                id: 1,
                phases: [
                    { id: 11, phase_order: 0, name: 'Phase 1', status: 'draft', items: [] },
                    { id: 12, phase_order: 1, name: 'Phase 2', status: 'draft', items: [] },
                    { id: 13, phase_order: 2, name: 'Phase 1: Urgent', status: 'draft', items: [] },
                ],
            };

            render(
                <>
                    {plan.phases.map((phase, idx) => (
                        <PlanPhaseCard
                            key={phase.id}
                            plan={plan}
                            phase={phase}
                            idx={idx}
                            canModifyPlan
                            onMovePhaseUp={vi.fn()}
                            onMovePhaseDown={vi.fn()}
                            onOpenEditPhase={vi.fn()}
                            onDeletePhase={onDeletePhase}
                            onOpenAddProcedure={onOpenAddProcedure}
                            onRemoveItem={vi.fn()}
                        />
                    ))}
                    <DeletePhaseConfirm
                        deletingPhase={{ planId: 1, phaseId: 11, name: 'Phase 1' }}
                        onClose={vi.fn()}
                        onConfirm={vi.fn()}
                        isPending={false}
                        isRtl
                    />
                </>
            );

            const phase1Card = screen.getByTestId('clinical-phase-item-11');
            expect(phase1Card.textContent).toContain('المرحلة 1');
            expect(phase1Card.textContent).not.toContain('Phase 1');

            const phase2Card = screen.getByTestId('clinical-phase-item-12');
            expect(phase2Card.textContent).toContain('المرحلة 2');
            expect(phase2Card.textContent).not.toContain('Phase 2');

            const customCard = screen.getByTestId('clinical-phase-item-13');
            expect(customCard.textContent).toContain('Phase 1: Urgent');

            fireEvent.click(screen.getByTestId('add-procedure-button-11'));
            expect(onOpenAddProcedure).toHaveBeenCalledWith(1, 11, 'المرحلة 1');

            fireEvent.click(screen.getByTestId('delete-phase-button-11'));
            expect(onDeletePhase).toHaveBeenCalledWith({ planId: 1, phaseId: 11, name: 'المرحلة 1' });

            const deleteDialog = screen.getByTestId('delete-phase-dialog');
            expect(deleteDialog.textContent).toContain('المرحلة 1');
            expect(deleteDialog.textContent).not.toContain('Phase 1');
        });
    });

    describe('PlanComparisonModal', () => {
        it('renders localized phase names, work_item.code procedure names, and surface_code targets in Arabic', () => {
            localeState.language = 'ar';
            const planA = {
                id: 10,
                title: 'خطة أ',
                status: 'proposed',
                plan_estimated_total: 1500,
                unpriced_items_count: 0,
                phases: [
                    {
                        id: 101,
                        phase_order: 0,
                        name: 'Phase 1',
                        phase_estimated_total: 1500,
                        items: [
                            {
                                id: 1001,
                                work_item_id: 501,
                                estimated_fee: 1500,
                                unpriced: false,
                                work_item: {
                                    id: 501,
                                    code: 'ENDO_RCT',
                                    status: 'proposed',
                                    targets: [{ tooth_key: '16', surface_code: 'MO' }],
                                },
                            },
                        ],
                    },
                ],
            };
            const planB = {
                id: 20,
                title: 'خطة ب',
                status: 'draft',
                plan_estimated_total: 800,
                unpriced_items_count: 0,
                phases: [
                    {
                        id: 201,
                        phase_order: 0,
                        name: 'Phase 2',
                        phase_estimated_total: 800,
                        items: [
                            {
                                id: 2001,
                                work_item_id: 502,
                                estimated_fee: 800,
                                unpriced: false,
                                work_item: {
                                    id: 502,
                                    code: 'D2150',
                                    status: 'planned',
                                    targets: [{ tooth_key: '26', surface_code: 'DO' }],
                                },
                            },
                        ],
                    },
                ],
            };

            render(
                <PlanComparisonModal
                    open
                    onClose={vi.fn()}
                    plans={[planA, planB]}
                    onAcceptPlan={vi.fn()}
                />
            );

            const colA = screen.getByTestId('comparison-column-plan-a');
            expect(colA.textContent).toContain('المرحلة 1');
            expect(colA.textContent).not.toContain('Phase 1');
            expect(colA.textContent).toContain('علاج جذور');
            expect(colA.textContent).not.toContain('#501');
            expect(colA.textContent).toContain('16 (MO)');

            const colB = screen.getByTestId('comparison-column-plan-b');
            expect(colB.textContent).toContain('المرحلة 2');
            expect(colB.textContent).toContain('D2150');
            expect(colB.textContent).toContain('26 (DO)');
        });
    });

    describe('PlanOverlayActiveBanner', () => {
        it('localizes default "Phase 1" in both the active header and phase chip in Arabic', () => {
            const t = makeTranslator('ar');
            render(
                <PlanOverlayActiveBanner
                    planOverlay={{
                        planId: 1,
                        planTitle: 'خطة شاملة',
                        phaseId: 11,
                        phases: [
                            {
                                id: 11,
                                name: 'Phase 1',
                                colorConfig: { bg: '#eff6ff', text: '#1d4ed8', border: '#3b82f6', badgeBg: '#2563eb' },
                            },
                        ],
                    }}
                    onToggleOverlay={vi.fn()}
                    t={t}
                />
            );

            const banner = screen.getByTestId('plan-overlay-active-banner');
            expect(banner.textContent).toContain('المرحلة 1');
            expect(banner.textContent).not.toContain('Phase 1');
        });
    });
});
